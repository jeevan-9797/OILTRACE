from app.schemas.spill_detection import SpillDetectionResult


def detect_spill(image_bytes: bytes) -> SpillDetectionResult:
    # Temporary implementation.
    # Replace this with the real YOLO inference tomorrow.

    return SpillDetectionResult(
        confidence=0.94,
        bbox=[100.0, 120.0, 450.0, 380.0],
        centroid=[275.0, 250.0],
        area=91000.0,
        polygon=None
    )