"""Native material calibration and direction-aware repair regressions."""

import numpy as np

from pkg_re.engine import SegmentationOptions, segment_copper
from pkg_re.models import Analyze


def test_red_chroma_separates_sampled_photo_colors_and_preserves_one_pixel():
    # Rounded patch means from native pcb_L2 ROI: copper plane/trace, yellow dielectric.
    rgb = np.array([[[143, 106, 100], [182, 152, 124], [150, 108, 100], [168, 136, 112]]], dtype=np.uint8)
    mask = segment_copper(rgb, SegmentationOptions(material_mode="red_chroma", chroma_threshold=14))
    assert mask.tolist() == [[True, False, True, False]]
    assert segment_copper(rgb, SegmentationOptions()).all()


def test_diagonal_scratch_review_requires_same_named_flanks():
    from pkg_re.engine import propose_repairs
    from pkg_re.models import Candidate, Layer, Marker, Parameters, Project
    from pkg_re.net_review import refresh_recommendations
    from pkg_re.store import Pixels, State

    layer = Layer(id="L", name="L", width=90, height=90, parameters=Parameters(directional_scratch=True))
    px = Pixels.blank(layer)
    px.observed[5:85, 5:85] = True
    yy, xx = np.indices(px.observed.shape)
    px.observed[np.abs(xx - yy) <= 1] = False
    layer.markers = [
        Marker(id="a", kind="net", x=20, y=40, net="A", confirmed=True),
        Marker(id="b", kind="net", x=40, y=20, net="A", confirmed=True),
    ]
    for i, p in enumerate(
        propose_repairs(px.observed, px.protected, SegmentationOptions(directional_scratch=True))
    ):
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
    assert any(c.recommendation == "accept" for c in layer.candidates)
    layer.parameters.directional_scratch = False
    refresh_recommendations(state, "L")
    assert all(c.recommendation != "accept" for c in layer.candidates)
    layer.parameters.directional_scratch = True
    for candidate in layer.candidates:
        candidate.annotation_overlap = True
    refresh_recommendations(state, "L")
    assert all(c.recommendation != "accept" for c in layer.candidates)
    for candidate in layer.candidates:
        candidate.annotation_overlap = False
    layer.markers[1].net = "B"
    refresh_recommendations(state, "L")
    assert all(c.recommendation != "accept" for c in layer.candidates)


def test_directional_scratch_cannot_cross_protection():
    from pkg_re.engine import propose_repairs

    observed = np.zeros((90, 90), dtype=bool)
    observed[5:85, 5:85] = True
    yy, xx = np.indices(observed.shape)
    observed[np.abs(xx - yy) <= 1] = False
    protected = np.zeros_like(observed)
    protected[45, 45] = True
    proposals = propose_repairs(observed, protected, SegmentationOptions(directional_scratch=True))
    assert not proposals


def test_real_material_settings_reach_image_analysis_and_persist(tmp_path):
    import io

    from PIL import Image

    from pkg_re.images import add_image
    from pkg_re.operations import analyze_layer
    from pkg_re.store import Store

    rgb = np.full((30, 30, 3), [182, 152, 124], dtype=np.uint8)
    rgb[15, 3:27] = [150, 108, 100]
    content = io.BytesIO()
    Image.fromarray(rgb).save(content, format="PNG")
    store = Store(tmp_path)
    state = store.create("Photo")
    layer = add_image(state, store, content.getvalue(), "photo.png")
    analyze_layer(state, store, layer.id, Analyze(material_mode="red_chroma", directional_scratch=True))
    assert state.pixels[layer.id].observed.sum() == 24
    assert layer.parameters.material_mode == "red_chroma"
    assert layer.parameters.directional_scratch
    store.save(state)
    assert store.load(state.project.id).layer(layer.id).parameters.chroma_threshold == 14


def test_opt_in_wider_trace_gap_preserves_collinear_evidence():
    from pkg_re.engine.continuity import trace_continuity

    observed = np.zeros((50, 80), dtype=bool)
    observed[25, 5:75] = True
    observed[25, 38:42] = False
    assert not trace_continuity(observed, (38, 25, 4, 1), 4)
    assert trace_continuity(observed, (38, 25, 4, 1), 4, directional=True)


def test_directional_terminal_guard_uses_patch_not_empty_bounding_box():
    from pkg_re.models import Candidate, Layer, Marker
    from pkg_re.net_review import near_terminal

    patch = np.eye(80, dtype=bool)
    candidate = Candidate(id="c", kind="reconnect", bbox=(5, 5, 80, 80), pixels=80, reason="scratch")
    layer = Layer(id="L", name="L", width=90, height=90)
    layer.markers = [Marker(id="v", kind="via", x=20, y=65, radius=3)]
    assert near_terminal(candidate, layer)
    assert not near_terminal(candidate, layer, patch=patch)
    layer.markers[0].x, layer.markers[0].y = 45, 48
    assert near_terminal(candidate, layer, patch=patch)


def test_directional_band_not_starved_by_compact_void_proposals():
    from pkg_re.engine import propose_repairs

    observed = np.ones((500, 500), dtype=bool)
    for y in range(10, 210, 20):
        for x in range(10, 210, 20):
            observed[y : y + 10, x : x + 10] = False
    for x in range(300, 320):
        observed[x - 1 : x + 2, x] = False
    proposals = propose_repairs(
        observed, np.zeros_like(observed), SegmentationOptions(directional_scratch=True)
    )
    assert len(proposals) == 100
    assert any(p.bbox == (300, 299, 20, 22) for p in proposals)


def test_enclosed_clean_slit_stays_review_in_both_modes():
    from pkg_re.engine import propose_repairs
    from pkg_re.models import Candidate, Layer, Marker, Parameters, Project
    from pkg_re.net_review import refresh_recommendations
    from pkg_re.store import Pixels, State

    for directional in (False, True):
        layer = Layer(
            id="L", name="L", width=80, height=360, parameters=Parameters(directional_scratch=directional)
        )
        px = Pixels.blank(layer)
        px.observed[5:355, 5:75] = True
        px.observed[20:337, 22] = False
        layer.markers = [Marker(id="a", kind="net", x=35, y=30, net="VDD", confirmed=True)]
        for i, p in enumerate(
            propose_repairs(px.observed, px.protected, SegmentationOptions(directional_scratch=directional))
        ):
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
        assert layer.candidates[0].recommendation == "review"
        assert layer.candidates[0].pixels == 317
