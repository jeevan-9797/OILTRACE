import gc
import logging
import os
import tempfile
import time
import uuid
from datetime import datetime, timezone

from app.core.database import supabase
from app.services.ai.inference import run_inference
from app.api.routes.drift import generate_drift_for_spill
from app.api.routes.attribution import calculate_attribution_for_spill 
from app.services.georeferencing.dartis import (
    get_image_metadata,
    pixel_to_geo,
    polygon_pixels_to_geo,
    calculate_polygon_area_km2,
)

logger = logging.getLogger("oiltrace.detection")


def get_or_create_satellite_image(
    image_name: str,
    metadata: dict
):
    """
    Find the satellite_images record for this DARTIS image.
    If it does not exist, create it and return its UUID.
    """

    # ---------------------------------------------------------
    # Check whether this image already exists
    # ---------------------------------------------------------

    response = (
        supabase
        .table("satellite_images")
        .select("id")
        .eq("local_path", image_name)
        .limit(1)
        .execute()
    )

    if response.data:
        return response.data[0]["id"]

    # ---------------------------------------------------------
    # Create satellite_images record
    # ---------------------------------------------------------

    # Calculate approximate geographic center from the DARTIS corners.
    latitude = (
        metadata["ul"][1]
        + metadata["ur"][1]
        + metadata["br"][1]
        + metadata["bl"][1]
    ) / 4

    longitude = (
        metadata["ul"][0]
        + metadata["ur"][0]
        + metadata["br"][0]
        + metadata["bl"][0]
    ) / 4

    new_image = {
        "provider": "DARTIS / Copernicus / ESA",
        "satellite": "Sentinel-1A",
        "sensor": "SAR (C-Band Synthetic Aperture Radar)",
        "acquired_at": "2019-04-13T03:42:57+00:00",
        "latitude": latitude,
        "longitude": longitude,
        "image_url": None,
        "local_path": image_name,
        "metadata": {
            "dataset": "DARTIS",
            "source_product": (
                "S1A_IW_GRDH_1SDV_20190413T034257_"
                "20190413T034322_026766_0301B4_A807.SAFE"
            ),
            "image_width": metadata["width"],
            "image_height": metadata["height"],
            "ul": metadata["ul"],
            "ur": metadata["ur"],
            "br": metadata["br"],
            "bl": metadata["bl"],
        },
    }

    try:
        inserted = (
            supabase
            .table("satellite_images")
            .insert(new_image)
            .execute()
        )
    except Exception as create_error:
        # A concurrent request may have created the same local_path between
        # the initial lookup and insert. Reuse that record when possible.
        existing = (
            supabase
            .table("satellite_images")
            .select("id")
            .eq("local_path", image_name)
            .limit(1)
            .execute()
        )
        if existing.data:
            return existing.data[0]["id"]
        raise RuntimeError(
            f"Failed to create satellite_images record for {image_name}: {create_error}"
        ) from create_error

    if not inserted.data:
        raise RuntimeError(
            f"Failed to create satellite_images record for {image_name}: "
            "the database returned no inserted record"
        )

    return inserted.data[0]["id"]


