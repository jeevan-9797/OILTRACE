from pathlib import Path

import pandas as pd
from pyproj import Geod


GEOD = Geod(ellps="WGS84")


METADATA_PATH = (
    Path(__file__).resolve().parents[3]
    / "data"
    / "image_geospatial_metadata.csv"
)


def get_image_metadata(image_name: str) -> dict:
    """
    Find DARTIS geographic metadata for an image.

    The CSV stores longitude and latitude separately.

    Internally corners are returned as:
        (longitude, latitude)

    DARTIS corner order:
        UL = top-left
        UR = top-right
        BR = bottom-right
        BL = bottom-left
    """

    if not METADATA_PATH.exists():
        raise FileNotFoundError(
            f"DARTIS metadata file not found: {METADATA_PATH}"
        )

    df = pd.read_csv(METADATA_PATH)

    matches = df[df["image"] == image_name]

    if matches.empty:
        raise ValueError(
            f"No DARTIS metadata found for image: {image_name}"
        )

    row = matches.iloc[0]

    return {
        "width": int(row["width"]),
        "height": int(row["height"]),

        # IMPORTANT:
        # CSV columns are lon/lat.
        # Internal format is (longitude, latitude).

        "ul": (
            float(row["ul_lon"]),
            float(row["ul_lat"])
        ),

        "ur": (
            float(row["ur_lon"]),
            float(row["ur_lat"])
        ),

        "br": (
            float(row["br_lon"]),
            float(row["br_lat"])
        ),

        "bl": (
            float(row["bl_lon"]),
            float(row["bl_lat"])
        )
    }


def pixel_to_geo(
    x: float,
    y: float,
    width: int,
    height: int,
    corners: dict
):
    """
    Convert image pixel coordinates to
    [latitude, longitude].

    corners are stored internally as:
        (longitude, latitude)
    """

    u = x / (width - 1)
    v = y / (height - 1)

    ul_lon, ul_lat = corners["ul"]
    ur_lon, ur_lat = corners["ur"]
    br_lon, br_lat = corners["br"]
    bl_lon, bl_lat = corners["bl"]

    lon = (
        (1 - u) * (1 - v) * ul_lon
        + u * (1 - v) * ur_lon
        + u * v * br_lon
        + (1 - u) * v * bl_lon
    )

    lat = (
        (1 - u) * (1 - v) * ul_lat
        + u * (1 - v) * ur_lat
        + u * v * br_lat
        + (1 - u) * v * bl_lat
    )

    return [
        float(lat),
        float(lon)
    ]


def polygon_pixels_to_geo(
    polygon,
    width: int,
    height: int,
    corners: dict
):
    """
    Convert a YOLO polygon from pixel coordinates
    to geographic [latitude, longitude] coordinates.
    """

    if not polygon:
        return None

    return [
        pixel_to_geo(
            x,
            y,
            width,
            height,
            corners
        )
        for x, y in polygon
    ]


def calculate_polygon_area_km2(polygon_geo):
    """
    Calculate geodesic polygon area in km².

    polygon_geo format:
        [
            [latitude, longitude],
            ...
        ]
    """

    if not polygon_geo or len(polygon_geo) < 3:
        return None

    lats = [
        point[0]
        for point in polygon_geo
    ]

    lons = [
        point[1]
        for point in polygon_geo
    ]

    area_m2, _ = GEOD.polygon_area_perimeter(
        lons,
        lats
    )

    return float(
        abs(area_m2) / 1_000_000
    )