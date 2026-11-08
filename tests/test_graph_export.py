"""Electrical graph and physical geometry regression scenarios."""

import io

import numpy as np
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from pkg_re.app import create_app


def upload(client, pid, pixels):
    data = io.BytesIO()
    Image.fromarray(pixels).save(data, format="PNG")
    p = client.post(
        f"/api/projects/{pid}/layers", files={"file": ("test.png", data.getvalue(), "image/png")}
    ).json()
    layer = p["layers"][-1]
    prefix = f"/api/projects/{pid}/layers/{layer['id']}"
    client.post(
        prefix + "/analyze", json={"threshold": 110, "max_gap": 2, "max_hole_area": 40}
    ).raise_for_status()
    client.post(prefix + "/calibration", json={"mm_per_pixel": 0.01}).raise_for_status()
    return layer["id"], prefix


def test_via_reaches_only_declared_layers_and_export_area_matches(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        pid = client.post("/api/projects", json={"name": "Span"}).json()["id"]
        rgb = np.zeros((40, 60, 3), dtype=np.uint8) + 20
        rgb[10:30, 10:50] = [182, 136, 70]
        layers = [upload(client, pid, rgb) for _ in range(3)]
        seed = {
            "id": "source",
            "kind": "via",
            "x": 20,
            "y": 20,
            "net": "VSS",
            "end_layer_id": layers[1][0],
            "confirmed": True,
        }
        client.put(layers[0][1] + "/markers", json={"markers": [seed]}).raise_for_status()
        p = client.get(f"/api/projects/{pid}").json()
        assigned = {r["layer_id"] for r in p["areas"] if r["net"] == "VSS"}
        assert assigned == {layers[0][0], layers[1][0]}
        neutral = client.get(f"/api/projects/{pid}/export/json").json()
        for layer in p["layers"]:
            geometry = neutral["geometry"][layer["id"]]
            polygon_area = sum(poly["area"] for group in geometry["groups"] for poly in group["polygons"])
            expected = sum(row["total_mm2"] for row in p["areas"] if row["layer_id"] == layer["id"])
            assert polygon_area == pytest.approx(expected)


def test_ballmap_does_not_restore_unpopulated_sites(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        pid = client.post("/api/projects", json={"name": "Grid"}).json()["id"]
        lid, prefix = upload(client, pid, np.zeros((60, 90, 3), dtype=np.uint8) + 20)
        p = client.post(
            prefix + "/ballmap",
            json={
                "csv": "row,col,net,populated\n0,0,VSS,1\n0,1,NC,0\n0,2,VDD,1\n",
                "origin": {"x": 15, "y": 20},
                "pitch_px": 25,
                "pitch_mm": 0.5,
                "radius_px": 5,
                "restore_missing": True,
            },
        ).json()
        assert len(p["layers"][0]["markers"]) == 2
        assert {r["net"] for r in p["areas"]} == {"VSS", "VDD"}
        assert all(r["observed_px"] == 0 and r["inferred_px"] > 0 for r in p["areas"])


def test_failed_conflicting_repair_is_not_persisted(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        pid = client.post("/api/projects", json={"name": "Conflict"}).json()["id"]
        rgb = np.zeros((40, 60, 3), dtype=np.uint8) + 20
        rgb[10:30, 5:55] = [182, 136, 70]
        rgb[:, 29:31] = 20
        lid, prefix = upload(client, pid, rgb)
        seeds = [
            {"id": str(x), "kind": "net", "x": x, "y": 20, "net": net, "confirmed": True}
            for x, net in [(10, "VSS"), (45, "VDD")]
        ]
        p = client.put(prefix + "/markers", json={"markers": seeds}).json()
        before = p["revision"]
        candidate = next(c for c in p["layers"][0]["candidates"] if c["kind"] == "reconnect")
        r = client.post(prefix + "/candidate", json={"id": candidate["id"], "decision": "accepted"})
        assert r.status_code == 409
        p = client.get(f"/api/projects/{pid}").json()
        assert p["revision"] == before
        assert {row["net"] for row in p["areas"]} == {"VSS", "VDD"}


def test_zip_preserves_provenance_log(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        pid = client.post("/api/projects", json={"name": "Persistence"}).json()["id"]
        lid, prefix = upload(client, pid, np.zeros((50, 50, 3), dtype=np.uint8) + 20)
        p = client.post(
            prefix + "/stroke", json={"kind": "add", "points": [{"x": 25, "y": 25}], "radius": 5}
        ).json()
        assert any("stroke" in row for row in p["edit_log"])
        blob = client.get(f"/api/projects/{pid}/export/zip").content
        restored = client.post(
            "/api/projects/import", files={"file": ("state.zip", blob, "application/zip")}
        ).json()
        assert restored["edit_log"] == p["edit_log"]
        assert restored["areas"][0]["inferred_px"] == p["areas"][0]["inferred_px"]
