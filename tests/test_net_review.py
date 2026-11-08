"""NET hints must describe real copper contacts, not spatial proximity."""

import numpy as np
import pytest

from pkg_re.graph import analyze_graph
from pkg_re.models import Calibration, Candidate, Layer, Marker, Project
from pkg_re.store import Pixels, State


def trace_state(names: tuple[str, str] = ("VSS", "VSS")) -> State:
    layer = Layer(id="layer", name="Trace", width=64, height=40)
    pixels = Pixels.blank(layer)
    pixels.observed[18:21, 5:30] = True
    pixels.observed[18:21, 32:58] = True
    layer.markers = [
        Marker(id=str(x), kind="net", x=x, y=19, net=net, confirmed=True)
        for x, net in ((8, names[0]), (54, names[1]))
        if net
    ]
    layer.candidates = [
        Candidate(
            id="gap", kind="reconnect", bbox=(30, 18, 2, 3), pixels=6, reason="gap", annotation_overlap=False
        )
    ]
    pixels.patches["gap"] = np.ones((3, 2), dtype=bool)
    return State(Project(id="project", name="Test", layers=[layer]), {layer.id: pixels})


@pytest.mark.parametrize(
    "names,expected",
    [(("VSS", "VDD"), "reject"), (("VSS", "VSS"), "accept"), (("", ""), "review"), (("VSS", ""), "accept")],
)
def test_recommendation_uses_contacting_net_identity(names, expected):
    # Given disconnected collinear trace ends with explicit physical seeds.
    state = trace_state(names)
    before = state.pixels["layer"].observed.copy()
    # When
    from pkg_re.net_review import refresh_recommendations

    refresh_recommendations(state, "layer")
    # Then
    assert state.layer("layer").candidates[0].recommendation == expected
    np.testing.assert_array_equal(state.pixels["layer"].observed, before)
    assert not state.pixels["layer"].added.any()


def test_round_void_stays_review_even_in_named_plane():
    # Given a small enclosed clearance on one assigned plane.
    state = trace_state()
    px = state.pixels["layer"]
    px.observed[4:36, 4:60] = True
    px.observed[18:21, 30:33] = False
    state.layer("layer").candidates = [
        Candidate(id="hole", kind="plane_hole_fill", bbox=(30, 18, 3, 3), pixels=9, reason="void")
    ]
    px.patches = {"hole": np.ones((3, 3), dtype=bool)}
    # When
    from pkg_re.net_review import refresh_recommendations

    refresh_recommendations(state, "layer")
    # Then
    assert state.layer("layer").candidates[0].recommendation == "review"


@pytest.mark.parametrize("blocker", ["erased", "protected", "annotation", "via"])
def test_explicit_or_occluded_gap_never_auto_accepts(blocker):
    # Given an otherwise valid small continuity repair.
    state = trace_state()
    if blocker in ("erased", "protected"):
        getattr(state.pixels["layer"], blocker)[19, 30] = True
    elif blocker == "annotation":
        state.layer("layer").candidates[0].annotation_overlap = True
    else:
        state.layer("layer").markers.append(Marker(id="via", kind="via", x=31, y=19, radius=4))
    # When
    from pkg_re.net_review import refresh_recommendations

    refresh_recommendations(state, "layer")
    # Then
    assert state.layer("layer").candidates[0].recommendation == "review"


def test_physical_via_graph_propagates_named_identity_to_other_layer():
    # Given the left trace inherits its identity through a confirmed via.
    state = trace_state(("", "VSS"))
    bottom = state.layer("layer")
    bottom.calibration = Calibration(mm_per_pixel=1)
    top = Layer(id="top", name="Top", width=64, height=40, calibration=Calibration(mm_per_pixel=1))
    top.markers = [
        Marker(id="via", kind="via", x=8, y=19, net="VDD", radius=1, confirmed=True, end_layer_id="layer")
    ]
    top_px = Pixels.blank(top)
    top_px.observed[18:21, 5:12] = True
    state.project.layers.insert(0, top)
    state.pixels[top.id] = top_px
    graph = analyze_graph(state)
    # When
    from pkg_re.net_review import refresh_recommendations

    refresh_recommendations(state, "layer", graph)
    # Then
    candidate = bottom.candidates[0]
    assert candidate.recommendation == "reject"
    assert candidate.hint_nets == ["VDD", "VSS"]


