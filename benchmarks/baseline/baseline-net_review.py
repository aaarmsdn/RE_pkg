"""Conservative, contact-based NET recommendations without geometry edits."""

from typing import assert_never

import numpy as np
from scipy import ndimage

from pkg_re.graph import GraphResult, analyze_graph
from pkg_re.models import Candidate, Layer
from pkg_re.store import Mask, State


def near_terminal(candidate: Candidate, layer: Layer) -> bool:
    """Keep repairs away from terminal clearances and detected annotations."""
    x, y, w, h = candidate.bbox
    for marker in layer.markers:
        if marker.bbox is not None and marker.source in ("ocr", "detected"):
            mx, my, mw, mh = marker.bbox
            if x < mx + mw and x + w > mx and y < my + mh and y + h > my:
                return True
        if marker.kind in ("ball", "pad", "via"):
            dx = max(x - marker.x, 0, marker.x - (x + w - 1))
            dy = max(y - marker.y, 0, marker.y - (y + h - 1))
            if dx * dx + dy * dy <= (marker.radius + layer.parameters.max_gap + 1) ** 2:
                return True
    return False


def _trace_continuity(observed: Mask, candidate: Candidate, max_gap: int) -> bool:
    """Require two straight narrow endpoints, with dielectric along both edges."""
    x, y, w, h = candidate.bbox
    for mask, left, top, gap, width in ((observed, x, y, w, h), (observed.T, y, x, h, w)):
        reach = max(6, width * 2)
        if not (1 <= gap <= min(2, max_gap) and 1 <= width <= 6):
            continue
        if left < reach or left + gap + reach > mask.shape[1] or top < 1 or top + width >= mask.shape[0]:
            continue
        flank = mask[top : top + width, left - reach : left + gap + reach]
        if not (flank[:, :reach].all() and flank[:, reach + gap :].all()):
            continue
        edges = mask[[top - 1, top + width], left - reach : left + gap + reach]
        if not edges.any():
            return True
    return False


def _same_net_scratch(observed: Mask, candidate: Candidate, max_gap: int) -> bool:
    """Recognize only elongated, narrow cuts between observed copper flanks."""
    x, y, w, h = candidate.bbox
    for mask, left, top, gap, length in ((observed, x, y, w, h), (observed.T, y, x, h, w)):
        if not (1 <= gap <= min(2, max_gap) and 4 * gap <= length <= 64):
            continue
        if left < 3 or left + gap + 3 > mask.shape[1]:
            continue
        if (
            mask[top : top + length, left - 3 : left].all()
            and mask[top : top + length, left + gap : left + gap + 3].all()
        ):
            return True
    return False


def refresh_recommendations(state: State, lid: str, graph: GraphResult | None = None) -> None:
    """Update pending metadata using one graph plus compact local neighborhoods.

    Recommendations are deterministic heuristics, not confidence scores. Actual
    decisions must revalidate the graph after every geometry-changing operation.
    """
    layer = state.layer(lid)
    px = state.pixels[lid]
    graph = analyze_graph(state) if graph is None else graph
    labels = graph.labels[lid]
    regions = {region.id: region for region in graph.regions[lid]}
    observed = px.observed & ~px.erased & ~px.protected
    for candidate in layer.candidates:
        if candidate.status != "pending":
            continue
        candidate.recommendation = "review"
        candidate.recommendation_reason = "Named physical continuity or material evidence is unresolved."
        candidate.hint_nets = []
        x, y, w, h = candidate.bbox
        patch = px.patches[candidate.id]
        x0, y0, x1, y1 = (
            max(0, x - 1),
            max(0, y - 1),
            min(layer.width, x + w + 1),
            min(layer.height, y + h + 1),
        )
        local = np.zeros((y1 - y0, x1 - x0), dtype=bool)
        local[y - y0 : y - y0 + h, x - x0 : x - x0 + w] = patch
        contacted = np.unique(labels[y0:y1, x0:x1][ndimage.binary_dilation(local)])
        touching = [regions[int(rid)] for rid in contacted if rid]
        assigned = {r.net for r in touching if r.status == "assigned"}
        candidate.hint_nets = sorted(
            assigned | {name for r in touching if r.status == "conflict" for name in r.net.split(" | ")}
        )
        match candidate.kind:
            case "short_split":
                candidate.recommendation_reason = (
                    "Weak observed bridge: inspect source and approve erase explicitly."
                )
                continue
            case "plane_hole_fill" | "reconnect":
                pass
            case unreachable:
                assert_never(unreachable)
        if any(r.status == "conflict" for r in touching):
            candidate.recommendation_reason = "Touches a conflicting component; resolve its named NETs first."
            continue
        if len(assigned) > 1:
            candidate.recommendation = "reject"
            candidate.recommendation_reason = (
                "Would bridge physically contacted components with different confirmed NETs."
            )
            continue
        if (patch & (px.protected[y : y + h, x : x + w] | px.erased[y : y + h, x : x + w])).any():
            candidate.recommendation_reason = "Crosses an explicit protection or erase."
            continue
        if candidate.annotation_overlap is None:
            candidate.recommendation_reason = (
                "Annotation evidence predates this analysis; regenerate candidates."
            )
            continue
        if candidate.annotation_overlap or near_terminal(candidate, layer):
            candidate.recommendation_reason = (
                "Terminal clearance or annotation occlusion requires source review."
            )
            continue
        if not assigned or not patch.all() or int(patch.sum()) > 128:
            continue
        known = all(r.status == "assigned" for r in touching)
        match candidate.kind:
            case "plane_hole_fill":
                if known and _same_net_scratch(observed, candidate, layer.parameters.max_gap):
                    candidate.recommendation = "accept"
                    candidate.recommendation_reason = (
                        "Thin elongated scratch enclosed by one confirmed NET and observed flanks."
                    )
                else:
                    candidate.recommendation_reason = (
                        "Compact void may be an intentional antipad; keep for review."
                    )
            case "reconnect":
                continuity = len(touching) == 2 and _trace_continuity(
                    observed, candidate, layer.parameters.max_gap
                )
                scratch = (
                    known
                    and len(touching) == 2
                    and _same_net_scratch(observed, candidate, layer.parameters.max_gap)
                )
                if continuity or scratch:
                    candidate.recommendation = "accept"
                    candidate.recommendation_reason = (
                        "Short collinear trace endpoints support continuity."
                        if continuity
                        else "Thin scratch has observed flanks belonging to the same confirmed NET."
                    )
            case "short_split":
                pass
            case unreachable:
                assert_never(unreachable)
