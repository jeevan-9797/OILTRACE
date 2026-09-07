from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException, Path

from app.core.database import supabase
from app.core.timeutil import parse_timestamp
from app.api.routes.drift import get_nearest_environment
from app.api.routes.attribution import (
    calculate_attribution_for_spill
)

router = APIRouter(
    prefix="/api",
    tags=["Spill Details"]
)


@router.get(
    "/spills/{spill_id}",
    summary="Get complete spill information"
)
def get_spill_details(
    spill_id: str = Path(
        ...,
        description="Spill code",
        example="SP-AI-2B609F84"
    )
):

    # =====================================================
    # 1. GET SPILL
    # =====================================================

    spill_response = (
        supabase
        .table("spills")
        .select(
            "id, spill_code, detected, confidence, "
            "area_km2, centroid_latitude, "
            "centroid_longitude, polygon, "
            "detected_at, estimated_origin_at, "
            "estimated_age_hours, status, "
            "source_image_id, created_at"
        )
        .eq(
            "spill_code",
            spill_id
        )
        .limit(1)
        .execute()
    )

    if not spill_response.data:

        raise HTTPException(
            status_code=404,
            detail=f"Spill '{spill_id}' not found"
        )

    spill = spill_response.data[0]

    spill_uuid = spill["id"]

    # =====================================================
    # 2. GET DRIFT
    # =====================================================

    drift_response = (
        supabase
        .table("spill_drift_points")
        .select(
            "sequence_no, latitude, longitude, "
            "timestamp, path_type, "
            "model_source, confidence"
        )
        .eq(
            "spill_id",
            spill_uuid
        )
        .order(
            "sequence_no"
        )
        .execute()
    )

    drift_points = (
        drift_response.data
        or []
    )

    historical_path = [
        point
        for point in drift_points
        if point["path_type"] == "historical"
        or point["path_type"] == "origin"
    ]

    predicted_path = [
        point
        for point in drift_points
        if point["path_type"] == "predicted"
    ]

    # =====================================================
    # 3. GET ATTRIBUTION
    # =====================================================

    try:

        attribution = (
            calculate_attribution_for_spill(
                spill_uuid
            )
        )

    except Exception as e:

        attribution = []

        print(
            f"Attribution error for "
            f"{spill_id}: {e}"
        )

    # =====================================================
    # 4. GET ENVIRONMENTAL DATA
    # =====================================================

    environment_response = (
        supabase
        .table("weather_ocean_data")
        .select(
            "id, timestamp, latitude, longitude, "
            "wind_speed, wind_direction, "
            "current_speed, current_direction, "
            "source, metadata"
        )
        .order(
            "timestamp",
            desc=True
        )
        .limit(20)
        .execute()
    )

    environment = (
        environment_response.data
        or []
    )

    # Find closest environmental observation to spill location & time
    nearest_env = None
    if spill.get("centroid_latitude") is not None and spill.get("centroid_longitude") is not None:
        try:
            spill_time_raw = spill.get("estimated_origin_at") or spill.get("detected_at")
            if spill_time_raw:
                spill_time_dt = parse_timestamp(spill_time_raw)
            else:
                spill_time_dt = datetime.now(timezone.utc)

            if spill_time_dt is not None:
                nearest_env = get_nearest_environment(
                    float(spill["centroid_latitude"]),
                    float(spill["centroid_longitude"]),
                    spill_time_dt
                )
        except Exception as env_err:
            print(f"Error finding nearest environment for {spill_id}: {env_err}")

    latest_env = nearest_env if nearest_env is not None else (environment[0] if environment else None)

    # =====================================================
    # 5. RETURN COMPLETE RESPONSE
    # =====================================================

    return {

        "spill": {

            "id":
                spill["id"],

            "spill_code":
                spill["spill_code"],

            "detected":
                spill["detected"],

            "confidence":
                spill["confidence"],

            "area_km2":
                spill["area_km2"],

            "centroid": {

                "latitude":
                    spill["centroid_latitude"],

                "longitude":
                    spill["centroid_longitude"]
            },

            "polygon":
                spill["polygon"],

            "detected_at":
                spill["detected_at"],

            "estimated_origin_at":
                spill["estimated_origin_at"],

            "estimated_age_hours":
                spill["estimated_age_hours"],

            "status":
                spill["status"],

            "source_image_id":
                spill["source_image_id"],

            "created_at":
                spill["created_at"]
        },

        "drift": {

            "historical":
                historical_path,

            "predicted":
                predicted_path,

            "total_points":
                len(drift_points)
        },

        "attribution": {

            "candidates":
                attribution,

            "top_candidate":
                (
                    attribution[0]
                    if attribution
                    else None
                ),

            "total_candidates":
                len(attribution)
        },

        "environment": {

            "data":
                environment,

            "latest":
                latest_env
        }
    }