def test_unknown_plane_side_is_not_trace_continuity():
    # Given two planes separated by a narrow clearance, only one identified.
    state = trace_state(("VSS", ""))
    px = state.pixels["layer"]
    px.observed[4:36, 5:30] = True
    px.observed[4:36, 32:58] = True
    # When
    from pkg_re.net_review import refresh_recommendations

    refresh_recommendations(state, "layer")
    # Then
    assert state.layer("layer").candidates[0].recommendation == "review"


def test_thin_enclosed_void_requires_review_despite_same_assigned_net():
    # Given a narrow elongated void with the same assigned copper on all sides.
    state = trace_state()
    px = state.pixels["layer"]
    px.observed[4:36, 4:60] = True
    px.observed[13:25, 30:32] = False
    state.layer("layer").candidates = [
        Candidate(
            id="scratch",
            kind="plane_hole_fill",
            bbox=(30, 13, 2, 12),
            pixels=24,
            reason="void",
            annotation_overlap=False,
        )
    ]
    px.patches = {"scratch": np.ones((12, 2), dtype=bool)}
    # When
    from pkg_re.net_review import refresh_recommendations

    refresh_recommendations(state, "layer")
    # Then
    assert state.layer("layer").candidates[0].recommendation == "review"


def test_existing_conflict_never_authorizes_extra_copper():
    # Given one endpoint already has contradictory confirmed seeds.
    state = trace_state()
    state.layer("layer").markers.append(
        Marker(id="conflict", kind="net", x=10, y=19, net="VDD", confirmed=True)
    )
    # When
    from pkg_re.net_review import refresh_recommendations

    refresh_recommendations(state, "layer")
    # Then
    assert state.layer("layer").candidates[0].recommendation == "review"


def test_clean_bga_clearances_are_never_recommended_for_automatic_fill(tmp_path):
    # Given pristine PNGs ingested normally with only supplied terminal annotations.
    from pkg_re.bga_sample import create_bga_sample
    from pkg_re.models import Analyze
    from pkg_re.net_review import refresh_recommendations
    from pkg_re.operations import analyze_layer
    from pkg_re.store import Store

    store = Store(tmp_path)
    state = store.create("Clean review")
    create_bga_sample(state, store, "clean")
    for layer in state.project.layers:
        analyze_layer(state, store, layer.id, Analyze())
    # When
    graph = analyze_graph(state)
    for layer in state.project.layers:
        refresh_recommendations(state, layer.id, graph)
    # Then
    assert all(c.recommendation != "accept" for layer in state.project.layers for c in layer.candidates)
    assert all(not px.added.any() and not px.erased.any() for px in state.pixels.values())


def test_lime_occlusion_blocks_auto_repair_even_if_explanation_is_translated(tmp_path):
    import io

    from PIL import Image

    from pkg_re.images import add_image
    from pkg_re.models import Analyze
    from pkg_re.net_review import refresh_recommendations
    from pkg_re.operations import analyze_layer
    from pkg_re.store import Store

    store = Store(tmp_path)
    state = store.create("Annotation raster")
    rgb = np.full((40, 64, 3), 20, dtype=np.uint8)
    rgb[18:21, 5:58] = [200, 170, 90]
    rgb[18:21, 30:32] = [80, 255, 80]
    output = io.BytesIO()
    Image.fromarray(rgb).save(output, format="PNG")
    layer = add_image(state, store, output.getvalue(), "Lime-covered trace")
    layer.markers = [Marker(id="known", kind="net", x=8, y=19, net="DQ0", confirmed=True)]
    analyze_layer(state, store, layer.id, Analyze())
    assert layer.candidates
    for candidate in layer.candidates:
        candidate.reason = "스크래치 후보: 설명 번역과 독립된 pixel 근거"
    refresh_recommendations(state, layer.id)
    assert all(c.annotation_overlap is True and c.recommendation == "review" for c in layer.candidates)
