"""Dense synthetic geometry is explicit ground truth, not a display-only net map."""

import numpy as np
from scipy import ndimage

from pkg_re.demo import dense_fixture
from pkg_re.engine import connected_regions
from pkg_re.graph import analyze_graph
from pkg_re.images import create_demo
from pkg_re.models import Analyze, Decision
from pkg_re.operations import analyze_layer, decide_candidate
from pkg_re.store import Store


def test_pristine_dense_nets_are_disjoint_connected_and_close():
    # Given each layer's known geometry before deliberately applied damage.
    for index in range(2):
        fixture = dense_fixture(index)
        occupancy = np.zeros(fixture.protected.shape, dtype=np.uint8)
        # When independently inspecting each net and the plane/signal separation.
        for net in fixture.nets:
            occupancy += net.mask
            labels, regions = connected_regions(net.mask)
            # Then each intended net is one actual conductive island.
            assert len(regions) == 1, (index, net.name, len(regions))
            assert labels[net.seed[1], net.seed[0]] > 0
        assert occupancy.max() == 1
        assert len(connected_regions(occupancy > 0)[1]) == 23
        assert not np.any((occupancy > 0) & fixture.protected)
        assert len(fixture.nets) == 23
        planes = np.logical_or.reduce([n.mask for n in fixture.nets[:3]])
        distance = ndimage.distance_transform_edt(~planes)
        for signal in fixture.nets[3:]:
            # Signal routes run alongside plane fingers, not in a remote open field.
            assert 4 <= distance[signal.mask].min() <= 6
            assert np.quantile(distance[signal.mask], 0.75) < 9
        # Real same-plane fingers between buses at the long parallel middle section.
        plane_runs = np.diff(np.pad(planes[180:530, 600].astype(np.int8), (1, 1)))
        starts, ends = np.flatnonzero(plane_runs == 1), np.flatnonzero(plane_runs == -1)
        assert sum(3 <= end - start <= 7 for start, end in zip(starts, ends, strict=True)) >= 12


def test_dense_demo_analysis_assigns_bus_and_planes_without_conflicts(tmp_path):
    # Given an unprocessed new demo project.
    store = Store(tmp_path)
    state = store.create("Dense demo")
    create_demo(state, store)
    assert len(state.project.layers) == 2
    assert all(not layer.analyzed for layer in state.project.layers)
    # When both native layers are analyzed.
    for layer in state.project.layers:
        analyze_layer(state, store, layer.id, Analyze())
    graph = analyze_graph(state)
    # Then all intended labels exist, no unintentional net short was built.
    expected = {"VSS", "VDD", "VDDQ", *(f"DQ{i}" for i in range(20))}
    for layer in state.project.layers:
        rows = [row for row in graph.areas if row.layer_id == layer.id]
        required = expected if layer.id == state.project.layers[0].id else expected - {"DQ6"}
        assert required <= {row.net for row in rows if row.status == "assigned"}
        if layer.id == state.project.layers[1].id:
            assert "DQ6" not in {row.net for row in rows if row.status == "assigned"}
            assert any(row.status == "unassigned" for row in rows)
            assert all(not marker.net for marker in layer.markers if marker.kind == "pad")
        assert not any(row.status == "conflict" for row in rows)
        assert all(c.status == "pending" for c in layer.candidates)
        assert not state.pixels[layer.id].added.any()
    first = state.project.layers[0]
    fixture = dense_fixture(0)
    for damage in (fixture.trace_gap, fixture.plane_hole, fixture.plane_scratch):
        assert any(
            np.any(
                state.pixels[first.id].patches[c.id]
                & damage[c.bbox[1] : c.bbox[1] + c.bbox[3], c.bbox[0] : c.bbox[0] + c.bbox[2]]
            )
            for c in first.candidates
        )
    assert not np.any(state.pixels[first.id].observed & fixture.protected)
    assert (
        len([m for m in first.markers if m.kind == "via" and m.end_layer_id == state.project.layers[1].id])
        == 20
    )


def test_dense_demo_gap_approval_propagates_bottom_ball_net_to_upper_pad(tmp_path):
    # Given DQ6 broken on L1, with unseeded upper pads and explicit interlayer vias.
    store = Store(tmp_path)
    state = store.create("Bottom-up propagation")
    create_demo(state, store)
    for layer in state.project.layers:
        analyze_layer(state, store, layer.id, Analyze())
    lower, upper = state.project.layers
    before = analyze_graph(state)
    assert not any(row.net == "DQ6" and row.layer_id == upper.id for row in before.areas)
    gap = next(c for c in lower.candidates if c.bbox == (620, 306, 2, 2))
    # When the operator accepts precisely the known trace gap, not all clearances.
    decide_candidate(state, lower.id, Decision(id=gap.id, decision="accepted"))
    # Then the lower ball seed propagates through physical copper and the explicit via.
    after = analyze_graph(state)
    assert any(
        row.net == "DQ6" and row.layer_id == upper.id and row.status == "assigned" for row in after.areas
    )
    assert not any(row.status == "conflict" for row in after.areas)
    assert state.pixels[lower.id].added.sum() == 4
    assert all(not marker.net for marker in upper.markers if marker.kind == "pad")
