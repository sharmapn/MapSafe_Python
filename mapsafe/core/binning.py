from __future__ import annotations

from collections import Counter

import geopandas as gpd
from shapely.geometry import Polygon

try:
    import h3
except ImportError as exc:  # pragma: no cover
    h3 = None
    H3_IMPORT_ERROR = exc
else:
    H3_IMPORT_ERROR = None


def _latlng_to_cell(lat: float, lng: float, resolution: int) -> str:
    """Compatibility wrapper for h3-py v3 and v4."""
    if hasattr(h3, "latlng_to_cell"):
        return h3.latlng_to_cell(lat, lng, resolution)
    return h3.geo_to_h3(lat, lng, resolution)


def _cell_to_polygon(cell: str) -> Polygon:
    """Compatibility wrapper for h3-py v3 and v4."""
    if hasattr(h3, "cell_to_boundary"):
        boundary = h3.cell_to_boundary(cell)
        coords = [(lng, lat) for lat, lng in boundary]
    else:
        boundary = h3.h3_to_geo_boundary(cell, geo_json=True)
        coords = [(lng, lat) for lng, lat in boundary]

    return Polygon(coords)


def h3_bin_points(gdf: gpd.GeoDataFrame, resolution: int) -> gpd.GeoDataFrame:
    """Create H3 hexagons with point counts."""
    if h3 is None:
        raise ImportError(
            "The h3 package is required for hexagonal binning. "
            "Install it with: pip install h3"
        ) from H3_IMPORT_ERROR

    if resolution < 0 or resolution > 15:
        raise ValueError("H3 resolution must be between 0 and 15.")

    geom_types = set(gdf.geometry.geom_type.dropna().unique())
    unsupported = geom_types.difference({"Point"})
    if unsupported:
        raise ValueError(
            "This first standalone version supports point layers for H3 binning. "
            f"Unsupported geometry type(s): {', '.join(sorted(unsupported))}"
        )

    wgs84 = gdf.to_crs("EPSG:4326")

    cells = [
        _latlng_to_cell(point.y, point.x, resolution)
        for point in wgs84.geometry
        if point is not None and not point.is_empty
    ]

    counts = Counter(cells)

    records = []
    polygons = []

    for cell, count in sorted(counts.items()):
        records.append({"h3_cell": cell, "numpoints": int(count), "resolution": int(resolution)})
        polygons.append(_cell_to_polygon(cell))

    return gpd.GeoDataFrame(records, geometry=polygons, crs="EPSG:4326")
