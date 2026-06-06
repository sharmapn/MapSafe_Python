"""Input/output helper functions for MapSafe Python vector layers.

This module keeps file-loading, file-saving, and coordinate reference system
logic separate from the user interface.  That separation is useful because the
same geospatial functions can later be reused by a command-line tool, tests, or
another GUI without rewriting the logic.
"""

# Enable postponed evaluation of type hints.  This keeps annotations lightweight
# at runtime and improves compatibility with forward references.
from __future__ import annotations

# ``math`` is used for calculating a UTM zone from longitude.
import math

# ``Path`` provides safer path handling than raw strings, especially across
# Windows, macOS, and Linux.
from pathlib import Path

# ``Tuple`` is used in the return annotation for get_metric_working_copy.
from typing import Tuple

# GeoPandas is the main library used by this application for reading, writing,
# storing, and transforming vector geospatial data.
import geopandas as gpd

# CRS from pyproj is used to inspect whether a layer is geographic or projected.
from pyproj import CRS


# Default coordinate reference system used when a loaded dataset has no CRS.
# EPSG:4326 is WGS84 longitude/latitude, which is the standard CRS for GeoJSON.
DEFAULT_CRS = "EPSG:4326"


def load_vector_layer(path: str | Path) -> gpd.GeoDataFrame:
    """Load a vector layer using GeoPandas.

    Args:
        path: File path to a supported vector dataset, such as GeoJSON,
            Shapefile, or GeoPackage.

    Returns:
        GeoDataFrame: The loaded spatial layer.

    Raises:
        FileNotFoundError: If the path does not exist.
        ValueError: If the file loads but contains no features.

    Notes:
        If the dataset has no CRS, this function assumes EPSG:4326.  This is a
        practical default for GeoJSON-style data, but users should still confirm
        the CRS for real datasets before applying distance-based masking.
    """

    # Convert the incoming string/path-like object into a Path object so we can
    # use consistent path operations below.
    path = Path(path)

    # Fail early with a clear error if the selected file does not exist.
    if not path.exists():
        raise FileNotFoundError(f"File does not exist: {path}")

    # GeoPandas delegates the actual reading to Fiona/GDAL where available.
    # This means several vector formats can be supported through one function.
    gdf = gpd.read_file(path)

    # A spatial file with zero features is not useful for masking or binning, so
    # report this as a user-facing validation error.
    if gdf.empty:
        raise ValueError("The selected vector layer has no features.")

    # Some demo or older files may not declare a CRS.  Setting a default prevents
    # later projection operations from crashing, but the README should remind
    # users that real datasets require verified CRS metadata.
    if gdf.crs is None:
        gdf = gdf.set_crs(DEFAULT_CRS)

    # Return the loaded GeoDataFrame to the caller.  The GUI stores this in
    # MainWindow.current_gdf and sends it to the map panel.
    return gdf


def save_vector_layer(gdf: gpd.GeoDataFrame, path: str | Path) -> Path:
    """Save a GeoDataFrame to GeoJSON, Shapefile, or GeoPackage.

    Args:
        gdf: The spatial layer to save.
        path: Requested output path.  The file extension determines the driver.

    Returns:
        Path: The final path written to disk.  If the extension is unsupported,
        the function changes the output extension to ``.geojson``.
    """

    # Normalise the path argument so path operations are consistent.
    path = Path(path)

    # Ensure that the destination folder exists before writing the file.  The
    # ``parents=True`` option also creates missing parent folders.
    path.parent.mkdir(parents=True, exist_ok=True)

    # Use the file extension to choose a driver.  Lowercasing avoids issues with
    # extensions such as ``.GEOJSON`` or ``.SHP``.
    suffix = path.suffix.lower()

    # GeoJSON is the preferred lightweight exchange format for the standalone
    # tool and is also the safest default for the browser map preview.
    if suffix in [".geojson", ".json"]:
        gdf.to_file(path, driver="GeoJSON")

    # Shapefile is still widely used in GIS workflows, so it is supported when
    # the user's environment has the necessary GDAL/Fiona support.
    elif suffix == ".shp":
        gdf.to_file(path, driver="ESRI Shapefile")

    # GeoPackage is a modern single-file GIS format and is useful for larger or
    # more structured outputs.
    elif suffix == ".gpkg":
        gdf.to_file(path, driver="GPKG")

    # If the user provides an unknown extension, keep the app simple and write a
    # GeoJSON file instead of failing unexpectedly.
    else:
        path = path.with_suffix(".geojson")
        gdf.to_file(path, driver="GeoJSON")

    # Return the actual output path so the UI can display or reuse it.
    return path


def get_metric_working_copy(gdf: gpd.GeoDataFrame) -> Tuple[gpd.GeoDataFrame, CRS]:
    """Return a projected copy suitable for metre-based distance operations.

    Geomasking distances are entered by the user in metres.  Longitude/latitude
    coordinates are angular units, not metres, so distance-based operations need
    a projected CRS.  This function creates a projected working copy when the
    source data is geographic.

    Args:
        gdf: Input GeoDataFrame.

    Returns:
        tuple[GeoDataFrame, CRS]: A projected copy of the data and the original
        CRS.  The original CRS can later be used to reproject the output back to
        the user's original coordinate system.
    """

    # Convert the GeoDataFrame CRS into a pyproj CRS object.  If the layer has no
    # CRS for any reason, fall back to EPSG:4326 so the app can continue.
    original_crs = CRS.from_user_input(gdf.crs or DEFAULT_CRS)

    # If the CRS is already projected, coordinates are assumed to be in linear
    # units suitable for metre-style operations.  Return a copy to avoid mutating
    # the caller's original GeoDataFrame.
    if not original_crs.is_geographic:
        return gdf.copy(), original_crs

    # If the data is geographic, first normalise it to WGS84.  This makes the UTM
    # zone calculation predictable and avoids mixing different geographic CRSs.
    wgs84 = gdf.to_crs(DEFAULT_CRS)

    # total_bounds returns [minx, miny, maxx, maxy].  For WGS84, x is longitude
    # and y is latitude.
    minx, miny, maxx, maxy = wgs84.total_bounds

    # Use the dataset centre to choose a local UTM zone.  This is a practical
    # approximation for small-to-medium local datasets.
    lon = (minx + maxx) / 2.0
    lat = (miny + maxy) / 2.0

    # Calculate the UTM zone number from longitude.  UTM zones are 6 degrees wide
    # and numbered from west to east starting at longitude -180.
    zone = int(math.floor((lon + 180.0) / 6.0) + 1)

    # EPSG 326xx is WGS84 / UTM northern hemisphere; EPSG 327xx is WGS84 / UTM
    # southern hemisphere.  Fiji is in the southern hemisphere, so Fiji datasets
    # normally resolve to an EPSG 327xx code.
    epsg = 32600 + zone if lat >= 0 else 32700 + zone

    # Reproject the working copy to the selected UTM CRS.
    projected = wgs84.to_crs(epsg)

    # Return both the projected data and the original CRS.
    return projected, original_crs


def default_output_path(input_path: str | Path, suffix: str) -> Path:
    """Create a default GeoJSON output path beside the input file.

    Args:
        input_path: Original input file path.
        suffix: Suffix to append to the input stem, such as ``_masked``.

    Returns:
        Path: A GeoJSON path beside the original input file.
    """

    # Convert to Path so we can safely access stem, parent, and filename parts.
    input_path = Path(input_path)

    # Keep outputs beside the input file and preserve the input filename stem so
    # users can easily see which output came from which source file.
    return input_path.with_name(f"{input_path.stem}{suffix}.geojson")
