"""Observable API contracts for the local workbench."""

import io
import zipfile

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from pkg_re.app import create_app


@pytest.fixture
def client(tmp_path):
    with TestClient(create_app(tmp_path)) as connection:
        yield connection


def image_bytes():
    rgb = np.zeros((80, 100, 3), dtype=np.uint8) + 20
    rgb[10:60, 10:90] = [182, 136, 70]
    rgb[30:35, 35:40] = 20
    out = io.BytesIO()
    Image.fromarray(rgb).save(out, format="PNG")
    return out.getvalue()


def setup_layer(client):
    p = client.post("/api/projects", json={"name": "Test", "demo": False}).json()
    p = client.post(
        f"/api/projects/{p['id']}/layers", files={"file": ("sample.png", image_bytes(), "image/png")}
    ).json()
    lid = p["layers"][0]["id"]
    prefix = f"/api/projects/{p['id']}/layers/{lid}"
    p = client.post(
        prefix + "/analyze", json={"threshold": 110, "max_gap": 3, "max_hole_area": 100, "roi": None}
    ).json()
    return p, prefix


def test_unknown_scale_does_not_fabricate_mm2(client):
    # Given a copper image without a calibration.
    p, _ = setup_layer(client)
    # When the accepted area is queried.
    rows = p["areas"]
    # Then native pixels are counted, but physical area remains unknown.
    assert sum(r["total_px"] for r in rows) > 3000
    assert all(r["total_mm2"] is None for r in rows)


def test_repair_adds_area_only_after_approval_and_undo_restores(client):
    p, prefix = setup_layer(client)
    before = sum(r["total_px"] for r in p["areas"])
    candidate = next(c for c in p["layers"][0]["candidates"] if c["kind"] == "plane_hole_fill")
    changed = client.post(prefix + "/candidate", json={"id": candidate["id"], "decision": "accepted"})
    assert changed.status_code == 200
    assert sum(r["total_px"] for r in changed.json()["areas"]) > before
    undone = client.post(f"/api/projects/{p['id']}/undo").json()
    assert sum(r["total_px"] for r in undone["areas"]) == before


def test_protected_void_survives_brush_and_reanalysis(client):
    p, prefix = setup_layer(client)
    brush = {"points": [{"x": 37, "y": 32}], "radius": 4}
    client.post(prefix + "/stroke", json={**brush, "kind": "protect"}).raise_for_status()
    client.post(prefix + "/stroke", json={**brush, "kind": "add"}).raise_for_status()
    p = client.post(
        prefix + "/analyze", json={"threshold": 110, "max_gap": 3, "max_hole_area": 100, "roi": None}
    ).json()
    mask = client.get(p["layers"][0]["overlay_url"]).content
    with Image.open(io.BytesIO(mask)) as im:
        assert im.getpixel((37, 32))[3] == 0


def test_different_net_seeds_produce_conflict(client):
    p, prefix = setup_layer(client)
    markers = [
        {
            "id": str(i),
            "kind": "net",
            "x": x,
            "y": 20,
            "net": net,
            "radius": 2,
            "end_layer_id": None,
            "source": "manual",
            "confirmed": True,
        }
        for i, x, net in [(1, 20, "VSS"), (2, 70, "VDD")]
    ]
    p = client.put(prefix + "/markers", json={"markers": markers}).json()
    assert any(r["status"] == "conflict" for r in p["areas"])


def test_calibration_area_and_zip_roundtrip(client):
    p, prefix = setup_layer(client)
    p = client.post(
        prefix + "/calibration",
        json={"mm_per_pixel": 0.01, "rotation_deg": 0, "mirror_x": False, "offset_x_mm": 0, "offset_y_mm": 0},
    ).json()
    row = p["areas"][0]
    assert row["total_mm2"] == pytest.approx(row["total_px"] * 0.0001)
    bundle = client.get(f"/api/projects/{p['id']}/export/zip")
    assert bundle.status_code == 200
    restored = client.post(
        "/api/projects/import", files={"file": ("project.zip", bundle.content, "application/zip")}
    )
    assert restored.status_code == 200
    assert restored.json()["areas"][0]["total_px"] == row["total_px"]


def test_rejects_zip_traversal_and_cross_origin_mutation(client):
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as bundle:
        bundle.writestr("../outside", "bad")
    r = client.post("/api/projects/import", files={"file": ("bad.zip", out.getvalue(), "application/zip")})
    assert r.status_code == 422
    r = client.post(
        "/api/projects", json={"name": "bad", "demo": False}, headers={"Origin": "https://untrusted.example"}
    )
    assert r.status_code == 403


def test_demo_has_two_layers_with_explicit_synthetic_warning(client):
    p = client.post("/api/projects", json={"name": "Demo", "demo": True}).json()
    assert len(p["layers"]) == 2
    assert p["simulation_ready"] is False
    assert p["warnings"]
