"""Geomasking functions for MapSafe Python.

This module contains the core location-displacement logic used by the standalone
application.  The current version focuses on point layers because point data is
usually the most privacy-sensitive geospatial data type and is the main target
for donut-style geomasking.
"""

# Enable modern type annotations while keeping runtime imports lightweight.
from __future__ import annotations

# ``time`` is used to measure how long a masking run takes.
import time

# dataclass reduces boilerplate for simple result/summary objects.
from dataclasses import dataclass

# Optional is used for values that may be absent, such as privacy_rating when the
# user chooses not to calculate it.
from typing import Optional

# GeoPandas stores the vector layer and handles CRS transformations.
import geopandas as gpd

# NumPy is used for fast vectorised random angles, random distances, and x/y
# displacement calculations.
import numpy as np

# cKDTree provides fast nearest-neighbour lookup for the privacy-rating check.
from scipy.spatial import cKDTree

# Shapely Point is used to rebuild geometries after coordinate displacement.
from shapely.geometry import Point

# Helper that converts geographic data into a projected metre-based working CRS.
from mapsafe.core.io import get_metric_working_copy


@dataclass
class MaskingReport:
    """Summary values returned after geomasking.

    This object is returned together with the masked GeoDataFrame so the user
    interface can show useful feedback without recomputing anything.
    """

    # Number of features successfully processed.
    feature_count: int

    # Minimum distance entered by the user, in metres.
    min_distance: float

    # Maximum distance entered by the user, in metres.
    max_distance: float

    # Spruill-style privacy rating.  This is optional because privacy-rating
    # calculation can be disabled for faster processing.
    privacy_rating: Optional[float]

    # Total processing time, rounded to seconds in the calling function.
    elapsed_seconds: float


def _validate_point_layer(gdf: gpd.GeoDataFrame) -> None:
    """Ensure that the input layer contains only point geometries.

    Args:
        gdf: Input GeoDataFrame to validate.

    Raises:
        ValueError: If the layer contains geometry types other than Point.
    """

    # Collect all geometry types present in the layer, ignoring null geometries.
    geom_types = set(gdf.geometry.geom_type.dropna().unique())

    # In this first standalone version, geomasking is intentionally limited to
    # Point layers.  Polygon/line masking needs different utility and topology
    # considerations and should be added separately later.
    unsupported = geom_types.difference({"Point"})

    # If any unsupported geometry type is found, raise a clear user-facing error.
    if unsupported:
        raise ValueError(
            "This first standalone version supports point layers for geomasking. "
            f"Unsupported geometry type(s): {', '.join(sorted(unsupported))}"
        )


def spruill_like_privacy_rating(
    original_projected: gpd.GeoDataFrame,
    masked_projected: gpd.GeoDataFrame,
) -> float:
    """Compute a simplified Spruill-style privacy score.

    The idea is to estimate how many masked points can still be linked back to
    their original locations using a nearest-neighbour attack.  If a masked point
    is still closest to its own original location, it is counted as reidentified.

    Args:
        original_projected: Original point layer in a projected CRS.
        masked_projected: Masked point layer in the same projected CRS.

    Returns:
        float: Privacy score between 0 and 100.  Higher means better privacy.
    """

    # Build an Nx2 NumPy array of original x/y coordinates.  The projected CRS
    # ensures x and y are linear map units rather than longitude/latitude angles.
    original_xy = np.column_stack(
        [original_projected.geometry.x.to_numpy(), original_projected.geometry.y.to_numpy()]
    )

    # Build an Nx2 NumPy array of masked x/y coordinates in the same projected
    # CRS as the original points.
    masked_xy = np.column_stack(
        [masked_projected.geometry.x.to_numpy(), masked_projected.geometry.y.to_numpy()]
    )

    # Create a KD-tree from the original points.  KD-trees make nearest-neighbour
    # lookup much faster than checking every original point against every masked
    # point manually.
    tree = cKDTree(original_xy)

    # For each masked point, find the index of the nearest original point.
    # ``k=1`` means only the closest original point is requested.
    _, nearest_indices = tree.query(masked_xy, k=1)

    # If feature order is preserved, the original point for feature i is also at
    # index i.  This array represents the expected original index for each masked
    # point if the point were perfectly reidentified.
    expected_indices = np.arange(len(original_projected))

    # Count how many masked points still have their own original point as the
    # nearest neighbour.
    reidentified = np.count_nonzero(nearest_indices == expected_indices)

    # Convert reidentification rate to a privacy score.  If all points are still
    # nearest to themselves, privacy is 0.  If none are, privacy is 100.
    privacy_rating = 100.0 - ((reidentified / len(original_projected)) * 100.0)

    # Round to two decimals for cleaner display in the UI.
    return round(float(privacy_rating), 2)


