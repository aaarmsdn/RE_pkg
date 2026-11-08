"""Reproducible dense-die PNG benchmark; truth is used only for scoring."""

import hashlib
import importlib.util
import json
from contextlib import contextmanager
from dataclasses import asdict
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from PIL import Image, ImageDraw

from pkg_re import batch_review, operations
from pkg_re.annotations import apply_ballmap
from pkg_re.bga_benchmark import evaluate
from pkg_re.bga_fixture import bga_fixture
from pkg_re.bga_render import render_layer
from pkg_re.bga_sample import ballmap_input, install_annotations
from pkg_re.die_fixture import die_fixture, die_fixture_metadata
from pkg_re.die_render import render_die_layer
from pkg_re.engine import connected_regions
from pkg_re.graph import analyze_graph
from pkg_re.images import add_image
from pkg_re.models import Analyze, AutoReview
from pkg_re.store import Store

ROOT = Path(__file__).resolve().parent.parent


def terminal_pairs(masks, fixture):
    """Score physical connectivity with native-coordinate via contacts, not NET-name union.

    Fixtures share identity registration. Missing contacts remain disconnected, including
    two missing terminals. Intended terminal nets define the evaluation oracle only.
    """
    labels = [connected_regions(mask)[0] for mask in masks]
    parents = {}

    def root(key):
        parents.setdefault(key, key)
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    for via in fixture.layers[0].vias:
        ids = [int(label[via.y, via.x]) for label in labels]
        if all(ids):
            parents[root((1, ids[1]))] = root((0, ids[0]))
    terminals = []
    for index, reference in enumerate(fixture.layers):
        for terminal in reference.terminals:
            rid = int(labels[index][terminal.y, terminal.x])
            terminals.append((terminal, root((index, rid)) if rid else None))
    false_open = false_short = expected_connected = 0
    failures = []
    for (a, ra), (b, rb) in combinations(terminals, 2):
        expected = a.net == b.net
        connected = ra is not None and rb is not None and root(ra) == root(rb)
        expected_connected += expected
        false_open += expected and not connected
        false_short += not expected and connected
        if expected != connected:
            failures.append({"a": a.name, "b": b.name, "error": "open" if expected else "short"})
    return {
        "false_open": false_open,
        "false_short": false_short,
        "expected_connected_pairs": expected_connected,
        "failures": failures,
    }


