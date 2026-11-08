"""Explicit copper edits and repair proposal decisions."""

import uuid
from typing import assert_never

import numpy as np
from fastapi import HTTPException
from PIL import Image

from pkg_re.annotations import annotation_unknown_mask
from pkg_re.batch_review import decide_batch
from pkg_re.engine import SegmentationOptions, propose_repairs, segment_copper, stroke_mask
from pkg_re.models import Analyze, BatchDecision, Candidate, Decision, Parameters, Stroke
from pkg_re.store import State, Store


def analyze_layer(state: State, store: Store, lid: str, options: Analyze) -> None:
    layer = state.layer(lid)
    x, y, w, h = options.roi or (0, 0, layer.width, layer.height)
    if min(x, y) < 0 or min(w, h) <= 0 or x + w > layer.width or y + h > layer.height:
        raise HTTPException(422, "ROI is outside the source image")
    if w * h > 4_000_000:
        raise HTTPException(
            422, "Select a native-resolution ROI of at most 4 million pixels; image is not downsampled"
        )
    with Image.open(store.folder(state.project.id) / f"{lid}.png") as image:
        rgb = np.array(image.crop((x, y, x + w, y + h)))
    config = SegmentationOptions(**options.model_dump(exclude={"roi", "auto_process"}))
    pixels = state.pixels[lid]
    unknown = annotation_unknown_mask(rgb, layer.markers, (x, y))
    pixels.observed[y : y + h, x : x + w] = segment_copper(rgb, config) & ~unknown
    observed = pixels.accepted()[y : y + h, x : x + w]
    proposals = propose_repairs(observed, pixels.protected[y : y + h, x : x + w], config)
    pixels.patches = {}
    layer.candidates = []
    for proposal in proposals:
        px, py, pw, ph = proposal.bbox
        cid = uuid.uuid4().hex
        local = proposal.mask
        reason = proposal.reason
        annotation_overlap = bool(np.any(local & unknown))
        if annotation_overlap:
            reason += " Crosses annotation occlusion: underlying material is unknown."
        pixels.patches[cid] = local[py : py + ph, px : px + pw].copy()
        layer.candidates.append(
            Candidate(
                id=cid,
                kind=proposal.kind,
                bbox=(x + px, y + py, pw, ph),
                pixels=proposal.pixels,
                reason=reason,
                annotation_overlap=annotation_overlap,
            )
        )
    layer.analyzed = True
    layer.roi = options.roi
    layer.parameters = Parameters(**options.model_dump(exclude={"roi", "auto_process"}))
    layer.review_summary = None
    layer.warnings = [
        "Heuristic copper mask: inspect source edges and clearances before use.",
        "Every repair is a proposal, not proof of missing metal.",
    ]
    if options.material_mode == "red_chroma":
        layer.warnings.append(
            "Red chroma calibration selects R - 2G + B above the configured threshold. "
            "Suitable only when copper is redder than dielectric; verify source samples. "
            "Lighting, oxidation and neutral metal can remain unresolved."
        )
    coverage = float(np.mean(pixels.observed[y : y + h, x : x + w]))
    if coverage > 0.90:
        layer.warnings.append(
            f"Copper mask covers {coverage:.1%} of this ROI: bright background or merged regions "
            "may be included. Inspect copper/background separation before assigning nets."
        )
    if not any(
        marker.confirmed and marker.net.strip() for item in state.project.layers for marker in item.markers
    ):
        layer.warnings.append(
            "No confirmed named net seeds in this stack. Copper regions remain UNASSIGNED until "
            "a named marker or ballmap is confirmed on copper; photo color does not identify net names."
        )
    if unknown.any():
        layer.warnings.append(
            "Annotation-covered pixels are unknown, not observed copper or proven dielectric. "
            "Approved manual geometry remains inferred."
        )
    if options.roi:
        layer.warnings.append(
            "Native ROI analyzed. Pixels outside analyzed ROIs are unknown, not dielectric."
        )
    if len(proposals) >= 100:
        layer.warnings.append(
            "Proposal limit reached (100). Review a smaller ROI to inspect additional gaps."
        )


def apply_stroke(state: State, lid: str, stroke: Stroke) -> None:
    layer = state.layer(lid)
    if any(not 0 <= p.x < layer.width or not 0 <= p.y < layer.height for p in stroke.points):
        raise HTTPException(422, "Stroke coordinates outside image")
    pixels = state.pixels[lid]
    mask = stroke_mask((layer.height, layer.width), [(p.x, p.y) for p in stroke.points], stroke.radius)
    match stroke.kind:
        case "add":
            pixels.added |= mask & ~pixels.protected
            pixels.erased &= ~mask
        case "erase":
            pixels.erased |= mask
            pixels.added &= ~mask
        case "protect":
            pixels.protected |= mask
            pixels.added &= ~mask
        case "unprotect":
            pixels.protected &= ~mask
        case unreachable:
            assert_never(unreachable)


def decide_candidate(state: State, lid: str, decision: Decision) -> None:
    decide_batch(
        state,
        lid,
        BatchDecision(
            ids=[decision.id], decision=decision.decision, expected_revision=state.project.revision
        ),
    )
