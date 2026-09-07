from pathlib import Path
import shutil

ROOT = Path.cwd()

image_dir = ROOT / "dataset" / "images"
label_root = ROOT / "yolo_segmentation" / "labels"
output_root = ROOT / "yolo_seg_dataset" / "images"

for split in ["train", "val"]:
    label_dir = label_root / split
    output_dir = output_root / split
    output_dir.mkdir(parents=True, exist_ok=True)

    copied = 0
    missing = []

    for label_file in label_dir.glob("*.txt"):
        image_file = image_dir / (label_file.stem + ".jpg")

        if image_file.exists():
            shutil.copy2(image_file, output_dir / image_file.name)
            copied += 1
        else:
            missing.append(label_file.stem)

    print(f"\n{split.upper()}")
    print(f"Labels found: {len(list(label_dir.glob('*.txt')))}")
    print(f"Images copied: {copied}")
    print(f"Images missing: {len(missing)}")

    if missing:
        print("First missing files:")
        for name in missing[:10]:
            print(name)