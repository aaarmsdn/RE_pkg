"""Ballmap uploads must preserve topology and never deserialize objects."""

import io
import struct

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from pkg_re.app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as connection:
        yield connection


def npy_bytes(array, version=None):
    stream = io.BytesIO()
    np.lib.format.write_array(stream, array, version=version, allow_pickle=True)
    return stream.getvalue()


def preview(client, payload):
    return client.post("/api/ballmaps/preview", files={"file": ("ballmap.npy", payload)})


@pytest.mark.parametrize("version", [(1, 0), (2, 0), (3, 0)])
@pytest.mark.parametrize("fortran", [False, True])
def test_unicode_preview_preserves_array_direction_and_reserved_cells(client, version, fortran):
    grid = [["VSS", "DQ0", ""], ["?", "NC", "신호_1"]]
    array = np.array(grid, dtype=">U160", order="F" if fortran else "C")
    response = preview(client, npy_bytes(array, version))
    assert response.status_code == 200, response.text
    assert response.json() == {"grid": grid, "rows": 2, "cols": 3}
    assert client.get("/api/projects").json() == []


@pytest.mark.parametrize("array", [
    np.array([["VSS"]], dtype=object), np.ones((2, 2)),
    np.array([[b"VSS"]]), np.array(["VSS"]), np.empty((0, 2), dtype="U1"),
    np.full((51, 100), "VSS"), np.array([["x" * 161]]),
])
def test_preview_rejects_non_grid_or_unsafe_arrays(client, array):
    assert preview(client, npy_bytes(array)).status_code == 422


@pytest.mark.parametrize("payload", [
    b"not numpy", b"\x93NUMPY\x01\x00" + struct.pack("<H", 20000),
    b"x" * (4 * 1024 * 1024 + 1),
    npy_bytes(np.array([["VSS"]]))[:-1],
    npy_bytes(np.array([["VSS"]])) + b"trailing data",
])
def test_preview_rejects_bad_or_oversized_payload(client, payload):
    assert preview(client, payload).status_code == 422


def test_forged_huge_shape_is_rejected_before_array_allocation(client):
    header = b"{'descr': '<U1', 'fortran_order': False, 'shape': (999999999999, 2)}\n"
    payload = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header
    assert preview(client, payload).status_code == 422


@pytest.mark.parametrize("header", [b"{[]: 1}", b"{'descr': {[]}, 'shape': (1, 1), 'fortran_order': False}"])
def test_malformed_header_container_returns_validation_error(client, header):
    payload = b"\x93NUMPY\x01\x00" + struct.pack("<H", len(header)) + header
    assert preview(client, payload).status_code == 422


@pytest.mark.parametrize("codepoint", [0xD800, 0x110000])
def test_preview_rejects_invalid_unicode_instead_of_failing_json_encoding(client, codepoint):
    payload = npy_bytes(np.array([["x"]], dtype="<U1"))
    assert preview(client, payload[:-4] + struct.pack("<I", codepoint)).status_code == 422


def blank_project(client):
    project = client.post("/api/projects", json={"name": "Ballmap test"}).json()
    image = io.BytesIO()
    Image.new("RGB", (100, 80), (20, 20, 20)).save(image, format="PNG")
    project = client.post(f"/api/projects/{project['id']}/layers",
                          files={"file": ("blank.png", image.getvalue())}).json()
    return project, f"/api/projects/{project['id']}/layers/{project['layers'][0]['id']}"


def placement(**changes):
    return {"grid": [["VSS", ""], ["?", "NC"]], "origin": {"x": 20, "y": 20},
            "pitch_px": 20, "pitch_mm": 0.5, "radius_px": 3,
            "restore_missing": True, **changes}


def test_grid_pitch_and_reserved_sites_survive_reopen_history_and_export(client):
    project, url = blank_project(client)
    response = client.post(url + "/ballmap", json=placement())
    assert response.status_code == 200, response.text
    updated = response.json()
    layer = updated["layers"][0]
    assert layer["ballmap"]["grid"] == [["VSS", ""], ["?", "NC"]]
    assert layer["ballmap"]["pitch_mm"] == 0.5
    assert layer["calibration"]["mm_per_pixel"] == 0.025
    assert [(m["x"], m["y"], m["net"]) for m in layer["markers"]] == [
        (20, 20, "VSS"), (20, 40, ""), (40, 40, "")]
    assert {area["net"] for area in updated["areas"] if area["status"] == "assigned"} == {"VSS"}
    with Image.open(io.BytesIO(client.get(layer["overlay_url"]).content)) as image:
        assert image.getpixel((20, 20))[3] > 0
        assert image.getpixel((40, 20))[3] == 0
        assert image.getpixel((20, 40))[3] > 0 and image.getpixel((40, 40))[3] > 0
    base = f"/api/projects/{project['id']}"
    assert client.get(base).json()["layers"][0]["ballmap"] == layer["ballmap"]
    assert client.post(base + "/undo").json()["layers"][0]["ballmap"] is None
    assert client.post(base + "/redo").json()["layers"][0]["ballmap"] == layer["ballmap"]
    bundle = client.get(base + "/export/zip")
    assert bundle.status_code == 200
    imported = client.post("/api/projects/import", files={"file": ("project.zip", bundle.content)})
    assert imported.status_code == 200, imported.text
    assert imported.json()["layers"][0]["ballmap"] == layer["ballmap"]


@pytest.mark.parametrize("changes", [
    {"grid": [["VSS"], ["DQ0", "VSS"]]}, {"grid": []}, {"grid": [[1]]},
    {"grid": [["x" * 161]]}, {"grid": [["VSS"]], "csv": "row,col,net,populated\n"},
    {"grid": [["VSS"]] * 5001}, {"pitch_mm": 0}, {"origin": {"x": 150, "y": 20}},
])
def test_invalid_apply_is_atomic(client, changes):
    project, url = blank_project(client)
    applied = client.post(url + "/ballmap", json=placement()).json()
    assert client.post(url + "/ballmap", json=placement(**changes)).status_code == 422
    current = client.get(f"/api/projects/{project['id']}").json()
    assert current["revision"] == applied["revision"]
    assert current["layers"][0]["ballmap"] == applied["layers"][0]["ballmap"]


def test_csv_and_npy_grid_assign_same_named_sites_and_pitch(client):
    _, url = blank_project(client)
    fields = placement(grid=[["VSS", "DQ0"], ["VSS", "VDD"]])
    grid = client.post(url + "/ballmap", json=fields)
    assert grid.status_code == 200, grid.text
    fields.pop("grid")
    fields["csv"] = "row,col,net,populated\n0,0,VSS,1\n0,1,DQ0,1\n1,0,VSS,1\n1,1,VDD,1\n"
    csv = client.post(url + "/ballmap", json=fields)
    assert csv.status_code == 200, csv.text
    def sites(response):
        return [(m["x"], m["y"], m["net"]) for m in response.json()["layers"][0]["markers"]]
    assert sites(grid) == sites(csv)
    assert csv.json()["layers"][0]["ballmap"]["pitch_mm"] == 0.5
