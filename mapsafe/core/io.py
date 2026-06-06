from __future__ import annotations

import math
from pathlib import Path
from typing import Tuple

import geopandas as gpd
from pyproj import CRS


DEFAULT_CRS = "EPSG:4326"


def load_vector_layer(path: str | Path) -> gpd.GeoDataFrame:
    """Load a vector layer using GeoPandas."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")

    gdf = gpd.read_file(path)

    if gdf.empty:
        raise ValueError("The selected vector layer has no features.")

    if gdf.crs is None:
        gdf = gdf.set_crs(DEFAULT_CRS)

    return gdf


def save_vector_layer(gdf: gpd.GeoDataFrame, path: str | Path) -> Path:
    """Save a GeoDataFrame to GeoJSON, Shapefile, or GeoPackage."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)

    suffix = path.suffix.lower()

    if suffix in [".geojson", ".json"]:
        gdf.to_file(path, driver="GeoJSON")
    elif suffix == ".shp":
        gdf.to_file(path, driver="ESRI Shapefile")
    elif suffix == ".gpkg":
        gdf.to_file(path, driver="GPKG")
    else:
        path = path.with_suffix(".geojson")
        gdf.to_file(path, driver="GeoJSON")

    return path


def get_metric_working_copy(gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, CRS]:
    """Return a projected copy suitable for metre-based distance operations."""
    original_crs = CRS.from_user_input(gdf.crs or DEFAULT_CRS)

    if not original_crs.is_geographic:
        return gdf.copy(), original_crs

    wgs84 = gdf.to_crs(DEFAULT_CRS)
    minx, miny, maxx, maxy = wgs84.total_bounds
    lon = (minx + maxx) / 2.0
    lat = (miny + maxy) / 2.0

    zone = int(math.floor((lon + 180.0) / 6.0) + 1)
    epsg = 32600 + zone if lat >= 0 else 32700 + zone
    projected = wgs84.to_crs(epsg)

    return projected, original_crs


def default_output_path(input_path: str | Path, suffix: str) -> Path:
    """Create a default output path beside the input file."""
    input_path = Path(input_path)
    return input_path.with_name(f"{input_path.stem}{suffix}.geojson")
