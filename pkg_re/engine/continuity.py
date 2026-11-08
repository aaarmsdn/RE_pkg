"""Bounded local shape evidence shared by proposal ranking and review."""

import numpy as np

from .types import Mask


def thin_scratch(bbox: tuple[int, int, int, int], pixels: int, max_gap: int) -> bool:
    _, _, width, height = bbox
    narrow, length = sorted((width, height))
    return 1 <= narrow <= min(2, max_gap) and 4 * narrow <= length <= 512 and pixels == width * height


def trace_continuity(
    observed: Mask, bbox: tuple[int, int, int, int], max_gap: int, *, directional: bool = False
) -> bool:
    """Fit narrow isolated flanks, allowing pixel stairs but not parallel sides."""
    x, y, w, h = bbox
    for mask, left, top, gap, span in ((observed, x, y, w, h), (observed.T, y, x, h, w)):
        reach, margin = 8, 16
        if not (1 <= gap <= min(4 if directional else 2, max_gap) and 1 <= span <= 8):
            continue
        if left < reach or left + gap + reach > mask.shape[1] or top < 1 or top + span >= mask.shape[0]:
            continue
        window_top = max(0, top - margin)
        window_bottom = min(mask.shape[0], top + span + margin)
        columns = list(range(left - reach, left)) + list(range(left + gap, left + gap + reach))
        centers, widths = [], []
        for column in columns:
            rows = np.flatnonzero(mask[window_top:window_bottom, column])
            if not len(rows):
                break
            runs = np.split(rows, np.flatnonzero(np.diff(rows) > 1) + 1)
            center = top - window_top + (span - 1) / 2
            rows = min(runs, key=lambda run: abs(float(run.mean()) - center))
            if not (1 <= len(rows) <= 8):
                break
            if rows[0] == 0 or rows[-1] == window_bottom - window_top - 1:
                break
            centers.append(float(rows.mean()) + window_top)
            widths.append(len(rows))
        if len(centers) != len(columns) or max(widths) - min(widths) > 2:
            continue
        slope, intercept = np.polyfit(np.array(columns) - left, centers, 1)
        residual = np.abs(np.array(centers) - (slope * (np.array(columns) - left) + intercept))
        if abs(slope) > 1.25 or residual.max() > 0.8:
            continue
        # The proposed cross section must agree with both extrapolated endpoints.
        predicted = slope * np.arange(gap) + intercept
        half_width = (float(np.median(widths)) - 1) / 2
        if top < predicted.min() - half_width - 0.8 or top + span - 1 > predicted.max() + half_width + 0.8:
            continue
        return True
    return False


def directional_scratch(patch: Mask, max_gap: int) -> tuple[float, float] | None:
    """Fit a thin straight missing-pixel band; no source/render angle input."""
    yy, xx = np.nonzero(patch)
    if len(xx) < 12:
        return None
    points = np.column_stack((xx, yy)).astype(float)
    centered = points - points.mean(axis=0)
    _, vectors = np.linalg.eigh(centered.T @ centered / len(points))
    normal, tangent = vectors[:, 0], vectors[:, 1]
    across, along = centered @ normal, centered @ tangent
    width, length = float(np.ptp(across) + 1), float(np.ptp(along) + 1)
    if width > min(4, max_gap) + 0.5 or length < 6 * width:
        return None
    if len(points) / (width * length) < 0.5:
        return None
    return float(normal[0]), float(normal[1])


def directional_flanks(observed: Mask, patch: Mask, x: int, y: int, max_gap: int) -> bool:
    """Require observed copper on both sides of a fitted band, away from its tips."""
    normal = directional_scratch(patch, max_gap)
    if normal is None:
        return False
    yy, xx = np.nonzero(patch)
    nx, ny = normal
    along = -ny * xx + nx * yy
    interior = (along > along.min() + 4) & (along < along.max() - 4)
    if interior.sum() < 8:
        return False
    xx, yy = xx[interior] + x, yy[interior] + y
    for side in (-1, 1):
        for distance in (min(4, max_gap) + 1, min(4, max_gap) + 2):
            sx = np.rint(xx + side * distance * nx).astype(int)
            sy = np.rint(yy + side * distance * ny).astype(int)
            if (
                (sx < 0).any()
                or (sy < 0).any()
                or (sx >= observed.shape[1]).any()
                or (sy >= observed.shape[0]).any()
            ):
                return False
            if not observed[sy, sx].all():
                return False
    return True
