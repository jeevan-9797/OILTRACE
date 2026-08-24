from math import radians, sin, cos, sqrt, atan2
from datetime import datetime, timezone

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


# ---------------------------------------------------------
# Utility: Haversine distance
# Returns distance in kilometers
# ---------------------------------------------------------

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
        + cos(radians(lat1))
        * cos(radians(lat2))
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c


# ---------------------------------------------------------
# Spatial score
#
# Closer vessel to spill origin = higher score
# ---------------------------------------------------------

def calculate_spatial_score(distance_km: float) -> float:

    # 0 km -> 100
    # 50 km or more -> 0

    score = 100 - (distance_km / 50 * 100)

    return max(0, min(100, score))


# ---------------------------------------------------------
# Temporal score
#
# Vessel position closer in time to spill origin
# = higher score
# ---------------------------------------------------------

def calculate_temporal_score(
    vessel_time: datetime,
    spill_time: datetime
) -> float:

    difference_hours = abs(
        (vessel_time - spill_time).total_seconds()
    ) / 3600

    # Within 24 hours -> decreasing score
    score = 100 - (difference_hours / 24 * 100)

    return max(0, min(100, score))


# ---------------------------------------------------------
# Trajectory score
#
# Checks how close vessel positions are to spill drift path
# ---------------------------------------------------------

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

    # 50 km = zero score
    score = 100 - (minimum_distance / 50 * 100)

    return max(0, min(100, score))


# ---------------------------------------------------------
# Behaviour score
#
# Initial heuristic based on vessel movement.
# This can later be replaced by the ML/behaviour model.
# ---------------------------------------------------------

def calculate_behaviour_score(position: dict) -> float:

    speed = position.get("speed_knots")

    if speed is None:
        return 50

    speed = float(speed)

    # Normal moving vessel
    if 2 <= speed <= 25:
        return 80

    # Very slow / stationary
    if speed < 2:
        return 50

    # Unusually high speed
    return 60


# ---------------------------------------------------------
# Main attribution endpoint
# ---------------------------------------------------------

@router.get(
    "/spills/{spill_id}/attribution",
    response_model=AttributionResponse,
    summary="Get attribution scores for a specific spill"
)
def get_attribution(
    spill_id: str = Path(
        ...,
        description="The unique ID of the spill",
        example="SP-001"
    )
):

    # -----------------------------------------------------
    # 1. Get spill
    # -----------------------------------------------------

    spill_response = (
        supabase
        .table("spills")
        .select(
            "id, spill_code, centroid_latitude, "
            "centroid_longitude, detected_at, "
            "estimated_origin_at"
        )
        .eq("spill_code", spill_id)
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

    spill_lat = float(
        spill["centroid_latitude"]
    )

    spill_lon = float(
        spill["centroid_longitude"]
    )

    # Prefer estimated origin time
    spill_time_string = (
        spill.get("estimated_origin_at")
        or spill.get("detected_at")
    )

    if not spill_time_string:
        raise HTTPException(
            status_code=500,
            detail="Spill has no usable timestamp"
        )

    spill_time = datetime.fromisoformat(
        spill_time_string.replace("Z", "+00:00")
    )

    # -----------------------------------------------------
    # 2. Get spill drift points
    # -----------------------------------------------------

    drift_response = (
        supabase
        .table("spill_drift_points")
        .select(
            "latitude, longitude, timestamp, path_type"
        )
        .eq("spill_id", spill_uuid)
        .order("sequence_no")
        .execute()
    )

    drift_points = drift_response.data or []

    # -----------------------------------------------------
    # 3. Get vessel positions
    #
    # For first version, get recent positions.
    # -----------------------------------------------------

    positions_response = (
        supabase
        .table("vessel_positions")
        .select(
            "mmsi, timestamp, latitude, longitude, "
            "speed_knots, heading_deg"
        )
        .execute()
    )

    positions = positions_response.data or []

    if not positions:
        return AttributionResponse(
            spill_id=spill_id,
            candidates=[]
        )

    # -----------------------------------------------------
    # 4. Group positions by MMSI
    # -----------------------------------------------------

    vessel_positions = {}

    for position in positions:

        mmsi = str(position["mmsi"])

        if mmsi not in vessel_positions:
            vessel_positions[mmsi] = []

        vessel_positions[mmsi].append(position)

    # -----------------------------------------------------
    # 5. Get vessel metadata
    # -----------------------------------------------------

    mmsis = list(vessel_positions.keys())

    vessels_response = (
        supabase
        .table("vessels")
        .select("mmsi, name")
        .in_("mmsi", mmsis)
        .execute()
    )

    vessel_names = {}

    for vessel in vessels_response.data or []:

        vessel_names[
            str(vessel["mmsi"])
        ] = vessel.get("name") or "UNKNOWN VESSEL"

    # -----------------------------------------------------
    # 6. Calculate scores for each vessel
    # -----------------------------------------------------

    candidates = []

    for mmsi, positions_for_vessel in vessel_positions.items():

        best_position = None
        best_total = -1

        for position in positions_for_vessel:

            latitude = float(position["latitude"])
            longitude = float(position["longitude"])

            # -----------------------------
            # Spatial
            # -----------------------------

            distance_km = haversine_km(
                spill_lat,
                spill_lon,
                latitude,
                longitude
            )

            spatial_score = calculate_spatial_score(
                distance_km
            )

            # -----------------------------
            # Timestamp
            # -----------------------------

            timestamp_string = position["timestamp"]

            vessel_time = datetime.fromisoformat(
                timestamp_string.replace("Z", "+00:00")
            )

            temporal_score = calculate_temporal_score(
                vessel_time,
                spill_time
            )

            # -----------------------------
            # Trajectory
            # -----------------------------

            trajectory_score = calculate_trajectory_score(
                latitude,
                longitude,
                drift_points
            )

            # -----------------------------
            # Behaviour
            # -----------------------------

            behaviour_score = calculate_behaviour_score(
                position
            )

            # -----------------------------
            # Final score
            # -----------------------------

            final_score = (
                spatial_score * 0.30
                + temporal_score * 0.25
                + trajectory_score * 0.30
                + behaviour_score * 0.15
            )

            if final_score > best_total:

                best_total = final_score

                best_position = {
                    "position": position,
                    "spatial": spatial_score,
                    "temporal": temporal_score,
                    "trajectory": trajectory_score,
                    "behaviour": behaviour_score,
                    "final": final_score
                }

        # -------------------------------------------------
        # Add best result for vessel
        # -------------------------------------------------

        if best_position:

            candidates.append(
                VesselScore(
                    mmsi=mmsi,
                    vessel_name=vessel_names.get(
                        mmsi,
                        "UNKNOWN VESSEL"
                    ),
                    spatial_score=round(
                        best_position["spatial"],
                        1
                    ),
                    temporal_score=round(
                        best_position["temporal"],
                        1
                    ),
                    trajectory_score=round(
                        best_position["trajectory"],
                        1
                    ),
                    behaviour_score=round(
                        best_position["behaviour"],
                        1
                    ),
                    final_score=round(
                        best_position["final"],
                        1
                    )
                )
            )

    # -----------------------------------------------------
    # 7. Sort highest probability first
    # -----------------------------------------------------

    candidates.sort(
        key=lambda x: x.final_score,
        reverse=True
    )

    # -----------------------------------------------------
    # 8. Return API response
    # -----------------------------------------------------

    return AttributionResponse(
        spill_id=spill_id,
        candidates=candidates
    )