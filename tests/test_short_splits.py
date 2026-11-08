"""Weak-short proposals preserve raw evidence and require explicit review."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from pkg_re.graph import analyze_graph, contact
from pkg_re.models import Calibration, Candidate, Layer, Marker
from pkg_re.store import Pixels, State, Store


def short_state(tmp_path: Path, bridge_rgb: int = 115) -> tuple[State, Store]:
    store = Store(tmp_path)
    state = store.create("Short")
    layer = Layer(id="layer", name="Short", width=64, height=40, analyzed=True)
    layer.markers = [
        Marker(id=str(x), kind="net", x=x, y=20, net=net, confirmed=True) for x, net in ((10, "A"), (54, "B"))
    ]
    px = Pixels.blank(layer)
    px.observed[10:31, 5:28] = True
    px.observed[10:31, 36:59] = True
    px.observed[19:22, 28:36] = True
    rgb = np.full((40, 64, 3), 20, dtype=np.uint8)
    rgb[px.observed] = 200
    rgb[19:22, 28:36] = bridge_rgb
    state.project.layers = [layer]
    state.pixels[layer.id] = px
    Image.fromarray(rgb).save(store.folder(state.project.id) / "layer.png")
    return state, store


def test_weak_bridge_proposes_erase_that_separates_nets_and_preserves_contacts(tmp_path):
    # Given two named planes joined only through a dim thin observed bridge.
    state, store = short_state(tmp_path)
    px = state.pixels["layer"]
    before = px.observed.copy()
    # When
    from pkg_re.short_splits import add_short_split_candidates

    add_short_split_candidates(state, store, "layer")
    # Then the proposal itself changes no geometry; applying its erase separates A/B.
    splits = [c for c in state.layer("layer").candidates if c.kind == "short_split"]
    assert len(splits) == 1
    assert splits[0].status == "pending"
    np.testing.assert_array_equal(px.observed, before)
    assert not px.erased.any()
    x, y, w, h = splits[0].bbox
    px.erased[y : y + h, x : x + w] |= px.patches[splits[0].id]
    graph = analyze_graph(state)
    assert {r.net for r in graph.regions["layer"]} == {"A", "B"}
    assert all(contact(graph.labels["layer"], m) for m in state.layer("layer").markers)


@pytest.mark.parametrize("blocked", ["strong", "protected", "marker", "ambiguous"])
def test_unsupported_or_protected_cut_stays_unproposed(tmp_path, blocked):
    # Given a bridge with no bounded safe optical cut.
    state, store = short_state(tmp_path, 200 if blocked == "strong" else 115)
    if blocked == "protected":
        state.pixels["layer"].protected[20, 31] = True
    elif blocked == "marker":
        state.layer("layer").markers.append(
            Marker(id="contact", kind="via", x=31, y=20, radius=2, confirmed=True)
        )
    elif blocked == "ambiguous":
        state.layer("layer").markers[1].net = ""
    # When
    from pkg_re.short_splits import add_short_split_candidates

    add_short_split_candidates(state, store, "layer")
    # Then
    assert not state.layer("layer").candidates


def test_split_survives_full_pending_budget_without_discarding_decisions(tmp_path):
    # Given a saturated repair queue and one already reviewed candidate.
    state, store = short_state(tmp_path)
    layer = state.layer("layer")
    for i in range(100):
        cid = f"old{i}"
        layer.candidates.append(
            Candidate(
                id=cid,
                kind="reconnect",
                bbox=(1, 1, 1, 1),
                pixels=1,
                reason="old",
                status="accepted" if i == 0 else "pending",
            )
        )
        state.pixels["layer"].patches[cid] = np.ones((1, 1), dtype=bool)
    # When
    from pkg_re.short_splits import add_short_split_candidates

    add_short_split_candidates(state, store, "layer")
    # Then
    assert layer.candidates[0].kind == "short_split"
    assert len(layer.candidates) == 100
    assert any(c.id == "old0" and c.status == "accepted" for c in layer.candidates)


def test_repeated_generation_keeps_one_identical_cut(tmp_path):
    # Given an existing short-split recommendation.
    state, store = short_state(tmp_path)
    from pkg_re.short_splits import add_short_split_candidates

    add_short_split_candidates(state, store, "layer")
    # When
    add_short_split_candidates(state, store, "layer")
    # Then
    assert len(state.layer("layer").candidates) == 1


def test_cut_preserves_via_contact_on_remote_endpoint_layer(tmp_path):
    # Given the weak bridge is the physical landing point of a via from another layer.
    state, store = short_state(tmp_path)
    target = state.layer("layer")
    target.calibration = Calibration(mm_per_pixel=1)
    source = Layer(id="source", name="Source", width=64, height=40, calibration=Calibration(mm_per_pixel=1))
    source.markers = [
        Marker(id="remote", kind="via", x=31, y=20, radius=1, confirmed=True, end_layer_id="layer")
    ]
    source_px = Pixels.blank(source)
    source_px.observed[19:22, 30:33] = True
    state.project.layers.insert(0, source)
    state.pixels[source.id] = source_px
    # When
    from pkg_re.short_splits import add_short_split_candidates

    add_short_split_candidates(state, store, "layer")
    # Then
    assert not target.candidates
