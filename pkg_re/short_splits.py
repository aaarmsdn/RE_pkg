"""Bounded weak-short erase proposals; observed evidence is never modified."""

import uuid
from dataclasses import replace

import numpy as np
from PIL import Image

from pkg_re.annotations import annotation_unknown_mask
from pkg_re.engine import SegmentationOptions, connected_regions, segment_copper
from pkg_re.graph import GraphResult, affine_for, analyze_graph, contact
from pkg_re.models import Candidate
from pkg_re.net_review import near_terminal
from pkg_re.store import State, Store


def _conflict_pixels(graph: GraphResult) -> int:
    return sum(row.total_px for row in graph.areas if row.status == "conflict")


def contacts_survive(state: State, before: GraphResult, after: GraphResult) -> bool:
    """Preserve direct marker contacts and every physical contact along each via span."""
    if not all(
        contact(after.labels[layer.id], marker) > 0
        for layer in state.project.layers
        for marker in layer.markers
        if marker.confirmed and contact(before.labels[layer.id], marker) > 0
    ):
        return False
    layers = state.project.layers
    positions = {layer.id: index for index, layer in enumerate(layers)}
    for layer in layers:
        transform = affine_for(layer.calibration)
        if transform is None:
            continue
        a, b, d, e, tx, ty = transform
        source_matrix = np.array([[a, b], [d, e]])
        for marker in layer.markers:
            if not marker.confirmed or marker.kind != "via" or marker.end_layer_id not in positions:
                continue
            start, end = positions[layer.id], positions[marker.end_layer_id]
            world = source_matrix @ np.array([marker.x, marker.y]) + [tx, ty]
            for target in layers[min(start, end) : max(start, end) + 1]:
                target_transform = affine_for(target.calibration)
                if target_transform is None:
                    continue
                ta, tb, td, te, ttx, tty = target_transform
                target_matrix = np.array([[ta, tb], [td, te]])
                xy = np.linalg.solve(target_matrix, world - [ttx, tty])
                projected = marker.model_copy(update={"x": float(xy[0]), "y": float(xy[1])})
                metric = np.linalg.solve(source_matrix, target_matrix)
                if contact(before.labels[target.id], projected, metric) and not contact(
                    after.labels[target.id], projected, metric
                ):
                    return False
    return True


def add_short_split_candidates(state: State, store: Store, lid: str) -> None:
    """Offer at most eight small low-score cuts after physical graph validation.

    Work stays inside the analyzed native ROI (at most four million pixels).
    Eight bounded trials are generation work; ordinary preview recommendations
    never repeat graph analysis per candidate. Ambiguous/strong bridges remain.
    """
    layer = state.layer(lid)
    x, y, w, h = layer.roi or (0, 0, layer.width, layer.height)
    if not layer.analyzed or w * h > 4_000_000:
        return
    before = analyze_graph(state)
    conflicts = [r.id for r in before.regions[lid] if r.status == "conflict"]
    if not conflicts:
        return
    px = state.pixels[lid]
    with Image.open(store.folder(state.project.id) / f"{lid}.png") as image:
        rgb = np.array(image.convert("RGB").crop((x, y, x + w, y + h)))
    threshold = layer.parameters.threshold
    weak = segment_copper(rgb, SegmentationOptions(threshold)) & ~segment_copper(
        rgb, SegmentationOptions(min(255, threshold + 20))
    )
    weak &= px.observed[y : y + h, x : x + w]
    weak &= np.isin(before.labels[lid][y : y + h, x : x + w], conflicts)
    unknown = annotation_unknown_mask(rgb, layer.markers, (x, y))
    blocked_roi = (px.protected | px.erased | px.inferred())[y : y + h, x : x + w] | unknown
    labels, components = connected_regions(weak)
    trials = 0
    proposals: list[Candidate] = []
    for component in sorted(components, key=lambda r: (r.pixels, r.bbox))[:256]:
        cx, cy, cw, ch = component.bbox
        if component.pixels > 64 or min(cw, ch) > 3 or max(cw, ch) > 24:
            continue
        patch = labels[cy : cy + ch, cx : cx + cw] == component.id
        gx, gy = x + cx, y + cy
        candidate = Candidate(
            id=uuid.uuid4().hex,
            kind="short_split",
            bbox=(gx, gy, cw, ch),
            pixels=component.pixels,
            reason=(
                "Thin near-threshold observed bridge connects conflicting NETs; manual erase review required."
            ),
        )
        if near_terminal(candidate, layer):
            continue
        blocked = blocked_roi[cy : cy + ch, cx : cx + cw]
        if blocked.any():
            continue
        if any(
            c.kind == "short_split" and c.bbox == candidate.bbox and np.array_equal(px.patches[c.id], patch)
            for c in layer.candidates
        ):
            continue
        if trials >= 8:
            break
        trials += 1
        erased = px.erased.copy()
        erased[gy : gy + ch, gx : gx + cw] |= patch
        trial = State(state.project, {**state.pixels, lid: replace(px, erased=erased)})
        after = analyze_graph(trial)
        if _conflict_pixels(before) - _conflict_pixels(after) <= component.pixels:
            continue
        if not contacts_survive(state, before, after):
            continue
        candidate.recommendation = "review"
        candidate.recommendation_reason = (
            "Removing this weak bridge reduces conflicting copper while preserving confirmed contacts."
        )
        proposals.append(candidate)
        px.patches[candidate.id] = patch.copy()
    if not proposals:
        return
    combined = [*proposals, *layer.candidates]
    excess = max(0, len(combined) - 100)
    discarded = set()
    for candidate in reversed(layer.candidates):
        if excess and candidate.status == "pending" and candidate.kind != "short_split":
            discarded.add(candidate.id)
            del px.patches[candidate.id]
            excess -= 1
    layer.candidates = [candidate for candidate in combined if candidate.id not in discarded]
