from fastapi import APIRouter, HTTPException, Path
from app.schemas.attribution import (
    AttributionResponse,
    VesselScore
)

router = APIRouter(
    prefix="/api",
    tags=["Attribution"]
)


def get_mock_attribution(spill_id: str) -> AttributionResponse:
    return AttributionResponse(
        spill_id=spill_id,
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
    response_model=AttributionResponse,
    summary="Get attribution scores for a specific spill"
)
def get_attribution(
    spill_id: str = Path(..., description="The unique ID of the spill", example="SP-001")
):
    if spill_id != "SP-001":
        raise HTTPException(
            status_code=404,
            detail=f"Spill '{spill_id}' not found"
        )

    return get_mock_attribution(spill_id)