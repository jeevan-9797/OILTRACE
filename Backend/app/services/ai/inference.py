import gc
import json
import logging
import os
from pathlib import Path
import time
import cv2
import numpy as np
import torch
from ultralytics import YOLO

logger = logging.getLogger("oiltrace.ai")

# Restrict PyTorch and BLAS/OpenMP thread allocation to prevent high memory usage on low-memory servers
try:
    torch.set_num_threads(1)
except Exception:
    pass

MODEL_PATH = (
    Path(__file__).resolve().parents[3]
    / "runs"
    / "segment"
    / "train-2"
    / "weights"
    / "best.pt"
)

_model = None


def get_model():
    """Load the YOLO weights once and cache the instance."""
    global _model

    if _model is None:
        if not MODEL_PATH.exists():
            logger.error("[DETECT] YOLO model weights not found at: %s", MODEL_PATH)
            raise FileNotFoundError(
                f"YOLO model not found: {MODEL_PATH}"
            )
        logger.info("[DETECT] Loading YOLO model weights from %s on CPU...", MODEL_PATH)
        _model = YOLO(str(MODEL_PATH))
        logger.info("[DETECT] YOLO model loaded successfully into memory.")

    return _model





def run_inference(image_path, confidence=0.10):
    """
    Run oil-spill segmentation on one image with minimal memory footprint.

    Parameters:
        image_path (str): Path to the input image.
        confidence (float): Detection confidence threshold.

    Returns:
        dict: JSON-serializable detection result.
    """
    logger.info("[DETECT] image decoded: %s", image_path)
    model = get_model()
    logger.info("[DETECT] model ready")

    task = getattr(model, "task", "segment")
    imgsz = 640
    logger.info(
        "[DETECT] inference started (confidence=%s, imgsz=%d, task=%s, device=cpu)",
        confidence,
        imgsz,
        task
    )

    t_start = time.perf_counter()
    logger.info("[DETECT] calling model.predict")

    with torch.inference_mode(), torch.no_grad():
        results = model.predict(
            source=str(image_path),
            conf=confidence,
            imgsz=imgsz,
            device="cpu",
            verbose=False,
            save=False,
            stream=False,
            max_det=50,
            retina_masks=False
        )

    t_predict = time.perf_counter() - t_start
    logger.info("[DETECT] model.predict returned in %.3fs", t_predict)
    logger.info("[DETECT] inference completed")

    result = results[0]
    height, width = result.orig_shape[:2]

    detections = []

    if result.boxes is not None and len(result.boxes) > 0:
        boxes = result.boxes.xyxy.cpu().tolist()
        confidences = result.boxes.conf.cpu().tolist()
        polygons = result.masks.xy if result.masks is not None else None

        for i, (box, confidence_value) in enumerate(
            zip(boxes, confidences)
        ):
            x1, y1, x2, y2 = box

            centroid_x = (x1 + x2) / 2
            centroid_y = (y1 + y2) / 2

            polygon = None
            area_pixels = None

            if polygons is not None and i < len(polygons):
                polygon = [
                    [float(x), float(y)]
                    for x, y in polygons[i]
                ]

                area_pixels = float(
                    abs(cv2.contourArea(polygons[i].astype("float32")))
                )

            detections.append({
                "confidence": float(confidence_value),
                "bbox": [
                    float(x1),
                    float(y1),
                    float(x2),
                    float(y2)
                ],
                "centroid": [
                    float(centroid_x),
                    float(centroid_y)
                ],
                "area_pixels": area_pixels,
                "polygon": polygon
            })

    num_detections = len(detections)
    logger.info(
        "[DETECT] mask/polygon processing completed: %d detection(s) found (%dx%d)",
        num_detections,
        width,
        height
    )

    # Explicitly release references to PyTorch/Ultralytics result objects
    del results
    del result
    gc.collect()

    return {
        "image_width": int(width),
        "image_height": int(height),
        "detections": detections
    }


# Local testing only
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_image = (
        r"yolo_seg_dataset\images\val"
        r"\nc-0023-00-000023.jpg"
    )

    print("Running local inference test...")

    output = run_inference(test_image)

    print(json.dumps(output, indent=2))

    print("INFERENCE COMPLETE")