"""Conservative copper evidence and native-pixel brush geometry."""

import math
from typing import assert_never

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage

from .types import Mask, RegionInfo, SegmentationOptions


def segment_copper(image: NDArray[np.uint8], options: SegmentationOptions) -> Mask:
    """Threshold brightness plus warm chroma, with no topology-changing filter.

    This score is a tunable optical heuristic, not a material classifier or
    probability. Bright neutral metal is allowed; green annotation is unknown.
    """
    rgb = image.astype(np.float32)
    red, green, blue = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    warm = np.maximum(np.minimum(red, green) - blue, 0)
    score = np.clip(np.maximum(red, green) + 0.6 * warm, 0, 255)
    annotation = (green > 1.12 * red) & (green > 1.15 * blue) & (green > 70)
    match options.material_mode:
        case "legacy":
            selected = score >= options.threshold
        case "red_chroma":
            # Signed color difference rejects bright yellow dielectric, without smoothing.
            selected = red - 2 * green + blue >= options.chroma_threshold
        case unreachable:
            assert_never(unreachable)
    return selected & ~annotation


def connected_regions(mask: Mask) -> tuple[NDArray[np.int32], list[RegionInfo]]:
    """Label edge contact only; diagonal pixels do not establish connectivity."""
    labels, count = ndimage.label(mask)
    sizes = np.bincount(labels.ravel(), minlength=count + 1)
    regions = []
    for region_id, bounds in enumerate(ndimage.find_objects(labels), 1):
        ys, xs = bounds
        regions.append(
            RegionInfo(
                region_id, int(sizes[region_id]), (xs.start, ys.start, xs.stop - xs.start, ys.stop - ys.start)
            )
        )
    return labels, regions


def stroke_mask(shape: tuple[int, int], points: list[tuple[float, float]], radius: float) -> Mask:
    """Rasterize round capsules using pixel centers at integer image coordinates."""
    result = np.zeros(shape, dtype=bool)
    if not points:
        return result
    segments = list(zip(points, points[1:], strict=False)) or [(points[0], points[0])]
    for (ax, ay), (bx, by) in segments:
        x0 = max(0, math.floor(min(ax, bx) - radius))
        y0 = max(0, math.floor(min(ay, by) - radius))
        x1 = min(shape[1], math.ceil(max(ax, bx) + radius) + 1)
        y1 = min(shape[0], math.ceil(max(ay, by) + radius) + 1)
        if x0 >= x1 or y0 >= y1:
            continue
        yy, xx = np.mgrid[y0:y1, x0:x1]
        dx, dy = bx - ax, by - ay
        length_squared = dx * dx + dy * dy
        t = (
            np.clip(((xx - ax) * dx + (yy - ay) * dy) / length_squared, 0, 1)
            if length_squared
            else np.zeros_like(xx, dtype=float)
        )
        distance_squared = (xx - ax - t * dx) ** 2 + (yy - ay - t * dy) ** 2
        result[y0:y1, x0:x1] |= distance_squared <= radius * radius
    return result
