"""Verify a fresh `python -m pkg_re.die_benchmark` run, including local PNGs.

The committed metrics are historical; regenerate before checking current sources.
"""

import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parents[2]
output = Path(__file__).resolve().parent
manifest = json.loads((output / "manifest.json").read_text())
metrics = json.loads((output / "metrics.json").read_text())
assert len(manifest["inputs"]) == 18
assert len(metrics) == 108
for item in manifest["inputs"]:
    assert hashlib.sha256((output / item["file"]).read_bytes()).hexdigest() == item["sha256"]
for name, digest in manifest["current_sources"].items():
    assert hashlib.sha256((root / name).read_bytes()).hexdigest() == digest
assert "pkg_re/engine/continuity.py" in manifest["current_sources"]
assert "pkg_re/die_benchmark.py" in manifest["current_sources"]
for name, digest in manifest["baseline_sources"].items():
    assert hashlib.sha256((root / "benchmarks/baseline" / name).read_bytes()).hexdigest() == digest
assert json.loads((output / "baseline-replay-verification.json").read_text()) == json.loads(
    (root / "benchmarks/baseline/damage-baseline.json").read_text()
)
for row in metrics:
    if row["profile"] == "clean":
        assert row["false_copper_px"] == row["false_added_copper_px"] == 0
        assert row["physical_pairs"]["false_open"] == row["physical_pairs"]["false_short"] == 0
        assert row["correct_terminals"] == len(row["terminals"])
    assert all(
        net["routing_correct_px"] + net["routing_missing_px"] == net["routing_truth_px"]
        for net in row["per_net"]
    )
control = json.loads((output / "original-bga-metrics.json").read_text())
for item in json.loads((output / "original-bga-inputs.json").read_text()):
    assert hashlib.sha256((output / item["file"]).read_bytes()).hexdigest() == item["sha256"]
assert not (output / "projects").exists()
print("PASS: 18 dense PNG hashes; 108 stage/layer rows; all final source hashes; baseline replay equality;")
print(
    "clean geometry/terminal/pair checks; routing accounting; "
    "original BGA input hashes; no durable project dumps."
)
for row in metrics:
    if (
        row["algorithm"] == "current"
        and row["stage"] == "automatic_after_land_restore"
        and row["layer"] == "L2"
    ):
        print(
            row["layout"],
            row["profile"],
            f"upper {row['correct_terminals']}/22",
            "false-added",
            row["false_added_copper_px"],
            "pair opens/shorts",
            row["physical_pairs"]["false_open"],
            row["physical_pairs"]["false_short"],
        )
for row in control:
    if row["algorithm"] == "current" and row["layer"] == "L2":
        print("Original BGA", row["stage"], f"{row['correct_terminals']}/36")
