"""Dense die examples use ordinary image input and unnamed upper terminals."""

import pytest
from fastapi.testclient import TestClient

from pkg_re.app import create_app
from pkg_re.models import CreateProject
from pkg_re.store import Store


@pytest.mark.parametrize("layout", ["edge_dense", "center_rows", "center_array"])
def test_dense_die_samples_create_two_unanalyzed_png_layers(tmp_path, layout):
    with TestClient(create_app(tmp_path)) as client:
        response = client.post(
            "/api/projects",
            json={
                "name": "Dense die test",
                "demo": True,
                "sample": f"die_{layout}",
                "damage_profile": "damaged",
            },
        )
        assert response.status_code == 200
        result = response.json()
        assert len(result["layers"]) == 2
        assert all(not item["analyzed"] and not item["net_legend"] for item in result["layers"])
        lower, upper = result["layers"]
        assert sum(m["kind"] == "ball" for m in lower["markers"]) == 32
        assert len(upper["markers"]) >= 22 and all(not m["net"] for m in upper["markers"])
        state = Store(tmp_path).load(result["id"])
        assert all(not px.accepted().any() for px in state.pixels.values())
        assert any("6" in warning and "12" in warning for warning in result["warnings"])


def test_dense_damage_profile_validation_keeps_old_create_compatible():
    assert CreateProject(demo=True).sample == "dense"
    with pytest.raises(ValueError):
        CreateProject.model_validate(
            {"demo": True, "sample": "die_center_rows", "damage_profile": "invented"}
        )
