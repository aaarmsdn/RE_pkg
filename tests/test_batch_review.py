"""A group decision is one reversible operation with joint topology validation."""

import io

import numpy as np
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from PIL import Image

from pkg_re.app import create_app
from pkg_re.batch_review import decide_batch
from pkg_re.images import add_image
from pkg_re.models import BatchDecision, Candidate, Marker
from pkg_re.store import Store


def setup_three_islands(tmp_path):
    store = Store(tmp_path)
    state = store.create("Joint repair")
    out = io.BytesIO()
    Image.new("RGB", (60, 30)).save(out, format="PNG")
    layer = add_image(state, store, out.getvalue(), "L1")
    layer.analyzed = True
    px = state.pixels[layer.id]
    for x in (5, 20, 35):
        px.observed[10:15, x : x + 11] = True
    layer.markers = [
        Marker(id="a", kind="ball", x=8, y=12, net="VSS", confirmed=True),
        Marker(id="b", kind="pad", x=40, y=12, net="VDD", confirmed=True),
    ]
    for cid, x in (("first", 16), ("second", 31)):
        layer.candidates.append(
            Candidate(id=cid, kind="reconnect", bbox=(x, 10, 4, 5), pixels=20, reason="Test independent gaps")
        )
        px.patches[cid] = np.ones((5, 4), dtype=bool)
    store.save(state)
    return store, state, layer


def test_combined_repairs_cannot_short_two_nets_and_failed_call_restores_buffers(tmp_path):
    # Given two independently plausible joins through an unnamed middle island.
    _, state, layer = setup_three_islands(tmp_path)
    before = state.pixels[layer.id].accepted().copy()
    # When both are accepted together they would connect VSS and VDD.
    with pytest.raises(HTTPException) as error:
        decide_batch(
            state, layer.id, BatchDecision(ids=["first", "second"], decision="accepted", expected_revision=0)
        )
    # Then the whole group fails with no partial edit or status changes.
    assert error.value.status_code == 409
    assert np.array_equal(state.pixels[layer.id].accepted(), before)
    assert not state.pixels[layer.id].added.any()
    assert all(c.status == "pending" for c in layer.candidates)


def test_batch_reject_has_one_undo_snapshot(tmp_path):
    # Given two pending repairs in the real HTTP store.
    _, state, layer = setup_three_islands(tmp_path)
    prefix = f"/api/projects/{state.project.id}"
    with TestClient(create_app(tmp_path)) as client:
        # When rejecting the selection through the API.
        result = client.post(
            f"{prefix}/layers/{layer.id}/candidates/batch",
            json={"ids": ["first", "second"], "decision": "rejected", "expected_revision": 0},
        )
        # Then one undo restores both candidates together.
        assert result.status_code == 200
        assert result.json()["history_count"] == 1
        assert all(c["status"] == "rejected" for c in result.json()["layers"][0]["candidates"])
        undone = client.post(prefix + "/undo").json()
        assert all(c["status"] == "pending" for c in undone["layers"][0]["candidates"])


@pytest.mark.parametrize("ids,revision", [(["missing"], 0), (["first", "first"], 0), (["first"], 5)])
def test_stale_or_invalid_batch_never_changes_geometry(tmp_path, ids, revision):
    # Given a current project and invalid selection metadata.
    _, state, layer = setup_three_islands(tmp_path)
    # When applying the stale/unknown/duplicated selection.
    with pytest.raises(HTTPException):
        decide_batch(state, layer.id, BatchDecision(ids=ids, decision="accepted", expected_revision=revision))
    # Then no geometry or candidate statuses change.
    assert not state.pixels[layer.id].added.any()
    assert all(c.status == "pending" for c in layer.candidates)


