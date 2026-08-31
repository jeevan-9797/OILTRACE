from datetime import datetime, timedelta, timezone
from math import radians, sin, cos, sqrt, atan2, asin

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from app.core.database import supabase


router = APIRouter(
    prefix="/api",
    tags=["Drift"]
)


# =========================================================
# CONFIGURATION
# =========================================================

EARTH_RADIUS_KM = 6371.0

# 1 knot = 1.852 km/h
KNOT_TO_KMH = 1.852

# Small contribution from wind to surface drift
WIND_DRIFT_FACTOR = 0.03

# Number of FUTURE prediction points
PREDICTION_POINTS = 5

# Time between predictions
STEP_HOURS = 3

MODEL_SOURCE = "environmental-drift-v1"


# =========================================================
# API SCHEMAS
# =========================================================

class Coordinates(BaseModel):
    latitude: float
    longitude: float


class TrajectoryPoint(Coordinates):
    timestamp: datetime


class DriftResponse(BaseModel):
    spill_id: str
    origin: Coordinates
    historical_path: list[TrajectoryPoint]
    predicted_path: list[TrajectoryPoint]


# =========================================================
# MOVE GEOGRAPHIC POINT
# =========================================================

def move_point(
    latitude: float,
    longitude: float,
    distance_km: float,
    bearing_deg: float
):
    """
    Move a geographic point by distance_km
    along bearing_deg.

    Bearing:
        0   = North
        90  = East
        180 = South
        270 = West

    Returns:
        (latitude, longitude)
    """

    lat1 = radians(latitude)
    lon1 = radians(longitude)
    bearing = radians(bearing_deg)

    angular_distance = (
        distance_km / EARTH_RADIUS_KM
    )

    # -----------------------------------------------------
    # New latitude
    # -----------------------------------------------------

    lat2_value = (
        sin(lat1) * cos(angular_distance)
        +
        cos(lat1)
        * sin(angular_distance)
        * cos(bearing)
    )

    # Protect against floating-point errors
    lat2_value = max(
        -1.0,
        min(1.0, lat2_value)
    )

    lat2 = asin(lat2_value)

    # -----------------------------------------------------
    # New longitude
    # -----------------------------------------------------

    lon2 = lon1 + atan2(
        sin(bearing)
        * sin(angular_distance)
        * cos(lat1),

        cos(angular_distance)
        -
        sin(lat1) * sin(lat2)
    )

    # Normalize longitude to -180 ... +180
    lon2 = (
        lon2 + 3.141592653589793
    ) % (
        2 * 3.141592653589793
    ) - 3.141592653589793

    return (
        lat2 * 180.0 / 3.141592653589793,
        lon2 * 180.0 / 3.141592653589793
    )


# =========================================================
# FIND NEAREST ENVIRONMENTAL DATA
# =========================================================

