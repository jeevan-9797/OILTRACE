from fastapi import APIRouter, HTTPException, Path

from app.schemas.spill import SpillResponse
from app.core.database import supabase


router = APIRouter(
    prefix="/api/spills",
    tags=["Spills"]
)


@router.get("/{spill_id}", response_model=SpillResponse)
def get_spill(
    spill_id: str = Path(
        ...,
        description="The unique ID of the spill",
        example="SP-001"
    )
):
    # Query the real Supabase database
    response = (
        supabase
        .table("spills")
        .select("*")
        .eq("spill_code", spill_id)
        .limit(1)
        .execute()
    )

    # Spill doesn't exist
    if not response.data:
        raise HTTPException(
            status_code=404,
            detail=f"Spill '{spill_id}' not found"
        )

    row = response.data[0]

    # Database stores GeoJSON coordinates as [longitude, latitude].
    # Our existing API contract uses [latitude, longitude].
    polygon = []

    if row.get("polygon"):
        coordinates = row["polygon"].get("coordinates", [[]])[0]

        polygon = [
            [point[1], point[0]]
            for point in coordinates
        ]

    return SpillResponse(
        spill_id=row["spill_code"],
        detected=row["detected"],
        confidence=row["confidence"],
        area_km2=row["area_km2"],
        centroid={
            "latitude": row["centroid_latitude"],
            "longitude": row["centroid_longitude"]
        },
        polygon=polygon,
        estimated_time=row.get("estimated_time")
    )