def test_auto_rechecks_after_each_join_and_one_undo_restores_all(tmp_path):
    store, state, layer = setup_three_islands(tmp_path)
    px = state.pixels[layer.id]
    px.observed[:] = False
    for start, end in ((5, 25), (27, 45), (47, 59)):
        px.observed[11:14, start:end] = True
    layer.markers = [
        Marker(id="left", kind="net", x=8, y=12, net="VSS", confirmed=True),
        Marker(id="right", kind="net", x=55, y=12, net="VDD", confirmed=True),
    ]
    for candidate, x in zip(layer.candidates, (25, 45), strict=True):
        candidate.bbox = (x, 11, 2, 3)
        candidate.pixels = 6
        candidate.annotation_overlap = False
        px.patches[candidate.id] = np.ones((3, 2), dtype=bool)
    store.save(state)
    prefix = f"/api/projects/{state.project.id}"
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(f"{prefix}/layers/{layer.id}/candidates/auto", json={"expected_revision": 0})
        assert response.status_code == 200
        result = response.json()
        assert [c["status"] for c in result["layers"][0]["candidates"]] == ["accepted", "rejected"]
        assert result["layers"][0]["review_summary"] == {
            "accepted": 1,
            "rejected": 1,
            "review": 0,
            "source": "automatic",
        }
        assert not any(area["status"] == "conflict" for area in result["areas"])
        assert result["history_count"] == 1
        restored = client.post(prefix + "/undo").json()
        assert all(c["status"] == "pending" for c in restored["layers"][0]["candidates"])
        assert not store.load(state.project.id).pixels[layer.id].added.any()


def test_cut_acceptance_preserves_source_and_revalidates_changed_terminal(tmp_path):
    from test_short_splits import short_state

    from pkg_re.short_splits import add_short_split_candidates

    state, store = short_state(tmp_path)
    add_short_split_candidates(state, store, "layer")
    candidate = state.layer("layer").candidates[0]
    px = state.pixels["layer"]
    source = px.observed.copy()
    state.layer("layer").markers.append(Marker(id="new", kind="pad", x=31, y=20, net="", confirmed=True))
    with pytest.raises(HTTPException):
        decide_batch(
            state, "layer", BatchDecision(ids=[candidate.id], decision="accepted", expected_revision=0)
        )
    assert not px.erased.any()
    assert candidate.status == "pending"
    state.layer("layer").markers.pop()
    decide_batch(state, "layer", BatchDecision(ids=[candidate.id], decision="accepted", expected_revision=0))
    assert px.erased.sum() == 24
    assert np.array_equal(px.observed, source)


def test_auto_never_applies_short_split(tmp_path):
    from test_short_splits import short_state

    from pkg_re.batch_review import auto_review
    from pkg_re.models import AutoReview
    from pkg_re.short_splits import add_short_split_candidates

    state, store = short_state(tmp_path)
    add_short_split_candidates(state, store, "layer")
    auto_review(state, "layer", AutoReview(expected_revision=0))
    assert state.layer("layer").candidates[0].status == "pending"
    assert not state.pixels["layer"].erased.any()


def test_addition_cannot_make_existing_physical_via_contact_ambiguous(tmp_path):
    from pkg_re.models import Calibration, Layer
    from pkg_re.store import Pixels

    _, state, bottom = setup_three_islands(tmp_path)
    bottom.calibration = Calibration(mm_per_pixel=1)
    bottom.markers = []
    px = state.pixels[bottom.id]
    px.observed[:] = False
    px.observed[10, 8:11] = True
    bottom.candidates = [
        Candidate(
            id="isolated",
            kind="reconnect",
            bbox=(14, 10, 1, 1),
            pixels=1,
            reason="new disconnected copper inside via radius",
        )
    ]
    px.patches = {"isolated": np.ones((1, 1), dtype=bool)}
    top = Layer(id="top", name="Top", width=60, height=30, calibration=Calibration(mm_per_pixel=1))
    top.markers = [
        Marker(
            id="via",
            kind="via",
            x=12,
            y=10,
            net="VSS",
            confirmed=True,
            end_layer_id=bottom.id,
            contact_radius=5,
        )
    ]
    state.project.layers.insert(0, top)
    state.pixels[top.id] = Pixels.blank(top)
    state.pixels[top.id].observed[10, 12] = True
    with pytest.raises(HTTPException, match="contact"):
        decide_batch(
            state, bottom.id, BatchDecision(ids=["isolated"], decision="accepted", expected_revision=0)
        )
    assert not px.added.any()
    assert bottom.candidates[0].status == "pending"
