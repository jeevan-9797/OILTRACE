import os
import tempfile

from app.core.database import supabase
from app.services.ai.inference import run_inference


SATELLITE_IMAGE_ID = "a1b2c3d4-e5f6-4a5b-8c9d-0e1f2a3b4c5d"


def detect_spill(image_bytes: bytes):
    temp_path = None

    try:
        # Save uploaded image temporarily
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".jpg"
        ) as temp_file:
            temp_file.write(image_bytes)
            temp_path = temp_file.name

        # Run YOLO inference
        result = run_inference(temp_path)

        # Save every YOLO detection into Supabase
        rows = []

        for index, detection in enumerate(result["detections"]):

            rows.append({
                "satellite_image_id": SATELLITE_IMAGE_ID,
                "detection_index": index,
                "confidence": detection["confidence"],
                "bbox": detection["bbox"],
                "centroid_pixels": detection["centroid"],
                "polygon_pixels": detection["polygon"],
                "area_pixels": detection["area_pixels"],
                "model_source": "YOLO"
            })

        if rows:
            supabase.table("ai_detections").insert(rows).execute()

        return result

    finally:
        # Remove temporary uploaded image
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)