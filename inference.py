from ultralytics import YOLO
import json
import cv2


MODEL_PATH = r"runs\segment\train-2\weights\best.pt"

# Load model once when this module is imported
model = YOLO(MODEL_PATH)


def run_inference(image_path, confidence=0.10):
    """
    Run oil-spill segmentation on one image.

    Parameters:
        image_path (str): Path to the input image.
        confidence (float): Detection confidence threshold.

    Returns:
        dict: JSON-serializable detection result.
    """

    image = cv2.imread(image_path)

    if image is None:
        raise ValueError(f"Could not read image: {image_path}")

    height, width = image.shape[:2]

    results = model.predict(
        source=image,
        conf=confidence,
        verbose=False
    )

    result = results[0]

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

    return {
        "image_width": int(width),
        "image_height": int(height),
        "detections": detections
    }


# Local testing only
if __name__ == "__main__":

    test_image = (
        r"yolo_seg_dataset\images\val"
        r"\nc-0023-00-000023.jpg"
    )

    print("Running local inference test...")

    output = run_inference(test_image)

    print(json.dumps(output, indent=2))

    print("INFERENCE COMPLETE")