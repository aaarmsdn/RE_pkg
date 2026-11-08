"""Physical raster tests for woven reference inputs, independent of inference."""

from collections import Counter

import cv2
import numpy as np
import pytest
from scipy import ndimage

from pkg_re.weave_fixture import weave_fixture, weave_metadata
from pkg_re.weave_render import render_weave_layer


@pytest.fixture(scope="module", params=["weave16", "weave32", "micro32"])
def fixture(request):
    return weave_fixture(request.param), request.param


def test_physical_connectivity_and_no_eight_neighbor_shorts(fixture):
    stack, layout = fixture
    count = 16 if layout == "weave16" else 32
    assert {n.name for n in stack.layers[0].nets} == {"VSS", "VDD", "VDDQ"} | {f"DQ{i}" for i in range(count)}
    counts = Counter(v.net for v in stack.layers[0].vias)
    assert all(counts[f"DQ{i}"] == 1 for i in range(count))
    assert all(counts[n] >= 15 for n in ("VSS", "VDD", "VDDQ"))
    for layer in stack.layers:
        occupied = np.sum([n.mask for n in layer.nets], axis=0)
        assert occupied.max() == 1
        by_name = {n.name: n for n in layer.nets}
        for net in layer.nets:
            assert ndimage.label(net.mask)[1] == 1, (layout, layer.name, net.name)
            expanded = ndimage.binary_dilation(net.mask, structure=np.ones((3, 3)))
            assert not np.any(expanded & (occupied > net.mask)), (layout, layer.name, net.name)
        for contact in (*layer.terminals, *layer.vias):
            assert by_name[contact.net].mask[contact.y, contact.x]
    assert stack.layers[0].vias == stack.layers[1].vias


