"""Bounded, explicitly ambiguous repair proposals. Never edit evidence."""

import numpy as np
from numpy.typing import NDArray
from scipy import ndimage

from .masks import connected_regions
from .types import Mask, RepairProposal, SegmentationOptions


def _axis_gaps(labels: NDArray[np.int32], max_gap: int) -> Mask:
    """Find bounded scan-line runs contacting distinct copper components."""
    gaps = np.zeros(labels.shape, dtype=bool)
    for distance in range(2, min(max_gap + 2, labels.shape[1])):
        left, right = labels[:, :-distance], labels[:, distance:]
        valid = (left > 0) & (right > 0) & (left != right)
        for offset in range(1, distance):
            valid &= labels[:, offset : labels.shape[1] - distance + offset] == 0
        for offset in range(1, distance):
            gaps[:, offset : labels.shape[1] - distance + offset] |= valid
    return gaps


def propose_repairs(observed: Mask, protected: Mask, options: SegmentationOptions) -> list[RepairProposal]:
    """Propose enclosed holes and narrow straight gaps, capped at 100 patches.

    Geometry alone cannot distinguish scratch from intended clearance. All
    proposals require review, including gaps between adjacent parallel traces.
    A protected pixel vetoes its entire enclosed hole or connected gap patch.
    Reserve 50 slots per kind, then fill spare slots by descending pixel area.
    Review priority reflects geometric impact, never confidence.
    """
    labels, _ = connected_regions(observed)
    holes = ndimage.binary_fill_holes(observed) & ~observed
    hole_labels, hole_regions = connected_regions(holes)
    hole_proposals: list[RepairProposal] = []
    for region in sorted(hole_regions, key=lambda item: (-item.pixels, item.bbox)):
        if region.pixels > options.max_hole_area:
            continue
        x, y, width, height = region.bbox
        patch = hole_labels[y : y + height, x : x + width] == region.id
        if (patch & protected[y : y + height, x : x + width]).any():
            continue
        hole_proposals.append(
            RepairProposal(
                "plane_hole_fill",
                region.bbox,
                region.pixels,
                "Enclosed void: damage versus intentional antipad is unresolved.",
                patch,
                observed.shape,
            )
        )
        if len(hole_proposals) == 100:
            break
    gaps = (_axis_gaps(labels, options.max_gap) | _axis_gaps(labels.T, options.max_gap).T) & ~holes
    gap_labels, gap_regions = connected_regions(gaps)
    gap_proposals: list[RepairProposal] = []
    for region in sorted(gap_regions, key=lambda item: (-item.pixels, item.bbox)):
        x, y, width, height = region.bbox
        patch = gap_labels[y : y + height, x : x + width] == region.id
        if (patch & protected[y : y + height, x : x + width]).any():
            continue
        gap_proposals.append(
            RepairProposal(
                "reconnect",
                region.bbox,
                region.pixels,
                "Narrow gap contacts separate islands; continuity and nets require review.",
                patch,
                observed.shape,
            )
        )
        if len(gap_proposals) == 100:
            break
    selected = hole_proposals[:50] + gap_proposals[:50]
    remaining = sorted(
        hole_proposals[50:] + gap_proposals[50:], key=lambda item: (-item.pixels, item.bbox, item.kind)
    )
    selected.extend(remaining[: 100 - len(selected)])
    return sorted(selected, key=lambda item: (-item.pixels, item.bbox, item.kind))
