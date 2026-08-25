import xml.etree.ElementTree as ET
from pathlib import Path

ANNOTATION_DIR = Path("dataset/annotations")
LABEL_DIR = Path("dataset/labels")

LABEL_DIR.mkdir(parents=True, exist_ok=True)

for xml_file in ANNOTATION_DIR.glob("*.xml"):

    tree = ET.parse(xml_file)
    root = tree.getroot()

    size = root.find("size")

    if size is None:
        continue

    width = int(size.find("width").text)
    height = int(size.find("height").text)

    yolo_lines = []

    for obj in root.findall("object"):

        name = obj.find("name").text.strip().lower()

        # Our only class is oil
        if name != "oil":
            continue

        box = obj.find("bndbox")

        xmin = float(box.find("xmin").text)
        ymin = float(box.find("ymin").text)
        xmax = float(box.find("xmax").text)
        ymax = float(box.find("ymax").text)

        # Convert VOC -> YOLO
        x_center = ((xmin + xmax) / 2) / width
        y_center = ((ymin + ymax) / 2) / height

        box_width = (xmax - xmin) / width
        box_height = (ymax - ymin) / height

        # YOLO class 0 = oil
        yolo_lines.append(
            f"0 {x_center:.6f} {y_center:.6f} "
            f"{box_width:.6f} {box_height:.6f}"
        )

    # Create corresponding .txt file
    label_file = LABEL_DIR / (xml_file.stem + ".txt")

    label_file.write_text(
        "\n".join(yolo_lines),
        encoding="utf-8"
    )

    print(f"Created: {label_file}")

print("\nXML → YOLO conversion complete!")