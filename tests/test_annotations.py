"""Annotation provenance must not become observed material evidence."""

from pathlib import Path

import numpy as np
import pytest
from PIL import Image
from pydantic import ValidationError

from pkg_re.annotations import annotation_unknown_mask, detect_annotations
from pkg_re.models import Analyze, Detect, Layer, Marker
from pkg_re.operations import analyze_layer
from pkg_re.store import Pixels, State, Store


def source_state(tmp_path: Path) -> tuple[State, Store]:
    store = Store(tmp_path)
    state = store.create("Annotation evidence")
    layer = Layer(id="a" * 32, name="a" * 32, width=60, height=50)
    state.project.layers.append(layer)
    state.pixels[layer.id] = Pixels.blank(layer)
    image = np.full((50, 60, 3), (182, 136, 70), dtype=np.uint8)
    image[14:18, 12:20] = 255
    image[30:36, 30:36] = (100, 255, 10)
    image[32:34, 32:34] = 0
    Image.fromarray(image).save(store.folder(state.project.id) / ("a" * 32 + ".png"))
    return state, store


def test_ocr_bbox_and_confidence_remain_at_source_after_ball_snap(tmp_path, monkeypatch):
    # Given OCR on an offset ROI and an existing nearby ball center.
    state, store = source_state(tmp_path)
    layer = state.layer("a" * 32)
    layer.roi = (10, 10, 30, 30)
    layer.markers = [Marker(id="ball", kind="ball", x=24, y=24, radius=5)]
    monkeypatch.setattr("pkg_re.annotations.shutil.which", lambda _: "/test/tesseract")
    monkeypatch.setattr(
        "pkg_re.annotations.pytesseract.image_to_data",
        lambda *args, **kwargs: "left\ttop\twidth\theight\tconf\ttext\n2\t4\t8\t4\t87.5\tVDD\n",
    )
    # When
    detect_annotations(state, store, "a" * 32, Detect(ocr=True, green_markers=False))
    # Then
    marker = next(m for m in layer.markers if m.source == "ocr")
    assert (marker.x, marker.y) == (24, 24)
    assert marker.bbox == (12, 14, 8, 4)
    assert marker.confidence == 87.5
    assert marker.net == "VDD" and not marker.confirmed
    store.save(state)
    persisted = next(m for m in store.load(state.project.id).layer("a" * 32).markers if m.source == "ocr")
    assert persisted.bbox == marker.bbox and persisted.confidence == 87.5


def test_annotations_are_unknown_on_reanalysis_without_erasing_approved_geometry(tmp_path):
    # Given prior analysis and approved restoration under an OCR-covered pixel.
    state, store = source_state(tmp_path)
    layer = state.layer("a" * 32)
    detect_annotations(state, store, "a" * 32, Detect(ocr=False, green_markers=True))
    layer.markers.append(
        Marker(id="text", kind="net", x=24, y=24, source="ocr", bbox=(12, 14, 8, 4), confidence=80)
    )
    pixels = state.pixels["a" * 32]
    pixels.observed[:] = True
    pixels.added[15, 15] = True
    pixels.added[32, 32] = True
    before_added = pixels.added.copy()
    # When
    analyze_layer(state, store, "a" * 32, Analyze())
    # Then: bright text, lime ink and black dot all remain unknown, never protected.
    assert not pixels.observed[14:18, 12:20].any()
    assert not pixels.observed[30:36, 30:36].any()
    assert pixels.observed[24, 24]
    assert not pixels.protected.any()
    np.testing.assert_array_equal(pixels.added, before_added)
    assert pixels.accepted()[15, 15] and pixels.accepted()[32, 32]
    assert all(candidate.status == "pending" for candidate in layer.candidates)


def test_ocr_bbox_exclusion_uses_roi_offset_and_clips_to_analysis(tmp_path):
    # Given a bbox crossing the analysis ROI edge.
    state, store = source_state(tmp_path)
    state.layer("a" * 32).markers = [
        Marker(id="text", kind="net", x=24, y=24, source="ocr", bbox=(12, 14, 8, 4))
    ]
    # When
    analyze_layer(state, store, "a" * 32, Analyze(roi=(15, 15, 10, 10)))
    # Then
    observed = state.pixels["a" * 32].observed
    assert not observed[15:18, 15:20].any()
    assert observed[18:25, 15:25].all()
    assert not observed[:15].any()


@pytest.mark.parametrize("metadata", [{"bbox": (1, 1, -1, 2)}, {"confidence": 101}])
def test_marker_rejects_invalid_annotation_metadata(metadata):
    # Given invalid imported/request annotation data.
    # When / Then
    with pytest.raises(ValidationError):
        Marker(id="text", kind="net", x=1, y=1, **metadata)


def test_black_center_of_detected_lime_shape_is_unknown(tmp_path):
    # Given a lime indicator with a black painted center.
    state, store = source_state(tmp_path)
    detect_annotations(state, store, "a" * 32, Detect(ocr=False, green_markers=True))
    with Image.open(store.folder(state.project.id) / ("a" * 32 + ".png")) as source:
        rgb = np.array(source)
    # When
    unknown = annotation_unknown_mask(rgb, state.layer("a" * 32).markers, (0, 0))
    # Then
    assert unknown[30:36, 30:36].all()
    assert not unknown[25, 25]


