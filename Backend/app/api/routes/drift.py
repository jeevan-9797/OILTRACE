from datetime import datetime

from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

from app.core.database import supabase


router = APIRouter(
    prefix="/api",
    tags=["Drift"]
)


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

    # 1. Find the spill using its human-readable spill code
    spill_result = (
        supabase
        .table("spills")
        .select(
            "id, spill_code, centroid_latitude, centroid_longitude, estimated_origin_at"
        )
        .eq("spill_code", spill_id)
        .limit(1)
        .execute()
    )

    if not spill_result.data:
        raise HTTPException(
            status_code=404,
            detail=f"Spill '{spill_id}' not found"
        )

    spill = spill_result.data[0]

    # 2. Get the UUID of the spill
    spill_uuid = spill["id"]

    # 3. Get drift points belonging to this spill
    drift_result = (
        supabase
        .table("spill_drift_points")
        .select(
            "sequence_no, latitude, longitude, timestamp"
        )
        .eq("spill_id", spill_uuid)
        .order("sequence_no")
        .execute()
    )

    points = drift_result.data

    # 4. Convert database points into API objects
    trajectory = [
        TrajectoryPoint(
            latitude=point["latitude"],
            longitude=point["longitude"],
            timestamp=point["timestamp"]
        )
        for point in points
    ]

    # 5. Split historical/predicted using estimated_origin_at
    origin_time = datetime.fromisoformat(
    spill["estimated_origin_at"].replace("Z", "+00:00")
)
    historical_path = [
        point
        for point in trajectory
        if point.timestamp <= origin_time
    ]

    predicted_path = [
        point
        for point in trajectory
        if point.timestamp > origin_time
    ]

    # 6. Return API response
    return DriftResponse(
        spill_id=spill["spill_code"],
        origin=Coordinates(
            latitude=spill["centroid_latitude"],
            longitude=spill["centroid_longitude"]
        ),
        historical_path=historical_path,
        predicted_path=predicted_path
    )