def detect_spill(
    image_bytes: bytes,
    image_name: str
):
    """
    Complete oil-spill detection pipeline.

    Flow:

        Uploaded image
            ↓
        DARTIS metadata
            ↓
        YOLO inference
            ↓
        Pixel coordinates
            ↓
        Geographic coordinates
            ↓
        Area in km²
            ↓
        ai_detections
            ↓
        spills
            ↓
        environmental drift prediction
    """

    temp_path = None
    pipeline_started = time.perf_counter()

    def log_stage(stage: str, started: float):
        logger.info(
            "[TIMING] %s: %.2fs",
            stage,
            time.perf_counter() - started,
        )

    try:

        # =====================================================
        # 1. Get DARTIS geospatial metadata
        # =====================================================

        stage_started = time.perf_counter()
        metadata = get_image_metadata(
            image_name
        )
        log_stage("metadata lookup", stage_started)

        width = metadata["width"]
        height = metadata["height"]

        corners = {
            "ul": metadata["ul"],
            "ur": metadata["ur"],
            "br": metadata["br"],
            "bl": metadata["bl"],
        }

        # =====================================================
        # 2. Get/create satellite image record
        # =====================================================

        stage_started = time.perf_counter()
        satellite_image_id = (
            get_or_create_satellite_image(
                image_name,
                metadata
            )
        )
        log_stage("satellite image lookup/create", stage_started)

        # =====================================================
        # 3. Save uploaded image temporarily
        # =====================================================

        stage_started = time.perf_counter()
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        ) as temp_file:

            temp_file.write(
                image_bytes
            )

            temp_path = temp_file.name
        log_stage("image_preprocessing", stage_started)

        # =====================================================
        # 4. Run YOLO inference
        # =====================================================

        stage_started = time.perf_counter()
        result = run_inference(
            temp_path
        )
        log_stage("YOLO inference and result processing", stage_started)

        ai_rows = []
        spill_rows = []
        geographic_detections = []

        # =====================================================
        # 5. Process every YOLO detection
        # =====================================================

        stage_started = time.perf_counter()
        for index, detection in enumerate(
            result["detections"]
        ):

            confidence = detection[
                "confidence"
            ]

            bbox = detection[
                "bbox"
            ]

            centroid_pixels = detection[
                "centroid"
            ]

            polygon_pixels = detection[
                "polygon"
            ]

            area_pixels = detection[
                "area_pixels"
            ]

            # -------------------------------------------------
            # Pixel centroid → geographic centroid
            # -------------------------------------------------

            centroid_geo = pixel_to_geo(
                x=centroid_pixels[0],
                y=centroid_pixels[1],
                width=width,
                height=height,
                corners=corners,
            )

            # -------------------------------------------------
            # Pixel polygon → geographic polygon
            # -------------------------------------------------

            polygon_geo = polygon_pixels_to_geo(
                polygon=polygon_pixels,
                width=width,
                height=height,
                corners=corners,
            )

            # -------------------------------------------------
            # Geographic area
            # -------------------------------------------------

            area_km2 = calculate_polygon_area_km2(
                polygon_geo
            )

            # =================================================
            # 6. Prepare ai_detections row
            # =================================================

            ai_rows.append({

                "satellite_image_id":
                    satellite_image_id,

                "detection_index":
                    index,

                "confidence":
                    confidence,

                "bbox":
                    bbox,

                "centroid_pixels":
                    centroid_pixels,

                "polygon_pixels":
                    polygon_pixels,

                "area_pixels":
                    area_pixels,

                "model_source":
                    "YOLO",
            })

            # =================================================
            # 7. Convert polygon to GeoJSON
            # =================================================

            geojson_polygon = None

            if polygon_geo:

                coordinates = [
                    [
                        point[1],  # longitude
                        point[0],  # latitude
                    ]
                    for point in polygon_geo
                ]

                # GeoJSON polygon must be closed
                if coordinates:

                    if coordinates[0] != coordinates[-1]:

                        coordinates.append(
                            coordinates[0]
                        )

                geojson_polygon = {
                    "type": "Polygon",

                    "coordinates": [
                        coordinates
                    ],
                }

            # =================================================
            # 8. Create spill record
            # =================================================

            spill_code = (
                f"SP-AI-"
                f"{uuid.uuid4().hex[:8].upper()}"
            )

            detected_at = (
                datetime.now(
                    timezone.utc
                ).isoformat()
            )

            spill_rows.append({

                "spill_code":
                    spill_code,

                "detected":
                    True,

                "confidence":
                    confidence,

                "area_km2":
                    area_km2,

                "centroid_latitude":
                    centroid_geo[0],

                "centroid_longitude":
                    centroid_geo[1],

                "polygon":
                    geojson_polygon,

                "detected_at":
                    detected_at,

                "estimated_origin_at":
                    None,

                "estimated_age_hours":
                    None,

                "status":
                    "detected",

                "source_image_id":
                    satellite_image_id,
            })

            # =================================================
            # 9. Prepare API response
            # =================================================

            geographic_detections.append({

                "spill_code":
                    spill_code,

                "detected_at":
                    detected_at,

                "confidence":
                    confidence,

                "bbox":
                    bbox,

                "centroid_pixels":
                    centroid_pixels,

                "centroid":
                    centroid_geo,

                "area_pixels":
                    area_pixels,

                "area_km2":
                    area_km2,

                "polygon_pixels":
                    polygon_pixels,

                "polygon":
                    polygon_geo,
            })
        log_stage("spill_processing", stage_started)

        # =====================================================
        # 10. Insert AI detections
        # =====================================================

        logger.info("[DETECT] Supabase operations started")

        stage_started = time.perf_counter()
        if ai_rows:

            ai_insert_response = (
                supabase
                .table("ai_detections")
                .insert(ai_rows)
                .execute()
            )

            if not ai_insert_response.data:

                raise RuntimeError(
                    "Failed to save AI detections"
                )

        # =====================================================
        # 11. Insert spills
        # =====================================================

        inserted_spills = []

        if spill_rows:

            spill_insert_response = (
                supabase
                .table("spills")
                .insert(spill_rows)
                .execute()
            )

            inserted_spills = (
                spill_insert_response.data
                or []
            )

            if not inserted_spills:

                raise RuntimeError(
                    "Failed to save spill records"
                )
        log_stage("AI and spill database inserts", stage_started)

        # =====================================================
        # 12. Generate drift + attribution for each new spill
        # =====================================================

        drift_results = []
        attribution_results = []

        # Per-request shared data: fetch weather and AIS data once for all spills in this request
        shared_weather_records = None
        shared_vessel_positions = None
        shared_vessel_names = None
        shared_vessel_details = None

        if inserted_spills:
            try:
                weather_resp = (
                    supabase
                    .table("weather_ocean_data")
                    .select(
                        "id, timestamp, latitude, longitude, "
                        "wind_speed, wind_direction, "
                        "current_speed, current_direction, "
                        "source, metadata"
                    )
                    .execute()
                )
                shared_weather_records = weather_resp.data or []
            except Exception as w_err:
                logger.warning("[DETECT] Failed to pre-fetch shared weather data: %s", w_err)

            try:
                positions_resp = (
                    supabase
                    .table("vessel_positions")
                    .select(
                        "mmsi, timestamp, latitude, "
                        "longitude, speed_knots, "
                        "heading_deg"
                    )
                    .execute()
                )
                raw_positions = positions_resp.data or []
                if raw_positions:
                    grouped_positions = {}
                    for pos in raw_positions:
                        mmsi = str(pos["mmsi"])
                        if mmsi not in grouped_positions:
                            grouped_positions[mmsi] = []
                        grouped_positions[mmsi].append(pos)
                    shared_vessel_positions = grouped_positions

                    mmsis = list(grouped_positions.keys())
                    vessels_resp = (
                        supabase
                        .table("vessels")
                        .select("mmsi, name, vessel_type, flag")
                        .in_("mmsi", mmsis)
                        .execute()
                    )
                    shared_vessel_names = {
                        str(v["mmsi"]): (v.get("name") or "UNKNOWN VESSEL")
                        for v in (vessels_resp.data or [])
                    }
                    shared_vessel_details = {
                        str(v["mmsi"]): v
                        for v in (vessels_resp.data or [])
                    }
            except Exception as v_err:
                logger.warning("[DETECT] Failed to pre-fetch shared vessel data: %s", v_err)

        all_drift_points = []
        all_attribution_rows = []

        for spill in inserted_spills:

            spill_uuid = spill["id"]
            spill_code = spill["spill_code"]

            # -------------------------------------------------
            # Generate environmental drift
            # -------------------------------------------------

            try:
                stage_started = time.perf_counter()
                # In-memory data reuse: pass spill record, is_new_spill=True, and shared weather records
                # Batch writes: pass save_to_db=False to batch insert all points after loop
                generated_points, drift_status, coverage_details = (
                    generate_drift_for_spill(
                        spill_uuid,
                        spill_record=spill,
                        is_new_spill=True,
                        environment_records=shared_weather_records,
                        save_to_db=False,
                        return_details=True
                    )
                )
                if generated_points:
                    all_drift_points.extend(generated_points)

                drift_results.append({
                    "spill_id": spill_code,
                    "status": drift_status,
                    "points": len(generated_points),
                    "environmental_coverage": (drift_status == "normal"),
                    "coverage_details": coverage_details
                })
                log_stage("drift", stage_started)

            except Exception as drift_error:

                logger.warning(
                    "[DETECT] drift calculation failed for spill %s: %s",
                    spill_code,
                    drift_error
                )

                drift_results.append({

                    "spill_id":
                        spill_code,

                    "status":
                        "failed",

                    "error":
                        str(drift_error)
                })

                # Don't calculate attribution if
                # drift generation failed.
                continue

            # -------------------------------------------------
            # Calculate vessel attribution
            # -------------------------------------------------

            try:
                stage_started = time.perf_counter()
                # In-memory data reuse: pass spill record, generated drift points, and shared vessel data
                # Batch writes: pass save_to_db=False and return_db_rows=True to batch upsert all rows after loop
                candidates, attr_rows = (
                    calculate_attribution_for_spill(
                        spill_uuid,
                        spill_record=spill,
                        drift_points=generated_points,
                        vessel_positions=shared_vessel_positions,
                        vessel_names=shared_vessel_names,
                        save_to_db=False,
                        return_db_rows=True,
                        vessel_details=shared_vessel_details
                    )
                )
                if attr_rows:
                    all_attribution_rows.extend(attr_rows)

                attribution_results.append({

                    "spill_id":
                        spill_code,

                    "status":
                        "calculated" if candidates else "no_eligible_vessels",

                    "candidates":
                        candidates
                })
                log_stage(f"attribution calculation ({spill_code})", stage_started)

            except Exception as attribution_error:

                logger.warning(
                    "[DETECT] attribution calculation failed for spill %s: %s",
                    spill_code,
                    attribution_error
                )

                attribution_results.append({

                    "spill_id":
                        spill_code,

                    "status":
                        "failed",

                    "error":
                        str(attribution_error)
                })

        # =====================================================
        # Batch bulk database writes for drift points & attribution
        # =====================================================

        if all_drift_points:
            stage_started = time.perf_counter()
            try:
                (
                    supabase
                    .table("spill_drift_points")
                    .insert(all_drift_points)
                    .execute()
                )
                log_stage(f"bulk drift points insert ({len(all_drift_points)} points)", stage_started)
            except Exception as b_drift_err:
                logger.warning("[DETECT] Failed to bulk insert drift points: %s", b_drift_err)

        if all_attribution_rows:
            stage_started = time.perf_counter()
            try:
                (
                    supabase
                    .table("attribution_scores")
                    .upsert(
                        all_attribution_rows,
                        on_conflict="spill_id,mmsi"
                    )
                    .execute()
                )
                log_stage(f"bulk attribution scores upsert ({len(all_attribution_rows)} rows)", stage_started)
            except Exception as b_attr_err:
                logger.warning("[DETECT] Failed to bulk upsert attribution scores: %s", b_attr_err)

        logger.info(
            "[DETECT] Supabase operations completed: %d spill(s) processed",
            len(inserted_spills)
        )
        log_stage("total detection pipeline", pipeline_started)

        # =====================================================
        # 13. Return complete pipeline response
        # =====================================================

        return {

            "image":
                image_name,

            "satellite_image_id":
                satellite_image_id,

            "image_width":
                width,

            "image_height":
                height,

            "detected_at":
                (inserted_spills[0].get("detected_at")
                 if len(inserted_spills) == 1 else None),

            "detections":
                geographic_detections,

            "spills_created":
                len(inserted_spills),

            "drift":
                drift_results,

            "attribution":
                attribution_results
        }

    finally:

        # =====================================================
        # Delete temporary uploaded image and free memory
        # =====================================================

        if (
            temp_path
            and os.path.exists(temp_path)
        ):
            try:
                os.remove(temp_path)
            except OSError:
                pass

        gc.collect()