def mask_points(
    gdf: gpd.GeoDataFrame,
    min_distance: float,
    max_distance: float,
    calculate_privacy_rating: bool = True,
    seed: Optional[int] = None,
) -> tuple[gpd.GeoDataFrame, MaskingReport]:
    """Randomly displace every point by a distance between min and max metres.

    Args:
        gdf: Input point GeoDataFrame.
        min_distance: Minimum masking distance in metres.
        max_distance: Maximum masking distance in metres.
        calculate_privacy_rating: Whether to calculate the Spruill-style score.
        seed: Optional random seed for reproducible demonstrations/tests.

    Returns:
        tuple[GeoDataFrame, MaskingReport]: The masked layer and a summary report.
    """

    # A negative distance would move points in a mathematically undefined way for
    # this workflow, so block it immediately.
    if min_distance < 0:
        raise ValueError("Minimum distance must be zero or greater.")

    # The maximum distance must be positive because a zero maximum would produce
    # no meaningful masking.
    if max_distance <= 0:
        raise ValueError("Maximum distance must be greater than zero.")

    # The distance interval must be valid.  For example, 500 m minimum and 100 m
    # maximum would not make sense.
    if max_distance < min_distance:
        raise ValueError("Maximum distance must be greater than or equal to minimum distance.")

    # Confirm that the input layer contains point geometries only.
    _validate_point_layer(gdf)

    # Record the start time so the UI can report processing duration.
    start_time = time.time()

    # Create a NumPy random number generator.  Passing a seed gives reproducible
    # output, which is useful for demos and testing.
    rng = np.random.default_rng(seed)

    # Store the original CRS before creating a projected working copy.  The final
    # masked output is returned to this CRS.
    original_crs = gdf.crs

    # Reset the index so original and masked feature order are cleanly aligned.
    # The projected copy lets us apply metre-based displacement safely.
    projected, _ = get_metric_working_copy(gdf.reset_index(drop=True))

    # Generate one random angle per point, measured in radians from 0 to 2π.
    angles = rng.uniform(0.0, 2.0 * np.pi, size=len(projected))

    # Generate one random displacement distance per point within the user-defined
    # distance range.
    distances = rng.uniform(min_distance, max_distance, size=len(projected))

    # Convert polar displacement (distance + angle) into x/y offsets.
    dx = distances * np.cos(angles)
    dy = distances * np.sin(angles)

    # Copy the projected GeoDataFrame so attributes are preserved while geometry
    # is replaced with masked point locations.
    masked_projected = projected.copy()

    # Add x offsets to original x coordinates.
    x = projected.geometry.x.to_numpy() + dx

    # Add y offsets to original y coordinates.
    y = projected.geometry.y.to_numpy() + dy

    # Rebuild the geometry column from the displaced coordinates.
    masked_projected.geometry = [Point(px, py) for px, py in zip(x, y)]

    # Default to no privacy rating when the option is disabled.
    privacy_rating = None

    # Calculate the privacy rating only when requested.  This can be skipped for
    # large datasets if the user wants faster processing.
    if calculate_privacy_rating:
        privacy_rating = spruill_like_privacy_rating(projected, masked_projected)

    # Reproject the masked output back to the original CRS so the saved output is
    # compatible with the user's source data.
    masked = masked_projected.to_crs(original_crs)

    # Calculate total runtime in seconds.
    elapsed_seconds = time.time() - start_time

    # Build a report object that the UI can display in labels and logs.
    report = MaskingReport(
        feature_count=len(masked),
        min_distance=min_distance,
        max_distance=max_distance,
        privacy_rating=privacy_rating,
        elapsed_seconds=round(elapsed_seconds, 2),
    )

    # Return both the masked spatial data and the summary report.
    return masked, report
