"""Exercise a public photograph through ordinary upload, analysis and export APIs."""

import hashlib
import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final

import numpy as np
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw

from pkg_re.app import create_app
from pkg_re.store import Store

ROOT: Final = Path(__file__).resolve().parent.parent
ROI: Final = (1800, 1000, 1200, 1200)
SAMPLES: Final = {
    "copper_plane": (750, 450, 60, 60),
    "copper_trace": (500, 155, 60, 7),
    "dielectric": (750, 280, 35, 20),
    "clearance": (500, 135, 60, 8),
}


def run_benchmark(source: Path, output: Path) -> Path:
    """Evaluate selected visible material patches; never infer real NET truth."""
    output.mkdir(parents=True, exist_ok=True)
    data = source.read_bytes()
    with Image.open(io.BytesIO(data)) as original:
        width, height = original.size
        x, y, w, h = ROI
        crop = original.convert("RGB").crop((x, y, x + w, y + h))
    report = {
        "source_file": source.name,
        "source_sha256": hashlib.sha256(data).hexdigest(),
        "source_size": [width, height],
        "roi": ROI,
        "patches": SAMPLES,
        "patch_selection": "Human-selected visible copper/dielectric interiors, not a full pixel oracle.",
        "modes": [],
        "source_hashes": {
            str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in sorted((ROOT / "pkg_re").rglob("*.py"))
        },
        "net_accuracy": None,
        "net_accuracy_reason": "No groundtruth netlist; PHOTO_PLANE_A is a demonstration user label.",
    }
    comparison = Image.new("RGB", (1200, 440), "white")
    thumb = crop.copy()
    thumb.thumbnail((400, 400))
    comparison.paste(thumb, (0, 40))
    ImageDraw.Draw(comparison).text((8, 8), "Actual PCB L2 native ROI (reduced)", fill="black")
    with TemporaryDirectory(prefix="real-photo-benchmark-") as folder:
        storage = Path(folder)
        with TestClient(create_app(storage)) as client:
            response = client.post("/api/projects", json={"name": "Public photo API verification"})
            response.raise_for_status()
            pid = response.json()["id"]
            response = client.post(
                f"/api/projects/{pid}/layers", files={"file": (source.name, data, "image/jpeg")}
            )
            response.raise_for_status()
            lid = response.json()["layers"][0]["id"]
            prefix = f"/api/projects/{pid}/layers/{lid}"
            oversized = client.post(prefix + "/analyze", json={})
            assert oversized.status_code == 422
            report["full_image_roi_guard_status"] = oversized.status_code
            for index, mode in enumerate(("legacy", "red_chroma")):
                response = client.post(
                    prefix + "/analyze",
                    json={"roi": ROI, "material_mode": mode, "chroma_threshold": 14},
                )
                response.raise_for_status()
                assert not any(area["status"] == "assigned" for area in response.json()["areas"])
                state = Store(storage).load(pid)
                observed = state.pixels[lid].observed[y : y + h, x : x + w]
                selected = {
                    name: float(observed[sy : sy + sh, sx : sx + sw].mean())
                    for name, (sx, sy, sw, sh) in SAMPLES.items()
                }
                report["modes"].append(
                    {"mode": mode, "coverage": float(observed.mean()), "selected_fraction": selected}
                )
                preview = Image.fromarray(observed.astype(np.uint8) * 255).convert("RGB")
                preview.thumbnail((400, 400))
                comparison.paste(preview, ((index + 1) * 400, 40))
                ImageDraw.Draw(comparison).text(((index + 1) * 400 + 8, 8), mode, fill="black")
            response = client.put(
                prefix + "/markers",
                json={
                    "markers": [
                        {
                            "id": "example-label",
                            "kind": "net",
                            "x": 2580,
                            "y": 1480,
                            "net": "PHOTO_PLANE_A",
                            "confirmed": True,
                        }
                    ]
                },
            )
            response.raise_for_status()
            assigned = [row for row in response.json()["areas"] if row["net"] == "PHOTO_PLANE_A"]
            assert assigned and assigned[0]["status"] == "assigned"
            report["demonstration_seed"] = {"native_xy": [2580, 1480], "assigned_areas": assigned}
            exported = client.get(f"/api/projects/{pid}/export/csv")
            exported.raise_for_status()
            assert "PHOTO_PLANE_A" in exported.text
            bundle = client.get(f"/api/projects/{pid}/export/zip")
            bundle.raise_for_status()
            restored = client.post(
                "/api/projects/import",
                files={"file": ("public-photo.zip", bundle.content, "application/zip")},
            )
            restored.raise_for_status()
            assert restored.json()["layers"][0]["parameters"]["material_mode"] == "red_chroma"
            assert any(row["net"] == "PHOTO_PLANE_A" for row in restored.json()["areas"])
            report["csv_export_and_zip_roundtrip"] = "PASS"
    comparison.save(output / "material-comparison.png")
    destination = output / "metrics.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(f"Real photo upload/ROI/material/label/CSV/ZIP: PASS. {destination}")
    return destination


if __name__ == "__main__":
    run_benchmark(ROOT / "references/pcb_L2.jpg", ROOT / "outputs/real-photo-benchmark")
