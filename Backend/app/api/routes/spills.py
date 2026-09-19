import logging
import time
import traceback
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.spill_detection_service import detect_spill

logger = logging.getLogger("oiltrace.detect")

router = APIRouter(
    prefix="/api/spills",
    tags=["Spills"]
)


@router.post("/detect")
async def detect_oil_spill(
    image: UploadFile = File(...)
):
    endpoint_started = time.perf_counter()
    logger.info(
        "[DETECT] request received: filename=%s, content_type=%s",
        getattr(image, "filename", None),
        getattr(image, "content_type", None)
    )

    if not image or not image.filename:
        logger.warning("[DETECT] validation failed: No image file provided")
        raise HTTPException(
            status_code=400,
            detail="No image file provided"
        )

    # Validate file extension
    valid_extensions = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")
    filename_lower = image.filename.lower()
    if not any(filename_lower.endswith(ext) for ext in valid_extensions):
        logger.warning(
            "[DETECT] validation failed: Invalid extension for '%s'. Supported: %s",
            image.filename,
            valid_extensions
        )
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Supported formats: {', '.join(valid_extensions)}"
        )

    try:
        image_read_started = time.perf_counter()
        image_bytes = await image.read()
        logger.info(
            "[DETECT] image received (%d bytes)",
            len(image_bytes) if image_bytes else 0
        )
        logger.info(
            "[TIMING] image_load: %.2fs",
            time.perf_counter() - image_read_started,
        )
    except Exception as read_err:
        logger.error(
            "[DETECT] Failed to read uploaded image bytes: %s\n%s",
            read_err,
            traceback.format_exc()
        )
        raise HTTPException(
            status_code=400,
            detail=f"Failed to read uploaded image: {str(read_err)}"
        )

    if not image_bytes or len(image_bytes) == 0:
        logger.warning("[DETECT] validation failed: Uploaded file is empty")
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty"
        )

    try:
        result = detect_spill(
            image_bytes,
            image.filename
        )
        logger.info(
            "[DETECT] response ready: %d detection(s), %d spill(s) created for %s",
            len(result.get("detections", [])),
            result.get("spills_created", 0),
            image.filename
        )
        logger.info(
            "[TIMING] total: %.2fs",
            time.perf_counter() - endpoint_started,
        )
        return result
    except ValueError as e:
        logger.warning(
            "[DETECT] Validation/Value error: %s\n%s",
            e,
            traceback.format_exc()
        )
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(
            "[DETECT] Pipeline execution error: %s\n%s",
            e,
            traceback.format_exc()
        )
        raise HTTPException(
            status_code=500,
            detail=f"Detection pipeline error: {str(e)}"
        )
