from fastapi import APIRouter
from app.schemas.attribution import (
    AttributionResponse,
    VesselScore
)

router = APIRouter(
    prefix="/api",
    tags=["Attribution"]
)


MOCK_ATTRIBUTION = AttributionResponse(
    spill_id="SP-001",
    candidates=[
        VesselScore(
            mmsi="123456789",
            vessel_name="VESSEL ALPHA",
            spatial_score=94,
            temporal_score=96,
            trajectory_score=91,
            behaviour_score=83,
            final_score=91.4
        ),
        VesselScore(
            mmsi="234567890",
            vessel_name="VESSEL BRAVO",
            spatial_score=81,
            temporal_score=72,
            trajectory_score=88,
            behaviour_score=69,
            final_score=77.5
        ),
        VesselScore(
            mmsi="345678901",
            vessel_name="VESSEL CHARLIE",
            spatial_score=64,
            temporal_score=91,
            trajectory_score=61,
            behaviour_score=72,
            final_score=72.0
        )
    ]
)


@router.get(
    "/spills/{spill_id}/attribution",
    response_model=AttributionResponse
)
def get_attribution(spill_id: str):

    if spill_id != MOCK_ATTRIBUTION.spill_id:
        return {
            "error": "Attribution data not found"
        }

    return MOCK_ATTRIBUTION