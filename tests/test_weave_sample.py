"""New shuffled examples retain ordinary PNG ingestion and unknown upper NETs."""

import pytest
from fastapi.testclient import TestClient

from pkg_re.app import create_app
from pkg_re.store import Store


@pytest.mark.parametrize(
    "layout,count,profile", [("weave16", 16, "clean"), ("weave32", 32, "diagonal"), ("micro32", 32, "damaged")]
)
def test_weave_creation_keeps_reference_masks_out_of_reconstruction(tmp_path, layout, count, profile):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(
            "/api/projects",
            json={"name": layout, "demo": True, "sample": f"die_{layout}", "damage_profile": profile},
        )
        assert response.status_code == 200
        project = response.json()
        lower, upper = project["layers"]
        dq_names = {m["net"] for m in lower["markers"] if m["kind"] == "ball" and m["net"].startswith("DQ")}
        assert dq_names == {f"DQ{i}" for i in range(count)}
        assert all(not m["net"] for m in upper["markers"])
        assert all(not layer["analyzed"] and not layer["net_legend"] for layer in project["layers"])
        state = Store(tmp_path).load(project["id"])
        assert all(not pixels.accepted().any() for pixels in state.pixels.values())
