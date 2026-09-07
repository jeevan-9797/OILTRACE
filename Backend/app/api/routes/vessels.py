from fastapi import APIRouter, HTTPException, Path

from app.schemas.vessel import Vessel
from app.core.database import supabase


router = APIRouter(
    prefix="/api",
    tags=["Vessels"]
)


@router.get("/spills/{spill_id}/vessels", response_model=list[Vessel])
def get_vessels(
    spill_id: str = Path(
        ...,
        description="The unique ID of the spill",
        example="SP-001"
    )
):
    # First verify that the spill exists
    spill_response = (
        supabase
        .table("spills")
        .select("id, spill_code")
        .eq("spill_code", spill_id)
        .limit(1)
        .execute()
    )

    if not spill_response.data:
        raise HTTPException(
            status_code=404,
            detail=f"Spill '{spill_id}' not found"
        )

    # Get all vessels
    vessels_response = (
        supabase
        .table("vessels")
        .select("mmsi, name")
        .execute()
    )

    if not vessels_response.data:
        return []

    # Get vessel positions, newest first
    positions_response = (
        supabase
        .table("vessel_positions")
            .select(
                "mmsi, latitude, longitude, speed_knots, heading_deg, timestamp"
            )
        .order("timestamp", desc=True)
        .execute()
    )

    # Keep the latest position for each vessel
    latest_positions = {}

    for position in positions_response.data:
        mmsi = position["mmsi"]

        if mmsi not in latest_positions:
            latest_positions[mmsi] = position

    # Combine vessel information with latest position
    result = []

    for vessel in vessels_response.data:
        mmsi = vessel["mmsi"]
        position = latest_positions.get(mmsi)

        result.append(
            Vessel(
                mmsi=str(mmsi),
                name=vessel.get("name") or "UNKNOWN VESSEL",
                latitude=float(position["latitude"]) if position and position.get("latitude") is not None else None,
                longitude=float(position["longitude"]) if position and position.get("longitude") is not None else None,
                speed=float(position["speed_knots"]) if position and position.get("speed_knots") is not None else None,
                heading=float(position["heading_deg"]) if position and position.get("heading_deg") is not None else None,
                timestamp=str(position["timestamp"]) if position and position.get("timestamp") is not None else None
            )
        )

    return result