import re
import requests
from pathlib import Path
from collections import defaultdict

TAB_FILE = Path("DARTIS_2019.tab")
IMAGE_DIR = Path("dataset/images")
ANNOTATION_DIR = Path("dataset/annotations")

IMAGE_DIR.mkdir(parents=True, exist_ok=True)
ANNOTATION_DIR.mkdir(parents=True, exist_ok=True)

BASE_URL = "https://download.pangaea.de/dataset/980773/files/"

text = TAB_FILE.read_text(
    encoding="utf-8",
    errors="replace"
)

groups = defaultdict(dict)

# Read dataset
for line in text.splitlines():

    parts = line.split()

    if len(parts) >= 3 and parts[0] in ["oc", "ow", "nc", "nw"]:

        category = parts[0]
        jpg_name = parts[1]
        xml_name = parts[2]

        # Dictionary automatically removes duplicate JPG names
        groups[category][jpg_name] = xml_name


print("UNIQUE IMAGES AVAILABLE:")

for category in ["oc", "ow", "nc", "nw"]:
    print(category, "=", len(groups[category]))


# We want 50 UNIQUE images per category
selected = []

for category in ["oc", "ow", "nc", "nw"]:

    unique_images = list(groups[category].items())[:50]

    for jpg_name, xml_name in unique_images:
        selected.append((category, jpg_name, xml_name))


print("\nTarget:", len(selected), "unique images")


# Download
for i, (category, jpg_name, xml_name) in enumerate(selected, 1):

    jpg_path = IMAGE_DIR / jpg_name
    xml_path = ANNOTATION_DIR / xml_name

    # JPG
    if not jpg_path.exists():

        print(f"[{i}/{len(selected)}] {jpg_name}")

        response = requests.get(BASE_URL + jpg_name)
        response.raise_for_status()

        jpg_path.write_bytes(response.content)

    # XML
    if not xml_path.exists():

        response = requests.get(BASE_URL + xml_name)

        if response.status_code == 200:
            xml_path.write_bytes(response.content)


print("\nDOWNLOAD COMPLETE!")


# Final check
print("\nCURRENT UNIQUE IMAGES:")

for category in ["oc", "ow", "nc", "nw"]:

    count = 0

    for jpg_name in groups[category]:

        if (IMAGE_DIR / jpg_name).exists():
            count += 1

    print(category, "=", count)