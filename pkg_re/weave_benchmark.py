"""Current reconstruction measured from saved woven-package PNG inputs."""

import csv
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Final, TypedDict

from PIL import Image, ImageDraw

from pkg_re import batch_review, operations
from pkg_re.annotations import apply_ballmap
from pkg_re.bga_benchmark import LayerMetric
from pkg_re.bga_fixture import BgaFixture
from pkg_re.bga_render import Profile
from pkg_re.bga_sample import ballmap_input, install_annotations
from pkg_re.die_benchmark import score
from pkg_re.images import add_image
from pkg_re.models import Analyze, AutoReview
from pkg_re.store import Store
from pkg_re.weave_fixture import WeaveLayout, weave_fixture, weave_metadata
from pkg_re.weave_render import render_weave_layer

ROOT: Final = Path(__file__).resolve().parent.parent
LAYOUTS: Final[tuple[WeaveLayout, ...]] = ("weave16", "weave32", "micro32")
PROFILES: Final[tuple[Profile, ...]] = ("clean", "damaged", "severe", "diagonal")


class PairMetric(TypedDict):
    false_open: int
    false_short: int
    expected_connected_pairs: int


class Metric(LayerMetric):
    layout: WeaveLayout
    correct_terminals: int
    false_added_copper_px: int
    missing_copper_px: int
    physical_pairs: PairMetric


def clean_errors(rows: list[Metric]) -> list[str]:
    """Return every clean-case failure; never relax criteria to fit a fixture."""
    failures = []
    for row in rows:
        if row["profile"] != "clean":
            continue
        checks = {
            "incorrect_terminals": len(row["terminals"]) - row["correct_terminals"],
            "false_open": row["physical_pairs"]["false_open"],
            "false_short": row["physical_pairs"]["false_short"],
            "false_added_copper_px": row["false_added_copper_px"],
            "false_copper_px": row["false_copper_px"],
            "missing_copper_px": row["missing_copper_px"],
            "conflict_px": row["conflict_px"],
        }
        failures.extend(
            f"{row['layout']}/{row['stage']}/{row['layer']}: {key}={value}"
            for key, value in checks.items()
            if value
        )
    return failures


