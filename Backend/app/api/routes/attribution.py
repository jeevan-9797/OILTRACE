from math import radians, sin, cos, sqrt, atan2
from datetime import datetime

from fastapi import APIRouter, HTTPException, Path

from app.core.database import supabase
from app.schemas.attribution import (
    AttributionResponse,
    VesselScore
)


router = APIRouter(
    prefix="/api",
    tags=["Attribution"]
)


MODEL_VERSION = "v1.0.0"


# =========================================================
# TIME
# =========================================================

def parse_timestamp(value):

    if isinstance(value, datetime):
        return value

    if not value:
        return None

    return datetime.fromisoformat(
        str(value).replace("Z", "+00:00")
    )


# =========================================================
# HAVERSINE DISTANCE
# =========================================================

def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float
) -> float:

    R = 6371.0

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        +
        cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a)
    )

    return R * c


# =========================================================
# SPATIAL SCORE
# =========================================================

def calculate_spatial_score(
    distance_km: float
) -> float:

    score = 100 - (
        distance_km / 50 * 100
    )

    return max(
        0,
        min(100, score)
    )


# =========================================================
# TEMPORAL SCORE
# =========================================================

def calculate_temporal_score(
    vessel_time: datetime,
    spill_time: datetime
) -> float:

    difference_hours = abs(
        (
            vessel_time - spill_time
        ).total_seconds()
    ) / 3600

    score = 100 - (
        difference_hours / 24 * 100
    )

    return max(
        0,
        min(100, score)
    )


# =========================================================
# TRAJECTORY SCORE
# =========================================================

def calculate_trajectory_score(
    vessel_lat: float,
    vessel_lon: float,
    drift_points: list
) -> float:

    if not drift_points:
        return 0

    minimum_distance = float("inf")

    for point in drift_points:

        distance = haversine_km(
            vessel_lat,
            vessel_lon,
            float(point["latitude"]),
            float(point["longitude"])
        )

        minimum_distance = min(
            minimum_distance,
            distance
        )

    score = 100 - (
        minimum_distance / 50 * 100
    )

    return max(
        0,
        min(100, score)
    )


# =========================================================
# BEHAVIOUR SCORE
# =========================================================

def calculate_behaviour_score(
    position: dict
) -> float:

    speed = position.get(
        "speed_knots"
    )

    if speed is None:
        return 50

    speed = float(speed)

    if 2 <= speed <= 25:
        return 80

    if speed < 2:
        return 50

    return 60

def calculate_environment_score(
    vessel_position: dict,
    drift_points: list
) -> float:
    """
    Estimate how compatible a vessel's position/time is
    with the environmental drift trajectory.

    Higher score means the vessel is closer to the
    predicted environmental pathway.
    """

    if not drift_points:
        return 0.0

    vessel_lat = float(
        vessel_position["latitude"]
    )

    vessel_lon = float(
        vessel_position["longitude"]
    )

    vessel_time = parse_timestamp(
        vessel_position["timestamp"]
    )

    best_score = 0.0

    for point in drift_points:

        point_lat = float(
            point["latitude"]
        )

        point_lon = float(
            point["longitude"]
        )

        point_time = parse_timestamp(
            point["timestamp"]
        )

        distance_km = haversine_km(
            vessel_lat,
            vessel_lon,
            point_lat,
            point_lon
        )

        time_difference_hours = abs(
            (
                vessel_time - point_time
            ).total_seconds()
        ) / 3600.0

        # Spatial compatibility:
        # 50 km or more = 0
        spatial_component = max(
            0.0,
            min(
                100.0,
                100.0
                - (
                    distance_km
                    / 50.0
                    * 100.0
                )
            )
        )

        # Temporal compatibility:
        # 24 hours or more = 0
        temporal_component = max(
            0.0,
            min(
                100.0,
                100.0
                - (
                    time_difference_hours
                    / 24.0
                    * 100.0
                )
            )
        )

        score = (
            spatial_component * 0.70
            +
            temporal_component * 0.30
        )

        best_score = max(
            best_score,
            score
        )

    return best_score
# =========================================================
# REUSABLE ATTRIBUTION CALCULATION
# =========================================================

