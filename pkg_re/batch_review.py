"""Atomic group decisions and conservative NET-assisted review."""

from typing import Literal

import numpy as np
from fastapi import HTTPException

from pkg_re.graph import GraphResult, analyze_graph
from pkg_re.models import AutoReview, BatchDecision, Candidate, ReviewSummary
from pkg_re.net_review import refresh_recommendations
from pkg_re.short_splits import contacts_survive
from pkg_re.store import State


def validate_selection(state: State, lid: str, ids: list[str] | None, revision: int) -> list[Candidate]:
    if revision != state.project.revision:
        raise HTTPException(409, "Project changed; refresh the selection before deciding")
    candidates = state.layer(lid).candidates
    if ids is None:
        return [c for c in candidates if c.status == "pending"]
    if len(ids) != len(set(ids)):
        raise HTTPException(422, "Duplicate candidate IDs")
    lookup = {c.id: c for c in candidates}
    if any(cid not in lookup for cid in ids):
        raise HTTPException(404, "Candidate not found; refresh the selection")
    selected = [lookup[cid] for cid in ids]
    if any(c.status != "pending" for c in selected):
        raise HTTPException(409, "Candidate already decided; undo or reanalyze")
    return selected


def _validate_topology(state: State, before: GraphResult, after: GraphResult, removed: int) -> None:
    for lid, regions in after.regions.items():
        previous = {r.id: r for r in before.regions[lid]}
        for region in regions:
            if region.status != "conflict":
                continue
            names = set(region.net.split(" | "))
            touched = np.unique(before.labels[lid][after.labels[lid] == region.id])
            if any(
                rid == 0
                or previous[int(rid)].status != "conflict"
                or not names.issubset(set(previous[int(rid)].net.split(" | ")))
                for rid in touched
            ):
                raise HTTPException(409, "Repair creates or expands a conflicting-net component")
    if not contacts_survive(state, before, after):
        raise HTTPException(409, "Repair would break a confirmed terminal or physical via contact")
    if set(after.warnings) - set(before.warnings):
        raise HTTPException(409, "Repair would break a confirmed marker or physical via contact")
    if removed:
        before_count = sum(r.total_px for r in before.areas if r.status == "conflict")
        after_count = sum(r.total_px for r in after.areas if r.status == "conflict")
        if before_count - after_count <= removed:
            raise HTTPException(409, "Split no longer separates conflicting NETs; regenerate candidates")
    # Even added copper can make a radius-based terminal contact ambiguous.
    for lid, regions in before.regions.items():
        named_after = {r.id: r.net for r in after.regions[lid] if r.status == "assigned"}
        for region in regions:
            if region.status == "assigned":
                touched = np.unique(after.labels[lid][before.labels[lid] == region.id])
                if any(rid and named_after.get(int(rid)) != region.net for rid in touched):
                    raise HTTPException(409, "Repair would disconnect previously assigned copper")


def decide_batch(
    state: State,
    lid: str,
    data: BatchDecision,
    source: Literal["manual", "automatic"] = "manual",
) -> None:
    selected = validate_selection(state, lid, data.ids, data.expected_revision)
    layer = state.layer(lid)
    px = state.pixels[lid]
    if data.decision == "accepted":
        original_added, original_erased = px.added, px.erased
        before = analyze_graph(state)
        px.added, px.erased = px.added.copy(), px.erased.copy()
        try:
            for candidate in selected:
                x, y, w, h = candidate.bbox
                patch = px.patches[candidate.id]
                if (patch & px.protected[y : y + h, x : x + w]).any():
                    raise HTTPException(409, "Candidate crosses an explicit protection")
                if candidate.kind == "short_split":
                    if source == "automatic" or (patch & px.inferred()[y : y + h, x : x + w]).any():
                        raise HTTPException(
                            409, "Split requires manual review and cannot erase inferred copper"
                        )
                    px.erased[y : y + h, x : x + w] |= patch
                    px.added[y : y + h, x : x + w] &= ~patch
                else:
                    if (patch & px.erased[y : y + h, x : x + w]).any():
                        raise HTTPException(
                            409, "Candidate crosses an explicit erase; use manual add after review"
                        )
                    px.added[y : y + h, x : x + w] |= patch
            after = analyze_graph(state)
            removed = int(((px.erased & ~original_erased) & (px.observed | original_added)).sum())
            if any(c.kind == "short_split" for c in selected) and not removed:
                raise HTTPException(409, "Split is stale; regenerate candidates")
            _validate_topology(state, before, after, removed)
        except BaseException:
            px.added, px.erased = original_added, original_erased
            raise
    for candidate in selected:
        candidate.status = data.decision
        candidate.decision_source = source
    layer.review_summary = ReviewSummary(
        accepted=len(selected) if data.decision == "accepted" else 0,
        rejected=len(selected) if data.decision == "rejected" else 0,
        review=sum(c.status == "pending" for c in layer.candidates),
        source=source,
    )


def auto_review(state: State, lid: str, data: AutoReview) -> None:
    """Recompute after each accepted repair; one outer transaction owns undo."""
    selected = validate_selection(state, lid, data.ids, data.expected_revision)
    scope = {c.id for c in selected}
    blocked: set[str] = set()
    accepted = rejected = 0
    while True:
        refresh_recommendations(state, lid)
        pending = [c for c in selected if c.status == "pending" and c.id not in blocked]
        reject_ids = [c.id for c in pending if c.recommendation == "reject"]
        if reject_ids:
            decide_batch(
                state,
                lid,
                BatchDecision(ids=reject_ids, decision="rejected", expected_revision=data.expected_revision),
                source="automatic",
            )
            rejected += len(reject_ids)
        candidate = next(
            (c for c in pending if c.recommendation == "accept" and c.kind != "short_split"), None
        )
        if candidate is None:
            break
        try:
            decide_batch(
                state,
                lid,
                BatchDecision(
                    ids=[candidate.id], decision="accepted", expected_revision=data.expected_revision
                ),
                source="automatic",
            )
            accepted += 1
        except HTTPException as error:
            if error.status_code != 409:
                raise
            blocked.add(candidate.id)
    refresh_recommendations(state, lid)
    for candidate in selected:
        if candidate.id in blocked:
            candidate.recommendation = "review"
            candidate.recommendation_reason = (
                "Joint topology guard refused this repair; inspect its contacts."
            )
    state.layer(lid).review_summary = ReviewSummary(
        accepted=accepted,
        rejected=rejected,
        review=sum(c.id in scope and c.status == "pending" for c in selected),
        source="automatic",
    )
