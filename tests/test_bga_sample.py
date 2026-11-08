"""PNG ingestion must remain independent from synthetic geometry truth."""

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from pkg_re.annotations import apply_ballmap
from pkg_re.app import create_app
from pkg_re.bga_benchmark import evaluate
from pkg_re.bga_fixture import BgaLayer, BgaNet, BgaTerminal
from pkg_re.bga_render import render_layer
from pkg_re.bga_sample import ballmap_input, create_bga_sample
from pkg_re.models import Analyze, CreateProject
from pkg_re.operations import analyze_layer
from pkg_re.store import Store


def optical_fixture():
    mask = np.zeros((180, 240), dtype=bool)
    mask[20:160, 20:220] = True
    plane = mask.copy()
    balls = (BgaTerminal("B2", "ball", "DQ2", 60, 60, 12), BgaTerminal("B5", "ball", "DQ5", 120, 60, 12))
    return BgaLayer("L1", (BgaNet("VSS", mask, plane, (100, 100)),), balls, ())


def test_bga_sample_modes_are_explicit_and_old_demo_is_compatible():
    # Given the existing create request and three new sample choices.
    old = CreateProject(demo=True)
    # When decoding a BGA sample request.
    damaged = CreateProject.model_validate({"demo": True, "sample": "bga_damaged"})
    # Then the old dense fixture remains the default.
    assert old.sample == "dense"
    assert damaged.sample == "bga_damaged"


def test_damage_is_reproducible_and_removes_whole_and_half_lands():
    # Given a pristine geometry with two labeled land sites.
    layer = optical_fixture()
    # When rendering repeatable damage to the raster only.
    result = render_layer(layer, "damaged", 0)
    again = render_layer(layer, "damaged", 0)
    # Then the input geometry is unchanged and optical damage is explicit.
    assert np.array_equal(result.image, again.image)
    assert layer.nets[0].mask[60, 60]
    assert result.removed[60, 60]
    assert result.image[60, 60].max() < 60
    assert result.removed[60, 120]
    assert not result.removed[60, 115]
    assert {e.kind for e in result.events} >= {"missing_ball", "half_ball", "plane_scratch"}


def test_clean_render_keeps_native_copper_and_background_separable():
    # Given pristine geometry.
    layer = optical_fixture()
    # When rendering a clean optical control.
    result = render_layer(layer, "clean", 0)
    # Then geometry is represented without damage, resizing or inferred fill.
    assert result.image.shape == (180, 240, 3)
    assert not result.removed.any()
    assert result.image[60, 60, 0] > 150
    assert result.image[0, 0].max() < 40


@pytest.fixture(scope="module")
def bga():
    from pkg_re.bga_fixture import bga_fixture

    return bga_fixture()


def test_clean_png_reimport_recovers_upper_pad_nets_without_upper_labels(tmp_path, bga):
    # Given only PNG bytes and supplied ball/via coordinates in normal application state.
    store = Store(tmp_path)
    state = store.create("clean PNG")
    create_bga_sample(state, store, "clean", bga)
    assert all(not state.pixels[layer.id].accepted().any() for layer in state.project.layers)
    assert all(not m.net for m in state.project.layers[1].markers)
    # When the ordinary pipeline reads each stored PNG.
    for layer in state.project.layers:
        analyze_layer(state, store, layer.id, Analyze())
    rows = evaluate(state, bga, "test")
    # Then copper and every physical terminal recover without prefilled truth masks.
    assert all(row["iou_pristine"] == 1 for row in rows)
    assert all(row["conflict_px"] == 0 for row in rows)
    assert all(all(t["correct"] for t in row["terminals"]) for row in rows)


def test_missing_ball_is_unknown_until_explicit_land_restore(tmp_path, bga):
    # Given the damaged PNG and known populated ballmap, with no prefilled copper.
    store = Store(tmp_path)
    state = store.create("missing land PNG")
    create_bga_sample(state, store, "damaged", bga)
    lower = state.project.layers[0]
    ball = next(t for t in bga.layers[0].terminals if t.net == "DQ2")
    for layer in state.project.layers:
        analyze_layer(state, store, layer.id, Analyze())
    assert not state.pixels[lower.id].observed[ball.y, ball.x]
    original = store.folder(state.project.id) / f"{lower.id}.png"
    source_bytes = original.read_bytes()
    # When an explicit populated-grid restoration is requested.
    apply_ballmap(state, lower.id, ballmap_input(bga, restore=True))
    # Then only inferred geometry gets the land; source and observation remain unchanged.
    assert state.pixels[lower.id].grid_added[ball.y, ball.x]
    assert not state.pixels[lower.id].observed[ball.y, ball.x]
    assert original.read_bytes() == source_bytes
    with Image.open(original) as image:
        assert max(image.getpixel((ball.x, ball.y))) < 60


def test_new_bga_modes_are_available_through_real_api(tmp_path):
    # Given the same HTTP boundary used by the GUI.
    with TestClient(create_app(tmp_path)) as client:
        # When requesting the new clean sample.
        response = client.post("/api/projects", json={"demo": True, "sample": "bga_clean"})
        # Then a real two-layer PNG project is returned with no analyzed geometry.
        assert response.status_code == 200
        layers = response.json()["layers"]
        assert len(layers) == 2
        assert all(not layer["analyzed"] and not layer["net_legend"] for layer in layers)
        assert len([m for m in layers[0]["markers"] if m["kind"] == "ball"]) == 32
        assert all(not m["net"] for m in layers[1]["markers"])