def calculate_attribution_for_spill(
    spill_uuid: str
):
    """
    Calculate, rank and save vessel attribution
    for a spill UUID.

    Returns:
        List of ranked vessel candidates.
    """

    # =====================================================
    # 1. GET SPILL
    # =====================================================

    spill_response = (
        supabase
        .table("spills")
        .select(
            "id, spill_code, "
            "centroid_latitude, "
            "centroid_longitude, "
            "detected_at, "
            "estimated_origin_at"
        )
        .eq("id", spill_uuid)
        .limit(1)
        .execute()
    )

    if not spill_response.data:

        raise ValueError(
            f"Spill '{spill_uuid}' not found"
        )

    spill = spill_response.data[0]

    spill_code = spill["spill_code"]

    spill_lat = float(
        spill["centroid_latitude"]
    )

    spill_lon = float(
        spill["centroid_longitude"]
    )

    # =====================================================
    # 2. SPILL TIME
    # =====================================================

    spill_time_string = (
        spill.get("estimated_origin_at")
        or spill.get("detected_at")
    )

    if not spill_time_string:

        raise ValueError(
            "Spill has no usable timestamp"
        )

    spill_time = parse_timestamp(
        spill_time_string
    )

    # =====================================================
    # 3. DRIFT POINTS
    # =====================================================

    drift_response = (
        supabase
        .table("spill_drift_points")
        .select(
            "latitude, longitude, "
            "timestamp, path_type"
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

    # =====================================================
    # 4. VESSEL POSITIONS
    # =====================================================

    positions_response = (
        supabase
        .table("vessel_positions")
        .select(
            "mmsi, timestamp, latitude, "
            "longitude, speed_knots, "
            "heading_deg"
        )
        .execute()
    )

    positions = (
        positions_response.data
        or []
    )

    if not positions:

        return []

    # =====================================================
    # 5. GROUP POSITIONS BY MMSI
    # =====================================================

    vessel_positions = {}

    for position in positions:

        mmsi = str(
            position["mmsi"]
        )

        if mmsi not in vessel_positions:

            vessel_positions[mmsi] = []

        vessel_positions[mmsi].append(
            position
        )

    # =====================================================
    # 6. VESSEL NAMES
    # =====================================================

    mmsis = list(
        vessel_positions.keys()
    )

    vessels_response = (
        supabase
        .table("vessels")
        .select(
            "mmsi, name"
        )
        .in_(
            "mmsi",
            mmsis
        )
        .execute()
    )

    vessel_names = {}

    for vessel in (
        vessels_response.data
        or []
    ):

        vessel_names[
            str(vessel["mmsi"])
        ] = (
            vessel.get("name")
            or "UNKNOWN VESSEL"
        )

    # =====================================================
    # 7. CALCULATE SCORES
    # =====================================================

    candidates = []

    best_positions = {}

    for mmsi, positions_for_vessel in (
        vessel_positions.items()
    ):

        best_position = None
        best_total = -1

        for position in positions_for_vessel:

            latitude = float(
                position["latitude"]
            )

            longitude = float(
                position["longitude"]
            )

            # -------------------------------------------------
            # Spatial
            # -------------------------------------------------

            distance_km = haversine_km(
                spill_lat,
                spill_lon,
                latitude,
                longitude
            )

            spatial_score = (
                calculate_spatial_score(
                    distance_km
                )
            )

            # -------------------------------------------------
            # Temporal
            # -------------------------------------------------

            vessel_time = parse_timestamp(
                position["timestamp"]
            )

            temporal_score = (
                calculate_temporal_score(
                    vessel_time,
                    spill_time
                )
            )

            # -------------------------------------------------
            # Trajectory
            # -------------------------------------------------

            trajectory_score = (
                calculate_trajectory_score(
                    latitude,
                    longitude,
                    drift_points
                )
            )

            # -------------------------------------------------
            # Behaviour
            # -------------------------------------------------

            behaviour_score = (
                calculate_behaviour_score(
                    position
                )
            )

            # -------------------------------------------------
            # Final score
            # -------------------------------------------------

            environment_score = calculate_environment_score(
    position,
    drift_points
) 
            final_score = (
    spatial_score * 0.25
    +
    temporal_score * 0.20
    +
    trajectory_score * 0.25
    +
    behaviour_score * 0.10
    +
    environment_score * 0.20
           )

            # -------------------------------------------------
            # Keep best position
            # -------------------------------------------------

            if final_score > best_total:

                best_total = final_score

                best_position = {
                    "position": position,
                    "distance_km": distance_km,
                    "spatial": spatial_score,
                    "temporal": temporal_score,
                    "trajectory": trajectory_score,
                    "environment": environment_score,
                    "behaviour": behaviour_score,
                    "final": final_score
                }

        if best_position:

            best_positions[mmsi] = (
                best_position
            )

            candidates.append(
                {
                    "mmsi": mmsi,

                    "vessel_name":
                        vessel_names.get(
                            mmsi,
                            "UNKNOWN VESSEL"
                        ),

                    "spatial_score":
                        round(
                            best_position["spatial"],
                            1
                        ),

                    "temporal_score":
                        round(
                            best_position["temporal"],
                            1
                        ),

                    "trajectory_score":
                        round(
                            best_position["trajectory"],
                            1
                        ),

                    "behaviour_score":
                        round(
                            best_position["behaviour"],
                            1
                        ),
                    "environment_score":
                        round( 
                            best_position["environment"],
                            1
                        ),
                    "final_score":
                        round(
                            best_position["final"],
                            1
                        )
                }
            )

    # =====================================================
    # 8. RANK
    # =====================================================

    candidates.sort(
        key=lambda x: x["final_score"],
        reverse=True
    )

    # =====================================================
    # 9. PREPARE DATABASE ROWS
    # =====================================================

    database_rows = []

    for rank, candidate in enumerate(
        candidates,
        start=1
    ):

        mmsi = candidate["mmsi"]

        best = best_positions[mmsi]

        position = best["position"]

        evidence = {

            "distance_km":
                round(
                    best["distance_km"],
                    3
                ),

            "vessel_position": {

                "latitude":
                    float(
                        position["latitude"]
                    ),

                "longitude":
                    float(
                        position["longitude"]
                    ),

                "timestamp":
                    position["timestamp"],

                "speed_knots":
                    (
                        float(
                            position["speed_knots"]
                        )
                        if position.get(
                            "speed_knots"
                        ) is not None
                        else None
                    ),

                "heading_deg":
                    (
                        float(
                            position["heading_deg"]
                        )
                        if position.get(
                            "heading_deg"
                        ) is not None
                        else None
                    )
            },

            "spill_position": {

                "latitude":
                    spill_lat,

                "longitude":
                    spill_lon
            },

            "weights": {

                "spatial":
                    0.30,

                "temporal":
                    0.25,

                "trajectory":
                    0.30,

                "behaviour":
                    0.15,
                "environment":
                    0.20

            },

            "drift_points_used":
                len(drift_points)
        }

        database_rows.append(
            {

                "spill_id":
                    spill_uuid,

                "mmsi":
                    int(mmsi),

                "spatial_score":
                    round(
                        best["spatial"],
                        2
                    ),

                "temporal_score":
                    round(
                        best["temporal"],
                        2
                    ),

                "trajectory_score":
                    round(
                        best["trajectory"],
                        2
                    ),

                "behaviour_score":
                    round(
                        best["behaviour"],
                        2
                    ),

                "environment_score":
                    round(
        best["environment"],
        2
                     ),

                "final_score":
                    round(
                        best["final"],
                        2
                    ),

                "rank":
                    rank,

                "evidence":
                    evidence,

                "model_version":
                    MODEL_VERSION
            }
        )

    # =====================================================
    # 10. SAVE TO DATABASE
    # =====================================================

    if database_rows:

        (
            supabase
            .table("attribution_scores")
            .upsert(
                database_rows,
                on_conflict="spill_id,mmsi"
            )
            .execute()
        )

    # =====================================================
    # 11. RETURN CANDIDATES
    # =====================================================

    return candidates


# =========================================================
# API ENDPOINT
# =========================================================

@router.get(
    "/spills/{spill_id}/attribution",
    response_model=AttributionResponse,
    summary="Get attribution scores for a specific spill"
)
def get_attribution(
    spill_id: str = Path(
        ...,
        description="The unique spill code",
        example="SP-001"
    )
):

    # =====================================================
    # Find spill UUID
    # =====================================================

    spill_response = (
        supabase
        .table("spills")
        .select("id, spill_code")
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

    spill_uuid = (
        spill_response.data[0]["id"]
    )

    # =====================================================
    # Calculate attribution
    # =====================================================

    try:

        candidates = (
            calculate_attribution_for_spill(
                spill_uuid
            )
        )

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    # =====================================================
    # Convert to response schema
    # =====================================================

    response_candidates = [

        VesselScore(
            mmsi=candidate["mmsi"],

            vessel_name=
                candidate["vessel_name"],

            spatial_score=
                candidate["spatial_score"],

            temporal_score=
                candidate["temporal_score"],

            trajectory_score=
                candidate["trajectory_score"],

            behaviour_score=
                candidate["behaviour_score"],
            environment_score=
                candidate["environment_score"],
            final_score=
                candidate["final_score"]
        )

        for candidate in candidates
    ]

    return AttributionResponse(
        spill_id=spill_id,
        candidates=response_candidates
    )