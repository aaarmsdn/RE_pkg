"""Ordinary PNG recovery and conservative local geometry regressions."""

import numpy as np
import pytest

from pkg_re.batch_review import auto_review
from pkg_re.bga_render import render_layer
from pkg_re.bga_sample import create_bga_sample
from pkg_re.engine import SegmentationOptions, propose_repairs
from pkg_re.models import Analyze, AutoReview, Candidate, Layer, Marker, Project
from pkg_re.net_review import refresh_recommendations
from pkg_re.operations import analyze_layer
from pkg_re.store import Pixels, State, Store


def test_damaged_png_reconnects_traces_but_keeps_enclosed_voids_for_review(tmp_path):
    store = Store(tmp_path)
    state = store.create("Damaged recovery")
    fixture = create_bga_sample(state, store, "damaged")
    for layer in state.project.layers:
        analyze_layer(state, store, layer.id, Analyze())
    recovered = 0
    for index, layer in enumerate(state.project.layers):
        auto_review(state, layer.id, AutoReview(expected_revision=state.project.revision))
        added = state.pixels[layer.id].added
        truth = np.logical_or.reduce([n.mask for n in fixture.layers[index].nets])
        damaged = render_layer(fixture.layers[index], "damaged", index)
        assert not (added & ~truth).any()
        recovered += int((added & damaged.removed).sum())
        enclosed = [c for c in layer.candidates if c.kind == "plane_hole_fill"]
        assert enclosed
        assert all(c.status == "pending" and c.recommendation == "review" for c in enclosed)
        for event in damaged.events:
            if event.kind == "plane_hole":
                x, y, w, h = event.bbox
                assert not added[y : y + h, x : x + w].any()
    assert recovered > 0


@pytest.mark.parametrize("other_net,expected", [("SIGNAL", "accept"), ("OTHER", "reject"), ("", "accept")])
def test_stair_step_trace_gap_uses_local_direction(other_net, expected):
    layer = Layer(id="L", name="Trace", width=80, height=60)
    px = Pixels.blank(layer)
    for x in range(8, 72):
        y = 20 + x // 8
        px.observed[y : y + 3, x] = True
    px.observed[:, 39:41] = False
    layer.markers = [Marker(id="a", kind="net", x=12, y=22, net="SIGNAL", confirmed=True)]
    if other_net:
        layer.markers.append(Marker(id="b", kind="net", x=68, y=29, net=other_net, confirmed=True))
    proposals = propose_repairs(px.observed, px.protected, SegmentationOptions())
    for i, p in enumerate(proposals):
        x, y, w, h = p.bbox
        layer.candidates.append(
            Candidate(
                id=str(i),
                kind=p.kind,
                bbox=p.bbox,
                pixels=p.pixels,
                reason=p.reason,
                annotation_overlap=False,
            )
        )
        px.patches[str(i)] = p.mask[y : y + h, x : x + w]
    state = State(Project(id="p", name="p", layers=[layer]), {"L": px})
    refresh_recommendations(state, "L")
    assert len(layer.candidates) == 1
    assert layer.candidates[0].recommendation == expected


@pytest.mark.parametrize("other_net", ["", "OTHER"])
def test_adjacent_parallel_traces_never_auto_merge(other_net):
    layer = Layer(id="L", name="Parallel", width=80, height=60)
    px = Pixels.blank(layer)
    px.observed[20:23, 8:72] = True
    px.observed[25:28, 8:72] = True
    layer.markers = [Marker(id="a", kind="net", x=12, y=21, net="SIGNAL", confirmed=True)]
    if other_net:
        layer.markers.append(Marker(id="b", kind="net", x=12, y=26, net=other_net, confirmed=True))
    proposals = propose_repairs(px.observed, px.protected, SegmentationOptions())
    for i, p in enumerate(proposals):
        x, y, w, h = p.bbox
        layer.candidates.append(
            Candidate(
                id=str(i),
                kind=p.kind,
                bbox=p.bbox,
                pixels=p.pixels,
                reason=p.reason,
                annotation_overlap=False,
            )
        )
        px.patches[str(i)] = p.mask[y : y + h, x : x + w]
    state = State(Project(id="p", name="p", layers=[layer]), {"L": px})
    refresh_recommendations(state, "L")
    assert layer.candidates
    assert all(c.recommendation != "accept" for c in layer.candidates)