def test_real_pad_dimensions_mapping_and_route_complexity(fixture):
    stack, layout = fixture
    meta = weave_metadata(stack, layout)
    width, height = (2, 4) if layout == "micro32" else (4, 8)
    assert meta["pad_width_px"] == width
    assert meta["pad_height_px"] == height
    assert meta["minimum_gap_px"] >= 1
    assert meta["mapping_order_inversions"] > 0
    assert meta["minimum_signal_bends"] >= 12
    by_name = {n.name: n for n in stack.layers[1].nets}
    for pad in stack.layers[1].terminals:
        mask = by_name[pad.net].mask
        assert mask[pad.y - height // 2 : pad.y + height // 2, pad.x - width // 2 : pad.x + width // 2].all()
        # Opposite side of horizontal incoming neck observes exact height.
        edge_x = pad.x if pad.x < 896 else pad.x - 1
        assert mask[pad.y - height // 2 - 1 : pad.y + height // 2 + 1, edge_x].tolist() == [False] + [
            True
        ] * height + [False]


def test_geometry_specific_damage_and_png_roundtrip(fixture):
    stack, layout = fixture
    layer = stack.layers[1]
    clean = render_weave_layer(layer, "clean", 1, layout)
    assert not clean.removed.any()
    for profile in ("damaged", "severe"):
        rendered = render_weave_layer(layer, profile, 1, layout)
        assert any(e.kind == "fine_power_gap" and e.removed_px > 0 for e in rendered.events)
        power = next(n for n in layer.nets if n.name == "VSS")
        assert ndimage.label(power.mask & ~rendered.removed)[1] > 1
        if profile == "severe":
            assert any(
                e.kind == "missing_die_pad" and e.removed_px == (8 if layout == "micro32" else 32)
                for e in rendered.events
            )
        ok, encoded = cv2.imencode(".png", rendered.image)
        assert ok
        assert np.array_equal(cv2.imdecode(encoded, cv2.IMREAD_COLOR), rendered.image)


def test_layouts_have_distinct_physical_copper():
    a, b = weave_fixture("weave32"), weave_fixture("micro32")
    assert not np.array_equal(a.layers[1].nets[-1].mask, b.layers[1].nets[-1].mask)


def test_lower_raster_contains_real_meanders(fixture):
    stack, layout = fixture
    for net in stack.layers[0].nets:
        if not net.name.startswith("DQ"):
            continue
        ball = next(t for t in stack.layers[0].terminals if t.net == net.name)
        via = next(v for v in stack.layers[0].vias if v.net == net.name)
        lo, hi = sorted((ball.x, via.x))
        corridor = ball.y if layout == "weave16" else ball.y + (88 if via.y > ball.y else -88)
        excursion = 12 if layout == "weave16" else 3
        # Observe copper on both alternating horizontal excursion rows.
        for y in (corridor - excursion, corridor + excursion):
            runs = ndimage.label(net.mask[y, lo + 20 : hi - 10])[1]
            assert runs >= 2, (net.name, y, runs)


def test_supplied_ballmap_grid_matches_every_center(fixture):
    stack, _ = fixture
    from pkg_re.bga_sample import ballmap_input

    metadata = ballmap_input(stack)
    balls = stack.layers[0].terminals
    assert {t.radius for t in balls} == {16}
    for ball in balls:
        assert (ball.x - min(t.x for t in balls)) % stack.pitch_px == 0
        assert (ball.y - min(t.y for t in balls)) % stack.pitch_px == 0
    assert metadata


@pytest.mark.parametrize("layout", ["weave32", "micro32"])
def test_adjacent_ball_rows_reverse_pad_order_within_each_bank(layout):
    stack = weave_fixture(layout)
    balls = [t for t in stack.layers[0].terminals if t.net.startswith("DQ")]
    pads = {t.net: t for t in stack.layers[1].terminals}
    for right in (False, True):
        for bottom in (False, True):
            bank = sorted(
                [b for b in balls if (b.x > 896) == right and (b.y > 768) == bottom], key=lambda b: b.y
            )
            assert len(bank) == 8
            for first, second in zip(bank[::2], bank[1::2], strict=True):
                assert first.y < second.y
                assert pads[first.net].y > pads[second.net].y


def test_plane_coverage_uses_canvas_minus_nonplane_geometry(fixture):
    # Given preserved native routing and contact geometry, when pouring each layer,
    # then planes occupy 90% of the independently reconstructed eligible area.
    stack, _ = fixture
    for layer in stack.layers:
        plane = np.logical_or.reduce([n.plane_mask for n in layer.nets])
        nonplane = np.logical_or.reduce([n.mask & ~n.plane_mask for n in layer.nets])
        assert not np.any(plane & nonplane)
        coverage = plane.sum() / (plane.size - nonplane.sum())
        assert 0.89 <= coverage <= 0.91, (layer.name, coverage)


def test_diagonal_profile_crosses_planes_and_signal_routes(fixture):
    # Given native copper, when rendering twice, then global diagonal damage is deterministic.
    stack, layout = fixture
    for index, layer in enumerate(stack.layers):
        first = render_weave_layer(layer, "diagonal", index, layout)
        second = render_weave_layer(layer, "diagonal", index, layout)
        assert np.array_equal(first.image, second.image)
        assert {e.kind for e in first.events} == {"diagonal_scratch"}
        planes = np.logical_or.reduce([n.plane_mask for n in layer.nets])
        signals = np.logical_or.reduce([n.mask for n in layer.nets if n.name.startswith("DQ")])
        assert (first.removed & planes).sum() > 1000
        assert (first.removed & signals).sum() > 50
        yy, xx = np.where(first.removed)
        assert ((2 * yy - xx + 31) % 181 < 7).all()


def test_pours_preserve_original_routing_and_denominator(fixture, monkeypatch):
    # Given the unpoured routing/contact construction, when planes are added,
    # then every original copper pixel and the eligible-area denominator survive.
    stack, layout = fixture
    monkeypatch.setattr("pkg_re.weave_fixture.pour_planes", lambda layer: layer)
    original = weave_fixture(layout)
    for before, after in zip(original.layers, stack.layers, strict=True):
        baseline = np.logical_or.reduce([n.mask & ~n.plane_mask for n in before.nets])
        measured = np.logical_or.reduce([n.mask & ~n.plane_mask for n in after.nets])
        assert np.array_equal(baseline, measured)
        for old, new in zip(before.nets, after.nets, strict=True):
            assert np.all(new.mask[old.mask])
            if old.name.startswith("DQ"):
                assert np.array_equal(old.mask, new.mask)
        plane_area = sum(int(n.plane_mask.sum()) for n in after.nets)
        assert 0.89 <= plane_area / (baseline.size - baseline.sum()) <= 0.91


def test_power_allocation_is_near_requested_shares(fixture):
    # Given three connected power pours, when measuring their area allocation,
    # then each power receives its requested share within five percentage points.
    stack, _ = fixture
    for layer in stack.layers:
        total = sum(int(n.plane_mask.sum()) for n in layer.nets)
        for net in layer.nets:
            if net.name in {"VSS", "VDDQ", "VDD"}:
                target = 0.5 if net.name == "VSS" else 0.25
                assert abs(net.plane_mask.sum() / total - target) <= 0.05
