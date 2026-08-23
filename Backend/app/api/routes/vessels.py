from fastapi import APIRouter
from app.schemas.vessel import Vessel

router = APIRouter(
    prefix="/api",
    tags=["Vessels"]
)


MOCK_VESSELS = [
    Vessel(
        mmsi="123456789",
        name="VESSEL ALPHA",
        latitude=12.350,
        longitude=74.570,
        speed=12.4,
        heading=183,
        timestamp="2026-08-22T12:30:00"
    ),
    Vessel(
        mmsi="234567890",
        name="VESSEL BRAVO",
        latitude=12.370,
        longitude=74.590,
        speed=9.8,
        heading=165,
        timestamp="2026-08-22T12:30:00"
    ),
    Vessel(
        mmsi="345678901",
        name="VESSEL CHARLIE",
        latitude=12.310,
        longitude=74.530,
        speed=14.1,
        heading=210,
        timestamp="2026-08-22T12:30:00"
    )
]


@router.get("/spills/{spill_id}/vessels", response_model=list[Vessel])
def get_vessels(spill_id: str):
    return MOCK_VESSELS