def write_readme(output: Path, metrics: list[Metric]) -> None:
    """Put final stack metrics first; retain all stage and per-NET data in JSON."""
    lines = [
        "# Plane-dominant package saved-PNG benchmark",
        "",
        "|Layout|Profile|Upper correct|Pair opens|Pair shorts|False added px|Missing copper px|",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    final = [r for r in metrics if r["stage"] == "automatic_after_land_restore"]
    for lower, upper in zip(final[::2], final[1::2], strict=True):
        pair = upper["physical_pairs"]
        lines.append(
            f"|{upper['layout']}|{upper['profile']}|"
            f"{upper['correct_terminals']}/{len(upper['terminals'])}|"
            f"{pair['false_open']}|{pair['false_short']}|"
            f"{lower['false_added_copper_px'] + upper['false_added_copper_px']}|"
            f"{lower['missing_copper_px'] + upper['missing_copper_px']}|"
        )
    failures = clean_errors(metrics)
    lines.extend(
        [
            "",
            f"Clean-case gate: {'FAIL' if failures else 'PASS'}.",
            "",
            "Run: `uv run python -m pkg_re.weave_benchmark`.",
            "",
            "24 PNG inputs: 3 layouts × clean/damaged/severe/diagonal × 2 layers. Every case reopens the "
            "saved PNG bytes through ordinary ingestion with empty observed/inferred/protected masks. "
            "Only supplied lower ball names and unnamed upper contacts/vias enter reconstruction. "
            "Source/input SHA256 and actual supplied annotations are in manifest.json. "
            "Geometry, damage events and NET mapping are evaluation-only in evaluation-oracle.json "
            "and *-evaluation-mapping.csv; none is loaded by reconstruction.",
            "",
            "Table values are final, after explicit ball-land restoration and automatic review. "
            "Copper counts sum both layers. Physical pair counts are stack-wide, using connected "
            "copper and contacting vias; matching NET names cannot join separate islands. "
            "metrics.json retains supplied_hints, explicit_land_restore and "
            "automatic_after_land_restore stages plus dynamic per-NET area and routing metrics. "
            "Directional scratch proposals are enabled for every profile; actual changes still "
            "require the existing NET, contact and protection checks. "
            "Correct terminal names do not establish complete copper recovery. False added counts only "
            "inferred false copper; false_copper_px in metrics.json also includes observed "
            "false copper from blur.",
            "",
            "native-pad-crops.png contains unscaled crops of the actual saved L2 PNGs, all four "
            "profiles. Crop boxes are recorded in manifest.json. full-layer-overview.png is a "
            "labelled reduced overview of the clean L1/L2 images; original PNGs retain native detail. "
            "Native pad dimensions, pitch, resolution, measured plane coverage and its denominator "
            "are recorded per layout in evaluation-oracle.json. "
            "Temporary projects are discarded; this output contains no project dumps.",
        ]
    )
    if failures:
        lines.extend(["", "Clean failures:", *[f"- {failure}" for failure in failures]])
    (output / "README.md").write_text("\n".join(lines) + "\n")


def run_benchmark(output: Path) -> Path:
    """Render, reopen and evaluate current code, retaining artifacts before any gate failure."""
    output.mkdir(parents=True, exist_ok=True)
    manifest = {"inputs": [], "supplied_annotations": [], "native_crops": [], "sources": {}}
    for path in sorted((ROOT / "pkg_re").rglob("*.py")):
        manifest["sources"][str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    oracle = {"layouts": [], "damage_events": []}
    metrics: list[Metric] = []
    crops = Image.new("RGB", (960, 480 * len(PROFILES)), "white")
    overview = Image.new("RGB", (1080, 780), "white")
    for column, layout in enumerate(LAYOUTS):
        fixture = weave_fixture(layout)
        oracle["layouts"].append(
            weave_metadata(fixture, layout)
            | {
                "image_width_px": fixture.width,
                "image_height_px": fixture.height,
                "mm_per_pixel": fixture.mm_per_pixel,
            }
        )
        _write_mapping(output / f"{layout}-evaluation-mapping.csv", fixture)
        (output / f"{layout}-ballmap.csv").write_text(ballmap_input(fixture).csv + "\n")
        pads = fixture.layers[1].terminals
        center_x = (min(t.x for t in pads) + max(t.x for t in pads)) // 2
        center_y = (min(t.y for t in pads) + max(t.y for t in pads)) // 2
        crop_box = (center_x - 160, center_y - 220, center_x + 160, center_y + 220)
        for row, profile in enumerate(PROFILES):
            paths = []
            for index, reference in enumerate(fixture.layers):
                rendered = render_weave_layer(reference, profile, index, layout)
                path = output / f"{layout}-{profile}-L{index + 1}.png"
                Image.fromarray(rendered.image).save(path)
                paths.append(path)
                manifest["inputs"].append(
                    {
                        "file": path.name,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                        "width": fixture.width,
                        "height": fixture.height,
                    }
                )
                oracle["damage_events"].append(
                    {
                        "file": path.name,
                        "events": [asdict(event) for event in rendered.events],
                        "removed_px": int(rendered.removed.sum()),
                        "faded_gap_px": int(rendered.faded_gap.sum()),
                    }
                )
                with Image.open(path) as image:
                    if index == 1:
                        crops.paste(image.crop(crop_box), (column * 320, row * 480 + 40))
                        ImageDraw.Draw(crops).text(
                            (column * 320 + 4, row * 480 + 5),
                            f"{layout} {profile} L2; native 1:1",
                            fill="black",
                        )
                        manifest["native_crops"].append({"file": path.name, "box": crop_box})
                    if profile == "clean":
                        thumb = image.copy()
                        thumb.thumbnail((360, 350))
                        overview.paste(thumb, (column * 360, index * 390 + 30))
                        ImageDraw.Draw(overview).text(
                            (column * 360 + 4, index * 390 + 5),
                            f"{layout} L{index + 1}; reduced",
                            fill="black",
                        )
                del rendered
            with TemporaryDirectory(prefix="weave-benchmark-") as scratch:
                store = Store(Path(scratch))
                state = store.create(f"{layout} {profile}")
                for path in paths:
                    layer = add_image(state, store, path.read_bytes(), path.stem)
                    px = state.pixels[layer.id]
                    assert not (px.observed.any() or px.inferred().any() or px.protected.any())
                install_annotations(state, fixture)
                manifest["supplied_annotations"].append(
                    {
                        "layout": layout,
                        "profile": profile,
                        "initial_masks_empty": True,
                        "layers": [[m.model_dump() for m in layer.markers] for layer in state.project.layers],
                    }
                )
                assert all(not m.net for m in state.project.layers[1].markers)
                assert all(not m.net for m in state.project.layers[0].markers if m.kind == "via")
                for layer in state.project.layers:
                    operations.analyze_layer(state, store, layer.id, Analyze(directional_scratch=True))
                stages = score(state, fixture, "supplied_hints")
                apply_ballmap(state, state.project.layers[0].id, ballmap_input(fixture, restore=True))
                stages.extend(score(state, fixture, "explicit_land_restore"))
                for layer in state.project.layers:
                    batch_review.auto_review(
                        state, layer.id, AutoReview(expected_revision=state.project.revision)
                    )
                stages.extend(score(state, fixture, "automatic_after_land_restore"))
                for stage in stages:
                    stage.update(layout=layout, profile=profile, algorithm="current")
                metrics.extend(stages)
                upper = stages[-1]
                print(
                    f"{layout} {profile}: upper {upper['correct_terminals']}/{len(upper['terminals'])}; "
                    f"opens {upper['physical_pairs']['false_open']}; "
                    f"shorts {upper['physical_pairs']['false_short']}",
                    flush=True,
                )
                del state
    crops.save(output / "native-pad-crops.png")
    overview.save(output / "full-layer-overview.png")
    for filename, content in (
        ("manifest.json", manifest),
        ("evaluation-oracle.json", oracle),
        ("metrics.json", metrics),
    ):
        (output / filename).write_text(json.dumps(content, indent=2) + "\n")
    write_readme(output, metrics)
    errors = clean_errors(metrics)
    if errors:
        raise RuntimeError("Clean fixture/reconstruction gate failed; see README.md: " + "; ".join(errors))
    return output / "metrics.json"


def _write_mapping(path: Path, fixture: BgaFixture) -> None:
    """Store oracle NET mappings separately from supplied reconstruction inputs."""
    with path.open("w", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(("lower_name", "lower_x", "lower_y", "upper_name", "upper_x", "upper_y", "net"))
        for lower in fixture.layers[0].terminals:
            for upper in fixture.layers[1].terminals:
                if lower.net == upper.net:
                    writer.writerow((lower.name, lower.x, lower.y, upper.name, upper.x, upper.y, lower.net))


if __name__ == "__main__":
    print(run_benchmark(ROOT / "outputs/plane-benchmark"))
