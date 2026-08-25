from pathlib import Path
import random
import shutil

IMAGE_DIR = Path("dataset/images")
LABEL_DIR = Path("dataset/labels")

OUTPUT_DIR = Path("yolo_dataset")

TRAIN_IMAGES = OUTPUT_DIR / "images/train"
VAL_IMAGES = OUTPUT_DIR / "images/val"

TRAIN_LABELS = OUTPUT_DIR / "labels/train"
VAL_LABELS = OUTPUT_DIR / "labels/val"

for folder in [
    TRAIN_IMAGES,
    VAL_IMAGES,
    TRAIN_LABELS,
    VAL_LABELS
]:
    folder.mkdir(parents=True, exist_ok=True)


# Find all images
images = list(IMAGE_DIR.glob("*.jpg"))

print(f"Found {len(images)} images.")


# Shuffle so the split is random
random.seed(42)
random.shuffle(images)


# 80% training, 20% validation
split = int(len(images) * 0.8)

train_images = images[:split]
val_images = images[split:]

print(f"Training images: {len(train_images)}")
print(f"Validation images: {len(val_images)}")


def copy_dataset(image_list, image_destination, label_destination):

    for image in image_list:

        # Copy image
        shutil.copy2(
            image,
            image_destination / image.name
        )

        # Find corresponding YOLO label
        label = LABEL_DIR / (image.stem + ".txt")

        destination_label = label_destination / label.name

        if label.exists():
            shutil.copy2(
                label,
                destination_label
            )
        else:
            # Empty label = no objects
            destination_label.write_text("")


copy_dataset(
    train_images,
    TRAIN_IMAGES,
    TRAIN_LABELS
)

copy_dataset(
    val_images,
    VAL_IMAGES,
    VAL_LABELS
)

print("\nYOLO dataset preparation complete!")