@contextmanager
def algorithm(version):
    original = operations.propose_repairs, batch_review.refresh_recommendations
    try:
        if version == "baseline":
            for name, filename, target, attribute in (
                ("pkg_re.engine.baseline_repairs", "baseline-repairs.py", operations, "propose_repairs"),
                (
                    "pkg_re.baseline_net_review",
                    "baseline-net_review.py",
                    batch_review,
                    "refresh_recommendations",
                ),
            ):
                spec = importlib.util.spec_from_file_location(
                    name, ROOT / "benchmarks/baseline" / filename
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                setattr(target, attribute, getattr(module, attribute))
        yield
    finally:
        operations.propose_repairs, batch_review.refresh_recommendations = original


def score(state, fixture, stage):
    rows = evaluate(state, fixture, stage)
    graph = analyze_graph(state)
    pairs = terminal_pairs([state.pixels[layer.id].accepted() for layer in state.project.layers], fixture)
    for row, layer, reference in zip(rows, state.project.layers, fixture.layers, strict=True):
        px = state.pixels[layer.id]
        accepted = px.accepted()
        truth = np.logical_or.reduce([net.mask for net in reference.nets])
        row.update(
            {
                "false_copper_px": int((accepted & ~truth).sum()),
                "false_added_copper_px": int((accepted & ~px.observed & ~truth).sum()),
                "missing_copper_recovered_px": int((accepted & ~px.observed & truth).sum()),
                "missing_copper_px": int((truth & ~accepted).sum()),
                "correct_terminals": sum(t["correct"] for t in row["terminals"]),
                "physical_pairs": pairs,
                "automatic_accepted": sum(
                    c.status == "accepted" and c.decision_source == "automatic" for c in layer.candidates
                ),
            }
        )
        for net in row["per_net"]:
            net["false_assigned_px"] = net["assigned_px"] - net["correct_px"]
            net["missing_assigned_px"] = net["truth_px"] - net["correct_px"]
            net["area_error_px"] = net["assigned_px"] - net["truth_px"]
            reference_net = next(n for n in reference.nets if n.name == net["net"])
            route = reference_net.mask & ~reference_net.plane_mask
            region_ids = [
                r.id for r in graph.regions[layer.id] if r.status == "assigned" and r.net == net["net"]
            ]
            assigned = np.isin(graph.labels[layer.id], region_ids)
            net["routing_truth_px"] = int(route.sum())
            net["routing_correct_px"] = int((route & assigned).sum())
            net["routing_missing_px"] = int((route & ~assigned).sum())
    return rows


def run_benchmark(output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="die-benchmark-") as scratch:
        return _run_benchmark(output, Store(Path(scratch)))


def _run_benchmark(output: Path, store: Store) -> Path:
    manifest = {"inputs": [], "layouts": [], "baseline_sources": {}, "current_sources": {}}
    for filename in (
        "pkg_re/engine/repairs.py",
        "pkg_re/engine/continuity.py",
        "pkg_re/die_benchmark.py",
        "pkg_re/net_review.py",
        "pkg_re/die_fixture.py",
        "pkg_re/die_render.py",
        "pkg_re/bga_render.py",
    ):
        manifest["current_sources"][filename] = hashlib.sha256((ROOT / filename).read_bytes()).hexdigest()
    for filename in (
        "baseline-repairs.py",
        "baseline-net_review.py",
        "damage-baseline.json",
        "damage-baseline-replay.json",
        "replay_baseline.py",
    ):
        path = ROOT / "benchmarks/baseline" / filename
        manifest["baseline_sources"][filename] = hashlib.sha256(path.read_bytes()).hexdigest()
    metrics = []
    overview = Image.new("RGB", (900, 650), "white")
    draw = ImageDraw.Draw(overview)
    for col, layout in enumerate(("edge_dense", "center_rows", "center_array")):
        fixture = die_fixture(layout)
        metadata = die_fixture_metadata(fixture, layout)
        metadata["supplied_annotations"] = [
            {
                "terminals": [asdict(t) | ({"net": ""} if index else {}) for t in layer.terminals],
                "vias": [asdict(v) | {"net": ""} for v in layer.vias],
            }
            for index, layer in enumerate(fixture.layers)
        ]
        manifest["layouts"].append(metadata)
        (output / f"{layout}-ballmap.csv").write_text(ballmap_input(fixture).csv + "\n")
        for profile in ("clean", "damaged", "severe"):
            paths = []
            for index, reference in enumerate(fixture.layers):
                rendered = render_die_layer(reference, profile, index)
                path = output / f"{layout}-{profile}-L{index + 1}.png"
                Image.fromarray(rendered.image).save(path)
                paths.append(path)
                manifest["inputs"].append(
                    {
                        "file": path.name,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "events": [asdict(event) for event in rendered.events],
                        "removed_px": int(rendered.removed.sum()),
                        "faded_gap_px": int(rendered.faded_gap.sum()),
                    }
                )
                if profile == "clean" and index == 1:
                    y = min(t.y for t in reference.terminals) - 60
                    crop = Image.fromarray(rendered.image).crop((750, y, 1050, y + 600))
                    overview.paste(crop, (col * 300, 50))
                    draw.text((col * 300 + 4, 3), f"{layout} L2, native 1:1", fill="black")
                    draw.text((col * 300 + 4, 20), f"x=750 y={y}; 300x600 px", fill="black")
                del rendered
            for version in ("baseline", "current"):
                with algorithm(version):
                    state = store.create(f"{layout} {profile} {version}")
                    for path in paths:
                        layer = add_image(state, store, path.read_bytes(), path.stem)
                        assert not state.pixels[layer.id].accepted().any()
                    install_annotations(state, fixture)
                    for layer in state.project.layers:
                        operations.analyze_layer(state, store, layer.id, Analyze())
                    stages = score(state, fixture, "supplied_hints")
                    apply_ballmap(state, state.project.layers[0].id, ballmap_input(fixture, restore=True))
                    stages.extend(score(state, fixture, "explicit_land_restore"))
                    for layer in state.project.layers:
                        batch_review.auto_review(
                            state, layer.id, AutoReview(expected_revision=state.project.revision)
                        )
                    stages.extend(score(state, fixture, "automatic_after_land_restore"))
                    for row in stages:
                        row.update(layout=layout, profile=profile, algorithm=version)
                    metrics.extend(stages)
                    store.save(state)
                    print(
                        f"{layout} {profile} {version}: "
                        f"upper {stages[-1]['correct_terminals']}/22; "
                        f"false added {sum(r['false_added_copper_px'] for r in stages[-2:])}",
                        flush=True,
                    )
                    del state
        del fixture
    overview.save(output / "native-pad-crops.png")
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    path = output / "metrics.json"
    path.write_text(json.dumps(metrics, indent=2) + "\n")
    write_readme(output, metrics)
    original_bga(output, store)
    return path


def original_bga(output, store):
    """Original damaged BGA control: reuse one fixture and exactly the same PNGs."""
    fixture = bga_fixture()
    paths = []
    for index, reference in enumerate(fixture.layers):
        path = output / f"original-bga-damaged-L{index + 1}.png"
        Image.fromarray(render_layer(reference, "damaged", index).image).save(path)
        paths.append(path)
    (output / "original-bga-inputs.json").write_text(
        json.dumps(
            [{"file": path.name, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in paths],
            indent=2,
        )
        + "\n"
    )
    metrics = []
    for version in ("baseline", "current"):
        with algorithm(version):
            state = store.create(f"Original BGA damaged {version}")
            for path in paths:
                layer = add_image(state, store, path.read_bytes(), path.stem)
                assert not state.pixels[layer.id].accepted().any()
            install_annotations(state, fixture)
            for layer in state.project.layers:
                operations.analyze_layer(state, store, layer.id, Analyze())
            rows = score(state, fixture, "supplied_hints")
            apply_ballmap(state, state.project.layers[0].id, ballmap_input(fixture, restore=True))
            rows.extend(score(state, fixture, "explicit_land_restore"))
            for layer in state.project.layers:
                batch_review.auto_review(
                    state, layer.id, AutoReview(expected_revision=state.project.revision)
                )
            rows.extend(score(state, fixture, "automatic_after_land_restore"))
            for row in rows:
                row["algorithm"] = version
            metrics.extend(rows)
            store.save(state)
    (output / "original-bga-metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    with (output / "README.md").open("a") as report:
        report.write(
            "\n## Original damaged BGA control\n\n"
            "|Algorithm|Stage|Upper correct pads|False added px|Recovered px|\n"
            "|---|---|---:|---:|---:|\n"
        )
        for row in metrics:
            if row["layer"] == fixture.layers[1].name:
                report.write(
                    f"|{row['algorithm']}|{row['stage']}|{row['correct_terminals']}/36|"
                    f"{row['false_added_copper_px']}|{row['missing_copper_recovered_px']}|\n"
                )


def write_readme(output, metrics):
    lines = [
        "# Dense die PNG benchmark",
        "",
        "Run: `uv run python -m pkg_re.die_benchmark`",
        "",
        "18 native PNGs: 3 independently routed layouts × clean/damaged/severe × 2 layers. "
        "All runs reopen identical saved PNG bytes with blank initial masks, confirmed lower ballmap, "
        "and unnamed pads/vias. Truth masks and terminal nets are used only in evaluation.",
        "",
        "Baseline files were reconstructed from a captured pre-edit read, not a Git commit. "
        "replay_baseline.py reproduced damage-baseline.json exactly; source/replay SHA256 hashes "
        "are in manifest.json. Dense fixture baseline measurements were captured now, not before editing.",
        "",
        "Native pad width×height 6×12 px, pitch 16 px, fine trace width 3 px. "
        "Center-array includes deliberate 1 px gap stress. native-pad-crops.png is a native-resolution "
        "300×600 crop per layout. Edge-dense lower bank lies outside its crop; "
        "both center-layout banks are visible. Full PNGs retain all banks.",
        "",
        "Physical pair scoring unions only connected copper and contacting vias; equal NET names "
        "alone never connect two islands. Expected connectivity comes from synthetic terminal nets. "
        "This fixture uses identical registration between layers. Scores include lower and upper terminals.",
        "",
        "|Layout|Profile|Algorithm|Stage|Layer|Correct terminals|False added px|Recovered px|Missing px|"
        "Conflict px|Pair opens|Pair shorts|",
        "|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in metrics:
        pair = row["physical_pairs"]
        lines.append(
            f"|{row['layout']}|{row['profile']}|{row['algorithm']}|{row['stage']}|{row['layer']}|"
            f"{row['correct_terminals']}/{len(row['terminals'])}|{row['false_added_copper_px']}|"
            f"{row['missing_copper_recovered_px']}|{row['missing_copper_px']}|{row['conflict_px']}|"
            f"{pair['false_open']}|{pair['false_short']}|"
        )
    lines.extend(
        [
            "",
            "Pair counts are stack-wide, repeated on each layer row. "
            "Per-net assigned/correct/missing/false area and signed area error are in metrics.json, "
            "including thin VDD/VDDQ/VSS routes. Automatic effects must be compared against "
            "explicit_land_restore, "
            "not supplied_hints: known land completion is a separate authorized metadata operation.",
            "",
            "Severe image ambiguity, unresolved missing pads, residual opens, false shorts and lost copper "
            "are retained as failures. Synthetic evidence is not production PCB/netlist or field validation.",
        ]
    )
    lines.extend(
        [
            "",
            "## Isolated current automatic effects",
            "",
            "|Layout|Profile|Upper pads before → after auto|Recovered extra px (both layers)|"
            "False added extra px|Final pair opens / shorts|",
            "|---|---|---:|---:|---:|---:|",
        ]
    )
    for layout in ("edge_dense", "center_rows", "center_array"):
        for profile in ("clean", "damaged", "severe"):
            selected = [
                r
                for r in metrics
                if r["layout"] == layout and r["profile"] == profile and r["algorithm"] == "current"
            ]
            before = [r for r in selected if r["stage"] == "explicit_land_restore"]
            after = [r for r in selected if r["stage"] == "automatic_after_land_restore"]
            recovered = sum(r["missing_copper_recovered_px"] for r in after) - sum(
                r["missing_copper_recovered_px"] for r in before
            )
            false = sum(r["false_added_copper_px"] for r in after) - sum(
                r["false_added_copper_px"] for r in before
            )
            pairs = after[-1]["physical_pairs"]
            lines.append(
                f"|{layout}|{profile}|{before[-1]['correct_terminals']} → "
                f"{after[-1]['correct_terminals']} /22|{recovered}|{false}|"
                f"{pairs['false_open']} / {pairs['false_short']}|"
            )
    (output / "README.md").write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    print(run_benchmark(ROOT / "outputs/die-benchmark"))