def test_small_continuity_gap_survives_large_gap_budget():
    observed = np.zeros((1500, 100), dtype=bool)
    for y in range(10, 1400, 12):
        observed[y : y + 3, 10:40] = True
        observed[y + 5 : y + 8, 10:40] = True
    observed[1440:1443, 10:40] = True
    observed[1440:1443, 42:72] = True
    proposals = propose_repairs(observed, np.zeros_like(observed), SegmentationOptions())
    assert len(proposals) == 100
    assert any(p.bbox == (40, 1440, 2, 3) for p in proposals)


def test_damaged_png_restores_upper_pad_connectivity_after_explicit_ball_restore(tmp_path):
    from pkg_re.annotations import apply_ballmap
    from pkg_re.bga_benchmark import evaluate
    from pkg_re.bga_sample import ballmap_input

    store = Store(tmp_path)
    state = store.create("Connectivity")
    fixture = create_bga_sample(state, store, "damaged")
    for layer in state.project.layers:
        analyze_layer(state, store, layer.id, Analyze())
    apply_ballmap(state, state.project.layers[0].id, ballmap_input(fixture, restore=True))
    before = evaluate(state, fixture, "before")
    assert sum(t["correct"] for t in before[1]["terminals"]) == 35
    for layer in state.project.layers:
        auto_review(state, layer.id, AutoReview(expected_revision=state.project.revision))
    after = evaluate(state, fixture, "after")
    assert sum(t["correct"] for t in after[1]["terminals"]) == 36
    assert all(row["conflict_px"] == 0 for row in after)
    for layer, reference in zip(state.project.layers, fixture.layers, strict=True):
        truth = np.logical_or.reduce([n.mask for n in reference.nets])
        assert not (state.pixels[layer.id].added & ~truth).any()


@pytest.mark.parametrize("layout", ["edge_dense", "center_rows"])
def test_dense_damaged_png_restores_oblique_trace_without_false_copper(tmp_path, layout):
    from pkg_re.annotations import apply_ballmap
    from pkg_re.bga_benchmark import evaluate
    from pkg_re.bga_sample import ballmap_input
    from pkg_re.die_sample import create_die_sample

    store = Store(tmp_path)
    state = store.create("Dense connectivity")
    fixture = create_die_sample(state, store, layout, "damaged")
    for layer in state.project.layers:
        analyze_layer(state, store, layer.id, Analyze())
    apply_ballmap(state, state.project.layers[0].id, ballmap_input(fixture, restore=True))
    for layer in state.project.layers:
        auto_review(state, layer.id, AutoReview(expected_revision=state.project.revision))
    after = evaluate(state, fixture, "after")
    assert sum(t["correct"] for t in after[1]["terminals"]) == 22
    assert all(row["conflict_px"] == 0 for row in after)
    for layer, reference in zip(state.project.layers, fixture.layers, strict=True):
        truth = np.logical_or.reduce([n.mask for n in reference.nets])
        assert not (state.pixels[layer.id].added & ~truth).any()


def test_diverging_narrow_endpoints_do_not_prove_continuity():
    from pkg_re.engine.continuity import trace_continuity

    observed = np.zeros((80, 80), dtype=bool)
    for y in range(10, 70):
        x = 30 + abs(y - 40)
        observed[y, x : x + 3] = True
    observed[39:41] = False
    assert not trace_continuity(observed, (31, 39, 2, 2), 4)
