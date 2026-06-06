"""H3 hexagonal binning functions for MapSafe Python.

This module converts point layers into H3 hexagonal aggregation layers.  H3
binning is useful for geoprivacy because it replaces exact point locations with
counts per hexagon, reducing the risk of exposing individual locations.
"""

# Enable postponed evaluation of annotations for consistency across the package.
from __future__ import annotations

# Counter is used to count how many points fall into each H3 cell.
from collections import Counter

# GeoPandas stores the input point layer and the output hexagon layer.
import geopandas as gpd

# Shapely Polygon is used to construct hexagonal cell geometries from H3 cell
# boundary coordinates.
from shapely.geometry import Polygon

# H3 is an optional dependency at runtime.  The app can still start without H3,
# but the H3 binning function should produce a clear error if the package is not
# installed.
try:
    # Import the H3 Python package.  Different versions expose slightly different
    # function names, so wrapper functions below handle compatibility.
    import h3
except ImportError as exc:  # pragma: no cover
    # If H3 is unavailable, store None so h3_bin_points can raise a helpful
    # message later when the user actually tries to run H3 binning.
    h3 = None

    # Store the original import error so it can be chained when raising the
    # user-facing ImportError.
    H3_IMPORT_ERROR = exc
else:
    # If import succeeds, there is no saved import error.
    H3_IMPORT_ERROR = None


def _latlng_to_cell(lat: float, lng: float, resolution: int) -> str:
    """Return the H3 cell ID for a latitude/longitude coordinate.

    This helper supports both newer and older versions of the h3-py package.

    Args:
        lat: Latitude in decimal degrees.
        lng: Longitude in decimal degrees.
        resolution: H3 resolution from 0 to 15.

    Returns:
        str: H3 cell identifier.
    """

    # h3-py v4 uses ``latlng_to_cell``.
    if hasattr(h3, "latlng_to_cell"):
        return h3.latlng_to_cell(lat, lng, resolution)

    # h3-py v3 used ``geo_to_h3``.
    return h3.geo_to_h3(lat, lng, resolution)


def _cell_to_polygon(cell: str) -> Polygon:
    """Convert an H3 cell ID into a Shapely Polygon.

    Args:
        cell: H3 cell identifier.

    Returns:
        Polygon: Polygon geometry representing the H3 cell boundary.
    """

    # h3-py v4 uses ``cell_to_boundary`` and returns coordinates as
    # latitude/longitude pairs.
    if hasattr(h3, "cell_to_boundary"):
        boundary = h3.cell_to_boundary(cell)

        # GeoJSON and Shapely expect coordinates in longitude/latitude order, so
        # swap the order from (lat, lng) to (lng, lat).
        coords = [(lng, lat) for lat, lng in boundary]

    # h3-py v3 used ``h3_to_geo_boundary``.  With geo_json=True it returns
    # coordinates in longitude/latitude order.
    else:
        boundary = h3.h3_to_geo_boundary(cell, geo_json=True)
        coords = [(lng, lat) for lng, lat in boundary]

    # Build a Shapely polygon from the boundary coordinates.
    return Polygon(coords)


def h3_bin_points(gdf: gpd.GeoDataFrame, resolution: int) -> gpd.GeoDataFrame:
    """Create H3 hexagons with point counts.

    Args:
        gdf: Input point GeoDataFrame.
        resolution: H3 resolution from 0 to 15.  Higher resolution means smaller
            hexagons.

    Returns:
        GeoDataFrame: Hexagon polygons with count attributes.
    """

    # Fail with a clear error if H3 is not installed.  This is better than a
    # confusing AttributeError later in the function.
    if h3 is None:
        raise ImportError(
            "The h3 package is required for hexagonal binning. "
            "Install it with: pip install h3"
        ) from H3_IMPORT_ERROR

    # H3 officially supports resolutions from 0 to 15.
    if resolution < 0 or resolution > 15:
        raise ValueError("H3 resolution must be between 0 and 15.")

    # Collect geometry types found in the input layer.
    geom_types = set(gdf.geometry.geom_type.dropna().unique())

    # This first version only supports point-to-hex aggregation.  Line and
    # polygon aggregation require different spatial logic.
    unsupported = geom_types.difference({"Point"})

    # Stop early if unsupported geometry types are found.
    if unsupported:
        raise ValueError(
            "This first standalone version supports point layers for H3 binning. "
            f"Unsupported geometry type(s): {', '.join(sorted(unsupported))}"
        )

    # H3 expects latitude/longitude coordinates on WGS84, so reproject the input
    # layer to EPSG:4326 before calculating cell IDs.
    wgs84 = gdf.to_crs("EPSG:4326")

    # Convert each point to an H3 cell.  For Shapely Point, x is longitude and y
    # is latitude.  Empty/null geometries are skipped.
    cells = [
        _latlng_to_cell(point.y, point.x, resolution)
        for point in wgs84.geometry
        if point is not None and not point.is_empty
    ]

    # Count how many points fall into each H3 cell.
    counts = Counter(cells)

    # Attribute records for the output GeoDataFrame.
    records = []

    # Polygon geometries for the output GeoDataFrame.
    polygons = []

    # Build one output polygon feature per occupied H3 cell.
    for cell, count in sorted(counts.items()):
        # Store useful attributes for later display, export, or analysis.
        records.append({"h3_cell": cell, "numpoints": int(count), "resolution": int(resolution)})

        # Convert the H3 cell boundary into a polygon geometry.
        polygons.append(_cell_to_polygon(cell))

    # Return the aggregated H3 layer.  H3 boundaries are in WGS84, so the output
    # CRS is EPSG:4326.
    return gpd.GeoDataFrame(records, geometry=polygons, crs="EPSG:4326")