def get_nearest_environment(
    latitude: float,
    longitude: float,
    timestamp: datetime
):
    """
    Find the closest weather/ocean observation
    based on location and time.
    """

    response = (
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

    records = response.data or []

    if not records:
        return None

    best_record = None
    best_score = float("inf")

    for record in records:

        record_lat = float(
            record["latitude"]
        )

        record_lon = float(
            record["longitude"]
        )

        record_time = datetime.fromisoformat(
            str(record["timestamp"])
            .replace("Z", "+00:00")
        )

        if record_time.tzinfo is None:
            record_time = record_time.replace(
                tzinfo=timezone.utc
            )

        # -------------------------------------------------
        # Spatial difference
        # -------------------------------------------------

        lat_difference = (
            record_lat - latitude
        )

        lon_difference = (
            record_lon - longitude
        )

        spatial_score = (
            lat_difference ** 2
            + lon_difference ** 2
        )

        # -------------------------------------------------
        # Temporal difference
        # -------------------------------------------------

        temporal_difference = abs(
            (
                record_time - timestamp
            ).total_seconds()
        ) / 3600.0

        # -------------------------------------------------
        # Combined score
        # -------------------------------------------------

        score = (
            spatial_score
            + temporal_difference / 100.0
        )

        if score < best_score:

            best_score = score
            best_record = record

    return best_record


# =========================================================
# CALCULATE ONE DRIFT STEP
# =========================================================

def calculate_drift_step(
    latitude: float,
    longitude: float,
    timestamp: datetime,
    hours: float
):
    """
    Calculate one environmental drift step.

    Ocean current:
        Main movement

    Wind:
        Small secondary surface-drift contribution
    """

    environment = get_nearest_environment(
        latitude,
        longitude,
        timestamp
    )

    # -----------------------------------------------------
    # No environmental data
    # -----------------------------------------------------

    if not environment:

        return (
            latitude,
            longitude,
            None,
            0.30
        )

    # -----------------------------------------------------
    # Current
    # -----------------------------------------------------

    current_speed = float(
        environment.get("current_speed") or 0
    )

    current_direction = float(
        environment.get("current_direction") or 0
    )

    # -----------------------------------------------------
    # Wind
    # -----------------------------------------------------

    wind_speed = float(
        environment.get("wind_speed") or 0
    )

    wind_direction = float(
        environment.get("wind_direction") or 0
    )

    # -----------------------------------------------------
    # Current displacement
    #
    # Current speed is treated as knots.
    # -----------------------------------------------------

    current_distance_km = (
        current_speed
        * KNOT_TO_KMH
        * hours
    )

    # -----------------------------------------------------
    # Wind displacement
    # -----------------------------------------------------

    wind_drift_speed = (
        wind_speed
        * WIND_DRIFT_FACTOR
    )

    wind_distance_km = (
        wind_drift_speed
        * KNOT_TO_KMH
        * hours
    )

    # -----------------------------------------------------
    # Current vector
    # -----------------------------------------------------

    current_angle = radians(
        current_direction
    )

    current_x = (
        current_distance_km
        * sin(current_angle)
    )

    current_y = (
        current_distance_km
        * cos(current_angle)
    )

    # -----------------------------------------------------
    # Wind vector
    # -----------------------------------------------------

    wind_angle = radians(
        wind_direction
    )

    wind_x = (
        wind_distance_km
        * sin(wind_angle)
    )

    wind_y = (
        wind_distance_km
        * cos(wind_angle)
    )

    # -----------------------------------------------------
    # Combine current + wind
    # -----------------------------------------------------

    total_x = (
        current_x + wind_x
    )

    total_y = (
        current_y + wind_y
    )

    total_distance_km = sqrt(
        total_x ** 2
        + total_y ** 2
    )

    # -----------------------------------------------------
    # No movement
    # -----------------------------------------------------

    if total_distance_km <= 0:

        return (
            latitude,
            longitude,
            environment,
            0.30
        )

    # -----------------------------------------------------
    # Resulting bearing
    # -----------------------------------------------------

    bearing = atan2(
        total_x,
        total_y
    ) * 180.0 / 3.141592653589793

    bearing = (
        bearing + 360.0
    ) % 360.0

    # -----------------------------------------------------
    # Move point
    # -----------------------------------------------------

    new_latitude, new_longitude = move_point(
        latitude,
        longitude,
        total_distance_km,
        bearing
    )

    # -----------------------------------------------------
    # Confidence
    # -----------------------------------------------------

    confidence = 0.75

    if current_speed > 0:
        confidence += 0.05

    if wind_speed > 0:
        confidence += 0.03

    confidence = min(
        confidence,
        0.95
    )

    return (
        new_latitude,
        new_longitude,
        environment,
        confidence
    )


# =========================================================
# GENERATE DRIFT FOR SPILL
# =========================================================

def generate_drift_for_spill(
    spill_id: str
):
    """
    Generate environmental predictions for a spill.

    Existing origin/historical points are preserved.

    Existing predicted points are removed.

    New environmental predictions begin from the
    latest historical observation.
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
        .eq("id", spill_id)
        .limit(1)
        .execute()
    )

    if not spill_response.data:

        raise ValueError(
            f"Spill '{spill_id}' not found"
        )

    spill = spill_response.data[0]

    spill_uuid = spill["id"]

    # =====================================================
    # 2. GET EXISTING DRIFT POINTS
    # =====================================================

    existing_response = (
        supabase
        .table("spill_drift_points")
        .select(
            "id, spill_id, sequence_no, "
            "latitude, longitude, timestamp, "
            "path_type, model_source, confidence"
        )
        .eq("spill_id", spill_uuid)
        .order("timestamp")
        .execute()
    )

    existing_points = (
        existing_response.data or []
    )

    # =====================================================
    # 3. KEEP ONLY ORIGIN + HISTORICAL
    #
    # Old predicted points are removed below.
    # =====================================================

    historical_points = [
        point
        for point in existing_points
        if point["path_type"] in (
            "origin",
            "historical"
        )
    ]

    # =====================================================
    # 4. IF NO HISTORICAL DATA EXISTS
    #
    # Create origin from spill centroid.
    # =====================================================

    if not historical_points:

        latitude = float(
            spill["centroid_latitude"]
        )

        longitude = float(
            spill["centroid_longitude"]
        )

        timestamp_value = (
            spill.get("estimated_origin_at")
            or spill.get("detected_at")
        )

        if not timestamp_value:

            raise ValueError(
                "Spill has no usable timestamp"
            )

        start_time = datetime.fromisoformat(
            str(timestamp_value)
            .replace("Z", "+00:00")
        )

        if start_time.tzinfo is None:

            start_time = start_time.replace(
                tzinfo=timezone.utc
            )

        historical_points = [
            {
                "sequence_no": 1,
                "latitude": latitude,
                "longitude": longitude,
                "timestamp": start_time.isoformat(),
                "path_type": "origin",
                "model_source": "spill-detection",
                "confidence": 0.95
            }
        ]

    # =====================================================
    # 5. FIND LAST OBSERVED POINT
    # =====================================================

    def parse_timestamp(point):

        value = point["timestamp"]

        parsed = datetime.fromisoformat(
            str(value).replace(
                "Z",
                "+00:00"
            )
        )

        if parsed.tzinfo is None:

            parsed = parsed.replace(
                tzinfo=timezone.utc
            )

        return parsed

    latest_historical = max(
        historical_points,
        key=parse_timestamp
    )

    current_latitude = float(
        latest_historical["latitude"]
    )

    current_longitude = float(
        latest_historical["longitude"]
    )

    current_time = parse_timestamp(
        latest_historical
    )

    # =====================================================
    # 6. NEXT SEQUENCE NUMBER
    # =====================================================

    max_sequence = max(
        int(point["sequence_no"])
        for point in historical_points
    )

    next_sequence = (
        max_sequence + 1
    )

    # =====================================================
    # 7. DELETE OLD PREDICTIONS
    #
    # This removes the previous mock prediction and
    # previous environmental predictions.
    #
    # Historical/origin points remain untouched.
    # =====================================================

    (
        supabase
        .table("spill_drift_points")
        .delete()
        .eq("spill_id", spill_uuid)
        .eq("path_type", "predicted")
        .execute()
    )

    # =====================================================
    # 8. GENERATE NEW ENVIRONMENTAL PREDICTIONS
    # =====================================================

    generated_points = []

    for index in range(
        PREDICTION_POINTS
    ):

        current_time = (
            current_time
            + timedelta(
                hours=STEP_HOURS
            )
        )

        (
            new_latitude,
            new_longitude,
            environment,
            confidence
        ) = calculate_drift_step(
            current_latitude,
            current_longitude,
            current_time,
            STEP_HOURS
        )

        generated_points.append(
            {
                "spill_id": spill_uuid,
                "sequence_no": next_sequence,
                "latitude": new_latitude,
                "longitude": new_longitude,
                "timestamp": current_time.isoformat(),
                "path_type": "predicted",
                "model_source": MODEL_SOURCE,
                "confidence": confidence
            }
        )

        # Move to the new point for the next step
        current_latitude = new_latitude
        current_longitude = new_longitude

        next_sequence += 1

    # =====================================================
    # 9. INSERT NEW PREDICTIONS
    # =====================================================

    if generated_points:

        insert_response = (
            supabase
            .table("spill_drift_points")
            .insert(generated_points)
            .execute()
        )

        if not insert_response.data:

            raise RuntimeError(
                "Failed to save drift predictions"
            )

        return insert_response.data

    return []


# =========================================================
# DRIFT API ENDPOINT
# =========================================================

@router.get(
    "/spills/{spill_id}/drift",
    response_model=DriftResponse,
    summary="Get drift prediction path for a spill"
)
def get_drift(
    spill_id: str = Path(
        ...,
        description="The unique spill code",
        example="SP-001"
    )
):

    # =====================================================
    # 1. FIND SPILL USING SPILL CODE
    # =====================================================

    spill_response = (
        supabase
        .table("spills")
        .select(
            "id, spill_code, "
            "centroid_latitude, "
            "centroid_longitude"
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

    # =====================================================
    # 2. GET ALL DRIFT POINTS
    # =====================================================

    drift_response = (
        supabase
        .table("spill_drift_points")
        .select(
            "sequence_no, latitude, "
            "longitude, timestamp, "
            "path_type"
        )
        .eq("spill_id", spill_uuid)
        .order("sequence_no")
        .execute()
    )

    points = (
        drift_response.data or []
    )

    # =====================================================
    # 3. CONVERT TO API OBJECTS
    # =====================================================

    historical_path = []
    predicted_path = []

    for point in points:

        trajectory_point = TrajectoryPoint(
            latitude=float(
                point["latitude"]
            ),
            longitude=float(
                point["longitude"]
            ),
            timestamp=datetime.fromisoformat(
                str(point["timestamp"])
                .replace(
                    "Z",
                    "+00:00"
                )
            )
        )

        if point["path_type"] in (
            "origin",
            "historical"
        ):

            historical_path.append(
                trajectory_point
            )

        elif point["path_type"] == "predicted":

            predicted_path.append(
                trajectory_point
            )

    # =====================================================
    # 4. SORT PATHS
    # =====================================================

    historical_path.sort(
        key=lambda point: point.timestamp
    )

    predicted_path.sort(
        key=lambda point: point.timestamp
    )

    # =====================================================
    # 5. ORIGIN
    #
    # Use first historical/origin point if available.
    # =====================================================

    if historical_path:

        origin = Coordinates(
            latitude=historical_path[0].latitude,
            longitude=historical_path[0].longitude
        )

    else:

        origin = Coordinates(
            latitude=float(
                spill["centroid_latitude"]
            ),
            longitude=float(
                spill["centroid_longitude"]
            )
        )

    # =====================================================
    # 6. RETURN RESPONSE
    # =====================================================

    return DriftResponse(
        spill_id=spill["spill_code"],
        origin=origin,
        historical_path=historical_path,
        predicted_path=predicted_path
    )