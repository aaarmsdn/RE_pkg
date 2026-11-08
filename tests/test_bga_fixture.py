"""Physical checks of the intended package, independent of the image analyzer."""

from collections import Counter

import numpy as np
import pytest
from scipy import ndimage

from pkg_re.bga_fixture import bga_fixture


@pytest.fixture(scope="module")
def fixture():
    return bga_fixture()


def test_bga_grid_and_net_population(fixture):
    # Given the requested 8 by 4 ball grid and nominal calibration.
    balls = fixture.layers[0].terminals
    # When reading physical ball centers.
    xs = sorted({ball.x for ball in balls})
    ys = sorted({ball.y for ball in balls})
    counts = Counter(ball.net for ball in balls)
    # Then pitch, dimensions, and signal/power populations match the package.
    assert len(balls) == 32 and len(xs) == 8 and len(ys) == 4
    assert all(ball.kind == "ball" for ball in balls)
    assert np.allclose(np.diff(xs) * fixture.mm_per_pixel, 5)
    assert np.allclose(np.diff(ys) * fixture.mm_per_pixel, 5)
    assert counts == Counter({**{f"DQ{i}": 1 for i in range(16)}, "VSS": 8, "VDD": 4, "VDDQ": 4})
    assert fixture.width * fixture.height <= 4_000_000


def test_edge_pad_order_and_vdd_insertions(fixture):
    # Given the requested top and bottom edge sequences.
    pads = fixture.layers[1].terminals
    # When ordering each edge from left to right.
    rows = [
        sorted((pad for pad in pads if pad.y == y), key=lambda pad: pad.x)
        for y in sorted({pad.y for pad in pads})
    ]
    # Then each sequence has eight DQ pads, alternating reference pads, and three VDD pads.
    assert len(rows) == 2
    for row, first, center_pair in zip(rows, (8, 0), ((10, 11), (3, 4)), strict=True):
        assert [pad.net for pad in row if pad.net.startswith("DQ")] == [
            f"DQ{i}" for i in range(first, first + 8)
        ]
        assert [pad.net for pad in row if pad.net in ("VSS", "VDDQ")] == [
            "VSS",
            "VDDQ",
            "VSS",
            "VDDQ",
            "VSS",
            "VDDQ",
            "VSS",
        ]
        vdd = [pad for pad in row if pad.net == "VDD"]
        assert len(vdd) == 3 and row[0].net == row[-1].net == "VDD"
        by_net = {pad.net: pad for pad in row if pad.net.startswith("DQ")}
        assert by_net[f"DQ{center_pair[0]}"].x < vdd[1].x < by_net[f"DQ{center_pair[1]}"].x


def test_layers_have_no_shorts_and_every_terminal_contacts_its_net(fixture):
    # Given the pristine copper for each named net.
    for layer in fixture.layers:
        occupancy = np.zeros((fixture.height, fixture.width), dtype=np.uint8)
        by_name = {net.name: net for net in layer.nets}
        # When combining masks and checking every terminal center.
        for net in layer.nets:
            occupancy += net.mask
            assert net.mask.dtype == np.bool_
            assert net.mask[net.seed[1], net.seed[0]]
        # Then no distinct nets even touch through an eight-neighbor connection.
        assert occupancy.max() == 1
        for net in layer.nets:
            adjacent = ndimage.binary_dilation(net.mask, structure=np.ones((3, 3)))
            assert not np.any(adjacent & (occupancy > net.mask))
        for terminal in layer.terminals:
            assert by_name[terminal.net].mask[terminal.y, terminal.x]


def test_every_net_is_connected_through_real_via_contacts(fixture):
    # Given per-layer conductive islands and physical via declarations.
    all_vias = fixture.layers[0].vias
    counts = Counter(via.net for via in all_vias)
    assert all(counts[f"DQ{i}"] == 1 for i in range(16))
    assert all(counts[net] >= 15 for net in ("VSS", "VDD", "VDDQ"))
    for name in ("VSS", "VDD", "VDDQ", *(f"DQ{i}" for i in range(16))):
        labels = []
        parent = {}
        for index, layer in enumerate(fixture.layers):
            net = next(net for net in layer.nets if net.name == name)
            labeled, count = ndimage.label(net.mask)
            labels.append(labeled)
            for component in range(1, count + 1):
                parent[index, component] = (index, component)

        def root(key, parent=parent):
            while parent[key] != key:
                key = parent[key]
            return key

        # When joining only vias whose centers contain this net on both layers.
        for via in (via for via in all_vias if via.net == name):
            contacts = [(index, int(label[via.y, via.x])) for index, label in enumerate(labels)]
            assert all(component > 0 for _, component in contacts)
            parent[root(contacts[1])] = root(contacts[0])
        # Then every copper island belongs to the one intended physical net.
        assert len({root(key) for key in parent}) == 1, name


def test_plane_areas_exclude_features_and_meet_requested_ratio(fixture):
    # Given explicit plane-only masks, separate from terminal, trace and via copper.
    for layer in fixture.layers:
        power = {net.name: net for net in layer.nets if net.name in ("VSS", "VDD", "VDDQ")}
        # When measuring only tagged plane pixels.
        areas = {name: int(net.plane_mask.sum()) for name, net in power.items()}
        total = sum(areas.values())
        # Then the requested split holds and planes remain dense next to signal routes.
        assert total > fixture.width * fixture.height * 0.5
        for name, target in (("VSS", 0.5), ("VDDQ", 0.25), ("VDD", 0.25)):
            assert abs(areas[name] / total - target) <= 0.005
            assert not np.any(power[name].plane_mask & ~power[name].mask)
        for terminal in layer.terminals:
            for net in power.values():
                assert not net.plane_mask[terminal.y, terminal.x]
        for via in layer.vias:
            for net in power.values():
                assert not net.plane_mask[via.y, via.x]
        plane = np.logical_or.reduce([net.plane_mask for net in power.values()])
        distance = ndimage.distance_transform_edt(~plane)
        signal = np.logical_or.reduce([net.mask for net in layer.nets if net.name.startswith("DQ")])
        for terminal in layer.terminals:
            yy, xx = np.ogrid[: fixture.height, : fixture.width]
            signal &= (xx - terminal.x) ** 2 + (yy - terminal.y) ** 2 > (terminal.radius + 20) ** 2
        assert np.percentile(distance[signal], 90) <= 20
