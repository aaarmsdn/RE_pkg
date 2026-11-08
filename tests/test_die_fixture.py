"""Dense-pad truth checks, independent of reconstruction."""

from collections import Counter

import numpy as np
import pytest
from scipy import ndimage

from pkg_re.bga_render import render_layer
from pkg_re.die_fixture import die_fixture, die_fixture_metadata


@pytest.fixture(scope="module", params=["edge_dense", "center_rows", "center_array"])
def fixture(request):
    return die_fixture(request.param), request.param


def test_grid_and_dimensions(fixture):
    stack, layout = fixture
    balls = stack.layers[0].terminals
    assert Counter(t.net for t in balls) == Counter(
        {**{f"DQ{i}": 1 for i in range(16)}, "VSS": 8, "VDD": 4, "VDDQ": 4}
    )
    assert {t.radius for t in balls} == {24}
    assert np.all(np.diff(sorted({t.x for t in balls})) == 160)
    assert np.all(np.diff(sorted({t.y for t in balls})) == 160)
    metadata = die_fixture_metadata(stack, layout)
    assert metadata["pad_width_px"] == 6
    assert metadata["pad_height_px"] == 12
    assert metadata["trace_width_px"] == 3
    assert metadata["pad_pitch_px"] == 16
    pads = stack.layers[1].terminals
    assert len(pads) == 22
    by_name = {net.name: net.mask for net in stack.layers[1].nets}
    for pad in pads:
        mask = by_name[pad.net]
        # Sample off the connected neck: measure actual raster, not metadata literals.
        assert mask[pad.y, pad.x - 4 : pad.x + 4].tolist() == [False] + [True] * 6 + [False]
        assert mask[pad.y - 7 : pad.y + 7, pad.x - 2].tolist() == [False] + [True] * 12 + [False]
        neck_y = pad.y - 12 if pad.y < stack.height / 2 else pad.y + 12
        assert mask[neck_y, pad.x - 2 : pad.x + 3].tolist() == [False, True, True, True, False]
    assert len({t.y for t in pads}) == (4 if layout == "center_array" else 2)
    if layout != "edge_dense":
        assert all(abs(t.x - stack.width / 2) < 120 and abs(t.y - stack.height / 2) < 150 for t in pads)


def test_no_shorts_and_real_vias(fixture):
    stack, _ = fixture
    counts = Counter(v.net for v in stack.layers[0].vias)
    assert all(counts[f"DQ{i}"] == 1 for i in range(16))
    assert all(counts[n] >= 15 for n in ("VSS", "VDD", "VDDQ"))
    for layer in stack.layers:
        occupied = np.sum([n.mask for n in layer.nets], axis=0)
        assert occupied.max() == 1
        by_name = {n.name: n for n in layer.nets}
        for net in layer.nets:
            assert ndimage.label(net.mask)[1] == 1, (layer.name, net.name)
            assert not np.any(
                ndimage.binary_dilation(net.mask, structure=np.ones((3, 3))) & (occupied > net.mask)
            ), (layer.name, net.name)
            assert net.mask[net.seed[1], net.seed[0]]
        for contact in (*layer.terminals, *layer.vias):
            assert by_name[contact.net].mask[contact.y, contact.x]
        for n in layer.nets:
            assert not np.any(n.plane_mask & ~n.mask)


def test_damage_intersects_fine_trace_and_png_roundtrip(fixture):
    import cv2

    stack, _ = fixture
    layer = stack.layers[1]
    clean = render_layer(layer, "clean", 1)
    assert not clean.removed.any()
    for profile in ("damaged", "severe"):
        rendered = render_layer(layer, profile, 1)
        assert any(e.kind == "trace_gap" and e.removed_px > 0 for e in rendered.events)
        dq6 = next(n for n in layer.nets if n.name == "DQ6")
        assert ndimage.label(dq6.mask & ~rendered.removed)[1] > 1
        ok, encoded = cv2.imencode(".png", rendered.image)
        assert ok
        assert np.array_equal(cv2.imdecode(encoded, cv2.IMREAD_COLOR), rendered.image)


def test_actual_parallel_gap_and_power_damage(fixture):
    from pkg_re.die_render import render_die_layer

    stack, layout = fixture
    layer = stack.layers[1]
    power = next(n for n in layer.nets if n.name == "VSS")
    signals = np.logical_or.reduce([n.mask for n in layer.nets if n.name.startswith("DQ")])
    distance = ndimage.distance_transform_cdt(~signals, metric="chessboard")
    assert distance[power.mask].min() - 1 == die_fixture_metadata(stack, layout)["minimum_gap_px"]
    for profile in ("damaged", "severe"):
        rendered = render_die_layer(layer, profile, 1)
        assert any(e.kind == "fine_power_gap" and e.removed_px > 0 for e in rendered.events)
        assert ndimage.label(power.mask & ~rendered.removed)[1] > 1
        if profile == "severe":
            assert any(e.kind == "missing_die_pad" and e.removed_px == 72 for e in rendered.events)
