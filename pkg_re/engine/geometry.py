"""Exact pixel-cell geometry; no contour-center area shrinkage."""

import numpy as np
from shapely import affinity, get_parts, union_all
from shapely.geometry import box

from .types import Affine, Mask, PolygonData


def mask_polygons(mask: Mask, affine: Affine | None = None) -> list[PolygonData]:
    """Union horizontal pixel runs, preserving holes and disconnected islands."""
    rectangles = []
    for y, row in enumerate(mask):
        transitions = np.diff(np.pad(row.astype(np.int8), (1, 1)))
        starts, ends = np.flatnonzero(transitions == 1), np.flatnonzero(transitions == -1)
        rectangles.extend(
            box(int(start), y, int(end), y + 1) for start, end in zip(starts, ends, strict=True)
        )
    if not rectangles:
        return []
    geometry = union_all(rectangles)
    if affine is not None:
        geometry = affinity.affine_transform(geometry, affine)
    return [
        PolygonData(
            list(polygon.exterior.coords),
            [list(ring.coords) for ring in polygon.interiors],
            float(polygon.area),
        )
        for polygon in get_parts(geometry)
    ]
