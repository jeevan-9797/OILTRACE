from pathlib import Path

LABEL_ROOT = Path("yolo_dataset/labels")
SEG_ROOT = Path("yolo_segmentation/labels")

for split in ["train", "val"]:
    src_dir = LABEL_ROOT / split
    dst_dir = SEG_ROOT / split
    dst_dir.mkdir(parents=True, exist_ok=True)

    for label_file in src_dir.glob("*.txt"):
        output_lines = []

        for line in label_file.read_text().splitlines():
            parts = line.split()

            if len(parts) != 5:
                continue

            cls, xc, yc, w, h = map(float, parts)

            x1 = xc - w / 2
            y1 = yc - h / 2
            x2 = xc + w / 2
            y2 = yc + h / 2

            polygon = [
                x1, y1,
                x2, y1,
                x2, y2,
                x1, y2
            ]

            output_lines.append(
                f"{int(cls)} " +
                " ".join(f"{p:.6f}" for p in polygon)
            )

        (dst_dir / label_file.name).write_text(
            "\n".join(output_lines)
        )

print("Bounding boxes converted to segmentation polygons!")