@pytest.mark.parametrize(
    "replacement",
    [
        {"csv": "row,col,net,populated\n0,0,VDD,0\n"},
        {"origin": {"x": 40, "y": 25}, "radius_px": 2},
        {"restore_missing": False},
    ],
)
def test_reapplying_grid_replaces_generated_disks_preserving_manual_add(tmp_path, replacement):
    # Given one restored grid disk and independent manual evidence, including overlap.
    from pkg_re.annotations import apply_ballmap
    from pkg_re.models import Ballmap

    state, _ = source_state(tmp_path)
    lid = "a" * 32
    pixels = state.pixels[lid]
    pixels.added[20, 20] = True
    pixels.added[5, 5] = True
    original_manual = pixels.added.copy()
    data = {
        "csv": "row,col,net,populated\n0,0,VDD,1\n",
        "origin": {"x": 20, "y": 20},
        "pitch_px": 10,
        "pitch_mm": 1,
        "radius_px": 4,
        "restore_missing": True,
    }
    apply_ballmap(state, lid, Ballmap(**data))
    assert pixels.accepted()[20, 23]
    # When
    apply_ballmap(state, lid, Ballmap(**{**data, **replacement}))
    # Then
    assert not pixels.accepted()[20, 23]
    np.testing.assert_array_equal(pixels.added, original_manual)
    assert pixels.accepted()[20, 20] and pixels.accepted()[5, 5]
    if "origin" in replacement:
        assert pixels.accepted()[25, 40]
        assert not pixels.accepted()[25, 43]


def test_invalid_grid_scale_rejected_without_corrupting_project_or_undo(tmp_path):
    # Given a persisted valid grid transaction, with history available.
    from fastapi.testclient import TestClient

    from pkg_re.app import create_app

    state, store = source_state(tmp_path)
    store.save(state)
    pid, lid = state.project.id, "a" * 32
    data = {
        "csv": "row,col,net,populated\n0,0,VDD,1\n",
        "origin": {"x": 20, "y": 20},
        "pitch_px": 10,
        "pitch_mm": 1,
        "radius_px": 4,
        "restore_missing": True,
    }
    with TestClient(create_app(tmp_path), raise_server_exceptions=False) as client:
        prefix = f"/api/projects/{pid}"
        valid = client.post(f"{prefix}/layers/{lid}/ballmap", json=data)
        assert valid.status_code == 200
        revision = valid.json()["revision"]
        # When an individually valid pitch pair derives an out-of-range scale.
        rejected = client.post(f"{prefix}/layers/{lid}/ballmap", json={**data, "pitch_px": 0.001})
        # Then no invalid calibration reaches disk or undo state.
        assert rejected.status_code == 422
        reopened = client.get(prefix)
        assert reopened.status_code == 200
        assert reopened.json()["revision"] == revision
        assert reopened.json()["layers"][0]["calibration"]["mm_per_pixel"] == 0.1
        assert client.post(f"{prefix}/undo").status_code == 200
        assert client.get(prefix).status_code == 200


def test_replacement_grid_respects_protection_and_explicit_erase(tmp_path):
    # Given missing copper with protected and explicitly erased pixels.
    from pkg_re.annotations import apply_ballmap
    from pkg_re.models import Ballmap

    state, _ = source_state(tmp_path)
    lid = "a" * 32
    pixels = state.pixels[lid]
    pixels.protected[20, 20] = True
    pixels.erased[20, 21] = True
    # When
    apply_ballmap(
        state,
        lid,
        Ballmap(
            csv="row,col,net,populated\n0,0,VDD,1\n",
            origin={"x": 20, "y": 20},
            pitch_px=10,
            pitch_mm=1,
            radius_px=4,
            restore_missing=True,
        ),
    )
    # Then
    assert pixels.grid_added is not None
    assert not pixels.grid_added[20, 20] and not pixels.grid_added[20, 21]
    assert pixels.grid_added[20, 22]


@pytest.mark.parametrize("raw_confidence, expected_calls", [(0, 2), (24, 2), (90, 1)])
def test_bright_text_fallback_only_after_raw_ocr_has_no_usable_tokens(
    tmp_path, monkeypatch, raw_confidence, expected_calls
):
    # Given native ROI OCR with empty/weak raw output or already usable raw text.
    from unittest.mock import Mock

    state, _store = source_state(tmp_path)
    layer = state.layer("a" * 32)
    layer.roi = (10, 10, 30, 30)
    layer.markers = [Marker(id="ball", kind="ball", x=24, y=24, radius=5)]
    header = "left\ttop\twidth\theight\tconf\ttext\n"
    raw = header if raw_confidence == 0 else header + f"2\t4\t8\t4\t{raw_confidence}\tVDD\n"
    ocr = Mock(side_effect=[raw, header + "2\t4\t8\t4\t88\tVSS\n"])
    monkeypatch.setattr("pkg_re.annotations.shutil.which", lambda _: "/test/tesseract")
    monkeypatch.setattr("pkg_re.annotations.pytesseract.image_to_data", ocr)
    # When
    detect_annotations(state, _store, "a" * 32, Detect(ocr=True, green_markers=False))
    # Then valid raw text wins; fallback keeps coordinates and stays unconfirmed.
    marker = next(m for m in layer.markers if m.source == "ocr")
    assert marker.net == ("VDD" if expected_calls == 1 else "VSS")
    assert marker.bbox == (12, 14, 8, 4)
    assert (marker.x, marker.y) == (24, 24) and not marker.confirmed
    assert ocr.call_count == expected_calls
    assert ocr.call_args_list[0].args[0].shape == (30, 30, 3)
    if expected_calls == 2:
        binary = ocr.call_args_list[1].args[0]
        assert binary.shape == (30, 30)
        assert binary[4:8, 2:10].max() == 0
        assert binary[0, 0] == 255
