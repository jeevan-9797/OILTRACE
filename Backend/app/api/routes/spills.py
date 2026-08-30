from fastapi import APIRouter, UploadFile, File

from app.services.spill_detection_service import detect_spill

router = APIRouter(
    prefix="/api/spills",
    tags=["Spills"]
)


# OLD simple GET /api/spills/{spill_id} was removed.
# It conflicted with get_spill_details in spill_details.py,
# which returns the complete spill + drift + attribution + environment payload.
# The previous handler returned only:
# spill_id, detected, confidence, area_km2, centroid, polygon, estimated_time


@router.post("/detect")
async def detect_oil_spill(
    image: UploadFile = File(...)
):
    image_bytes = await image.read()

    result = detect_spill(
        image_bytes,
        image.filename
    )

    return result