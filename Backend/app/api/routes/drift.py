from datetime import datetime
from fastapi import APIRouter, HTTPException, Path
from pydantic import BaseModel

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


MOCK_DRIFT = {
    "spill_id": "SP-001",
    "origin": {
        "latitude": 12.320,
        "longitude": 74.540
    },
    "historical_path": [
        {
            "latitude": 12.320,
            "longitude": 74.540,
            "timestamp": "2026-08-22T08:30:00"
        },
        {
            "latitude": 12.325,
            "longitude": 74.545,
            "timestamp": "2026-08-22T09:30:00"
        },
        {
            "latitude": 12.330,
            "longitude": 74.550,
            "timestamp": "2026-08-22T10:30:00"
        },
        {
            "latitude": 12.337,
            "longitude": 74.558,
            "timestamp": "2026-08-22T11:30:00"
        }
    ],
    "predicted_path": [
        {
            "latitude": 12.345,
            "longitude": 74.567,
            "timestamp": "2026-08-22T13:30:00"
        },
        {
            "latitude": 12.355,
            "longitude": 74.578,
            "timestamp": "2026-08-22T14:30:00"
        },
        {
            "latitude": 12.367,
            "longitude": 74.590,
            "timestamp": "2026-08-22T15:30:00"
        }
    ]
}


@router.get(
    "/spills/{spill_id}/drift",
    response_model=DriftResponse,
    summary="Get drift prediction path for a spill"
)
def get_drift(
    spill_id: str = Path(..., description="The unique ID of the spill", example="SP-001")
):
    if spill_id != "SP-001":
        raise HTTPException(
            status_code=404,
            detail=f"Spill '{spill_id}' not found"
        )

    # Indentation fixed here
    return MOCK_DRIFT