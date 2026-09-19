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

def _get_model_config():
    """Determine model version tag and path based on OILTRACE_MODEL env var (default: TRAIN2)."""
    model_choice = os.getenv("OILTRACE_MODEL", "TRAIN2").strip()
    if model_choice.upper() in ("TRAIN3", "TRAIN-3", "3"):
        model_name = "TRAIN3"
        train_folder = "train-3"
    else:
        model_name = "TRAIN2"
        train_folder = "train-2"

    base_dir = Path(__file__).resolve().parents[3]
    checkpoint_path = (
        base_dir
        / "runs"
        / "segment"
        / train_folder
        / "weights"
        / "best.pt"
    )
    if not checkpoint_path.exists() and len(Path(__file__).resolve().parents) > 4:
        root_path = (
            Path(__file__).resolve().parents[4]
            / "runs"
            / "segment"
            / train_folder
            / "weights"
            / "best.pt"
        )
        if root_path.exists():
            checkpoint_path = root_path

    return model_name, checkpoint_path


MODEL_NAME, MODEL_PATH = _get_model_config()

_model = None


def get_model():
    """Load the YOLO weights once and cache the instance."""
    global _model, MODEL_PATH, MODEL_NAME

    if _model is None:
        MODEL_NAME, MODEL_PATH = _get_model_config()
        if not MODEL_PATH.exists():
            logger.error("[DETECT] YOLO model weights not found at: %s", MODEL_PATH)
            raise FileNotFoundError(
                f"YOLO model not found: {MODEL_PATH}"
            )
        print(f"[DETECT] Checkpoint loaded: {MODEL_NAME} ({MODEL_PATH})")
        logger.info("[DETECT] Loading YOLO model weights [%s] from %s on CPU...", MODEL_NAME, MODEL_PATH)
        _model = YOLO(str(MODEL_PATH))
        logger.info("[DETECT] YOLO model loaded successfully into memory.")

    return _model


def warmup_model():
    """Perform one lightweight dummy inference on CPU to warm JIT kernels and avoid first-request latency."""
    model = get_model()
    try:
        dummy = np.zeros((512, 512, 3), dtype=np.uint8)
        with torch.inference_mode(), torch.no_grad():
            model.predict(
                source=dummy,
                conf=0.90,
                imgsz=512,
                device="cpu",
                verbose=False,
                save=False,
                stream=False,
                max_det=1,
                retina_masks=False
            )
        del dummy
        gc.collect()
        logger.info("[STARTUP] YOLO model warm-up completed successfully.")
    except Exception as e:
        logger.warning("[STARTUP] YOLO model warm-up deferred: %s", e)


def run_inference(image_path, confidence=0.20):
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
    imgsz = 512
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