"""Analysis explains optical saturation separately from missing net evidence."""

import io
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from pkg_re.graph import analyze_graph
from pkg_re.images import add_image
from pkg_re.models import Analyze, Layer, Marker, Project
from pkg_re.operations import analyze_layer
from pkg_re.store import Pixels, State, Store


@pytest.mark.parametrize("bright_rows,warn", [(18, False), (19, True)])
def test_coverage_warning_uses_native_roi_observation_fraction(
    tmp_path: Path, bright_rows: int, warn: bool
) -> None:
    rgb = np.full((40, 40, 3), 20, dtype=np.uint8)
    # Light dielectric can score as copper; the diagnostic must flag ambiguity.
    rgb[10 : 10 + bright_rows, 10:30] = (180, 160, 140)
    payload = io.BytesIO()
    Image.fromarray(rgb).save(payload, format="PNG")
    store = Store(tmp_path)
    state = store.create("Optical ambiguity")
    layer = add_image(state, store, payload.getvalue(), "Photo")
    state.pixels[layer.id].added[10:30, 10:30] = True

    analyze_layer(state, store, layer.id, Analyze(roi=(10, 10, 20, 20)))

    assert any("bright background or merged regions" in item for item in layer.warnings) is warn
    assert int(state.pixels[layer.id].observed.sum()) == bright_rows * 20
    assert all(row.status == "unassigned" for row in analyze_graph(state).areas)


@pytest.mark.parametrize(
    "marker,warn",
    [
        (Marker(id="seed", kind="net", x=4, y=4, net=" ", confirmed=True), True),
        (Marker(id="seed", kind="net", x=4, y=4, net="VSS", confirmed=False), True),
        (Marker(id="seed", kind="net", x=4, y=4, net="VSS", confirmed=True), False),
    ],
)
def test_missing_seed_warning_counts_confirmed_named_markers_across_stack(
    tmp_path: Path, marker: Marker, warn: bool
) -> None:
    layers = [Layer(id=str(i), name=f"L{i}", width=10, height=10) for i in range(2)]
    layers[1].markers = [marker]
    state = State(
        Project(id="0" * 32, name="Seed evidence", layers=layers),
        {layer.id: Pixels.blank(layer) for layer in layers},
    )
    store = Store(tmp_path)
    store.folder(state.project.id).mkdir()
    Image.new("RGB", (10, 10), (40, 40, 40)).save(store.folder(state.project.id) / "0.png")

    analyze_layer(state, store, "0", Analyze())

    assert any("No confirmed named net seeds" in item for item in layers[0].warnings) is warn
