import csv
import re
from pathlib import Path

TAB_FILE = Path("DARTIS_2019.tab")
IMAGE_DIR = Path("yolo_seg_dataset/images")
OUTPUT_FILE = Path("image_geospatial_metadata.csv")

# All images actually present in our project
image_files = {
    p.name
    for p in IMAGE_DIR.rglob("*")
    if p.suffix.lower() in [".jpg", ".jpeg", ".png"]
}

metadata = {}

with open(TAB_FILE, "r", encoding="utf-8", errors="replace") as f:

    for line in f:

        line = line.strip()

        if not line:
            continue

        parts = re.split(r"\s+", line)

        # Find JPG filename
        image_name = next(
            (
                p for p in parts
                if p.lower().endswith((".jpg", ".jpeg", ".png"))
            ),
            None
        )

        if image_name not in image_files:
            continue

        try:
            image_index = parts.index(image_name)
        except ValueError:
            continue

        # Find the 640 640 dimensions
        width_index = None

        for i in range(image_index, len(parts) - 1):

            if parts[i] == "640" and parts[i + 1] == "640":
                width_index = i
                break

        if width_index is None:
            continue

        # According to the DARTIS header:
        #
        # patch_ul_lon
        # patch_ul_lat
        # patch_ur_lon
        # patch_ur_lat
        # patch_br_lon
        # patch_br_lat
        # patch_bl_lon
        # patch_bl_lat

        try:

            coords = [
                float(parts[width_index + 2]),
                float(parts[width_index + 3]),
                float(parts[width_index + 4]),
                float(parts[width_index + 5]),
                float(parts[width_index + 6]),
                float(parts[width_index + 7]),
                float(parts[width_index + 8]),
                float(parts[width_index + 9]),
            ]

        except (ValueError, IndexError):
            continue

        # Keep one geographic entry per image
        metadata[image_name] = {
            "image": image_name,
            "width": 640,
            "height": 640,

            "ul_lon": coords[0],
            "ul_lat": coords[1],

            "ur_lon": coords[2],
            "ur_lat": coords[3],

            "br_lon": coords[4],
            "br_lat": coords[5],

            "bl_lon": coords[6],
            "bl_lat": coords[7],
        }


fieldnames = [
    "image",
    "width",
    "height",
    "ul_lon",
    "ul_lat",
    "ur_lon",
    "ur_lat",
    "br_lon",
    "br_lat",
    "bl_lon",
    "bl_lat",
]

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as f:

    writer = csv.DictWriter(f, fieldnames=fieldnames)

    writer.writeheader()

    for image_name in sorted(metadata):
        writer.writerow(metadata[image_name])


print("==========================================")
print("DARTIS GEOSPATIAL CSV CREATED")
print("==========================================")
print(f"Images in YOLO dataset : {len(image_files)}")
print(f"Metadata entries       : {len(metadata)}")
print(f"Images without metadata: {len(image_files - metadata.keys())}")
print(f"CSV                    : {OUTPUT_FILE}")
print("==========================================")