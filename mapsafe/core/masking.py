from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import geopandas as gpd
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import Point

from mapsafe.core.io import get_metric_working_copy


@dataclass
class MaskingReport:
    """Summary values returned after geomasking."""
    feature_count: int
    min_distance: float
    max_distance: float
    privacy_rating: Optional[float]
    elapsed_seconds: float


def _validate_point_layer(gdf: gpd.GeoDataFrame) -> None:
    geom_types = set(gdf.geometry.geom_type.dropna().unique())
    unsupported = geom_types.difference({"Point"})
    if unsupported:
        raise ValueError(
            "This first standalone version supports point layers for geomasking. "
            f"Unsupported geometry type(s): {', '.join(sorted(unsupported))}"
        )


def spruill_like_privacy_rating(
    original_projected: gpd.GeoDataFrame,
    masked_projected: gpd.GeoDataFrame,
) -> float:
    """Compute a Spruill-style privacy score."""
    original_xy = np.column_stack(
        [original_projected.geometry.x.to_numpy(), original_projected.geometry.y.to_numpy()]
    )
    masked_xy = np.column_stack(
        [masked_projected.geometry.x.to_numpy(), masked_projected.geometry.y.to_numpy()]
    )

    tree = cKDTree(original_xy)
    _, nearest_indices = tree.query(masked_xy, k=1)

    expected_indices = np.arange(len(original_projected))
    reidentified = np.count_nonzero(nearest_indices == expected_indices)
    privacy_rating = 100.0 - ((reidentified / len(original_projected)) * 100.0)

    return round(float(privacy_rating), 2)


def mask_points(
    gdf: gpd.GeoDataFrame,
    min_distance: float,
    max_distance: float,
    calculate_privacy_rating: bool = True,
    seed: Optional[int] = None,
) -> tuple[gpd.GeoDataFrame, MaskingReport]:
    """Randomly displace every point by a distance between min and max metres."""
    if min_distance < 0:
        raise ValueError("Minimum distance must be zero or greater.")

    if max_distance <= 0:
        raise ValueError("Maximum distance must be greater than zero.")

    if max_distance < min_distance:
        raise ValueError("Maximum distance must be greater than or equal to minimum distance.")

    _validate_point_layer(gdf)

    start_time = time.time()
    rng = np.random.default_rng(seed)

    original_crs = gdf.crs
    projected, _ = get_metric_working_copy(gdf.reset_index(drop=True))

    angles = rng.uniform(0.0, 2.0 * np.pi, size=len(projected))
    distances = rng.uniform(min_distance, max_distance, size=len(projected))

    dx = distances * np.cos(angles)
    dy = distances * np.sin(angles)

    masked_projected = projected.copy()
    x = projected.geometry.x.to_numpy() + dx
    y = projected.geometry.y.to_numpy() + dy
    masked_projected.geometry = [Point(px, py) for px, py in zip(x, y)]

    privacy_rating = None
    if calculate_privacy_rating:
        privacy_rating = spruill_like_privacy_rating(projected, masked_projected)

    masked = masked_projected.to_crs(original_crs)
    elapsed_seconds = time.time() - start_time

    report = MaskingReport(
        feature_count=len(masked),
        min_distance=min_distance,
        max_distance=max_distance,
        privacy_rating=privacy_rating,
        elapsed_seconds=round(elapsed_seconds, 2),
    )

    return masked, report
