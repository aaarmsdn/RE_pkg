"""Net visualization follows accepted electrical components, never photo color."""

import io

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image

from pkg_re.app import create_app


def net_project(client):
    p = client.post("/api/projects", json={"name": "Color test"}).json()
    rgb = np.full((40, 120, 3), 20, dtype=np.uint8)
    for x in (5, 28, 51, 74, 97):
        rgb[10:30, x : x + 15] = [182, 136, 70]
    out = io.BytesIO()
    Image.fromarray(rgb).save(out, format="PNG")
    p = client.post(
        f"/api/projects/{p['id']}/layers", files={"file": ("nets.png", out.getvalue(), "image/png")}
    ).json()
    lid = p["layers"][0]["id"]
    prefix = f"/api/projects/{p['id']}/layers/{lid}"
    seeds = [
        {"id": net, "kind": "net", "x": x, "y": 20, "net": net, "confirmed": True}
        for net, x in zip(("VSS", "VDD", "VDDQ", "DQ0"), (10, 33, 56, 79), strict=True)
    ]
    client.put(prefix + "/markers", json={"markers": seeds}).raise_for_status()
    p = client.post(prefix + "/analyze", json={"max_gap": 2}).json()
    return p, prefix, seeds


def read_png(response):
    response.raise_for_status()
    with Image.open(io.BytesIO(response.content)) as image:
        return np.array(image)


def test_net_overlay_colors_match_legend_unknown_is_not_assigned(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        p, _, _ = net_project(client)
        layer = p["layers"][0]
        legend = {row["net"]: row for row in layer["net_legend"]}
        assert set(legend) == {"VSS", "VDD", "VDDQ", "DQ0", "UNASSIGNED"}
        assert len({row["color"] for row in legend.values()}) == 5
        pixels = read_png(client.get(layer["net_overlay_url"]))
        for net, x in zip(("VSS", "VDD", "VDDQ", "DQ0", "UNASSIGNED"), (10, 33, 56, 79, 102), strict=True):
            color = legend[net]["color"]
            assert pixels[20, x, :3].tolist() == [int(color[i : i + 2], 16) for i in (1, 3, 5)]
            assert pixels[20, x, 3] > 0
        assert pixels[0, 0, 3] == 0
        assert legend["UNASSIGNED"]["status"] == "unassigned"


def test_highlight_only_changes_opacity_not_identity_or_geometry(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        p, prefix, _ = net_project(client)
        before = read_png(client.get(prefix + "/nets.png"))
        selected = read_png(client.get(prefix + "/nets.png?net=VSS"))
        assert selected[20, 10, 3] > selected[20, 33, 3] > 0
        np.testing.assert_array_equal(before[:, :, :3], selected[:, :, :3])
        after = client.get(f"/api/projects/{p['id']}").json()
        assert after["revision"] == p["revision"] and after["areas"] == p["areas"]
        assert after["layers"][0]["net_legend"] == p["layers"][0]["net_legend"]


def test_conflict_has_own_color_and_cannot_masquerade_as_vss(tmp_path):
    with TestClient(create_app(tmp_path)) as client:
        p, prefix, seeds = net_project(client)
        colors = {r["net"]: r["color"] for r in p["layers"][0]["net_legend"]}
        seeds.append({"id": "short", "kind": "net", "net": "VDD", "x": 12, "y": 20, "confirmed": True})
        p = client.put(prefix + "/markers", json={"markers": seeds}).json()
        conflict = next(r for r in p["layers"][0]["net_legend"] if r["status"] == "conflict")
        assert conflict["color"] not in colors.values()
        assert "VSS" in conflict["net"] and "VDD" in conflict["net"]
