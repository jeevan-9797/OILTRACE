from fastapi import APIRouter, UploadFile, File, HTTPException

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
    if not image or not image.filename:
        raise HTTPException(
            status_code=400,
            detail="No image file provided"
        )

    # Validate file extension
    valid_extensions = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")
    filename_lower = image.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in valid_extensions):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Supported formats: {', '.join(valid_extensions)}"
        )

    image_bytes = await image.read()

    if not image_bytes or len(image_bytes) == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    try:
        result = detect_spill(
            image_bytes,
            image.filename
        )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Detection pipeline error: {str(e)}"
        )