from fastapi import APIRouter
from app.schemas.spill import SpillResponse

router = APIRouter(
    prefix="/api/spills",
    tags=["Spills"]
)


MOCK_SPILL = SpillResponse(
    spill_id="SP-001",
    detected=True,
    confidence=0.96,
    area_km2=12.4,
    centroid={
        "latitude": 12.345,
        "longitude": 74.567
    },
    polygon=[
        [12.34, 74.56],
        [12.35, 74.56],
        [12.36, 74.57],
        [12.35, 74.58],
        [12.34, 74.57]
    ],
    estimated_time="2026-08-22T12:30:00"
)


@router.get("/{spill_id}", response_model=SpillResponse)
def get_spill(spill_id: str):

    if spill_id != MOCK_SPILL.spill_id:
        return {
            "error": "Spill not found"
        }

    return MOCK_SPILL