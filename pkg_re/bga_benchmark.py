"""Reopen exported PNG inputs and quantify errors without truth-assisted inference.

Run: uv run python -m pkg_re.bga_benchmark
"""

import json
from dataclasses import asdict
from pathlib import Path
from typing import NotRequired, TypedDict

import numpy as np
from PIL import Image

from pkg_re.annotations import apply_ballmap
from pkg_re.bga_fixture import BgaFixture, bga_fixture
from pkg_re.bga_render import Profile, render_layer
from pkg_re.bga_sample import ballmap_input, install_annotations
from pkg_re.graph import analyze_graph, contact
from pkg_re.images import add_image
from pkg_re.models import Analyze, Marker
from pkg_re.operations import analyze_layer
from pkg_re.store import State, Store


class NetMetric(TypedDict):
    net: str
    truth_px: int
    assigned_px: int
    correct_px: int
    net_recall: float


class TerminalMetric(TypedDict):
    terminal: str
    expected: str
    assigned: str | None
    correct: bool


class LayerMetric(TypedDict):
    stage: str
    layer: str
    precision: float
    recall_pristine: float
    iou_pristine: float
    observed_px: int
    inferred_px: int
    conflict_px: int
    unassigned_px: int
    assigned_nets: list[str]
    pending_candidates: int
    candidate_fill_px: int
    candidate_true_missing_px: int
    terminals: list[TerminalMetric]
    per_net: list[NetMetric]
    profile: NotRequired[Profile]


def evaluate(state: State, fixture: BgaFixture, stage: str) -> list[LayerMetric]:
    """Evaluation only: intended geometry is never passed back to segmentation."""
    graph = analyze_graph(state)
    result: list[LayerMetric] = []
    for layer, reference in zip(state.project.layers, fixture.layers, strict=True):
        accepted = state.pixels[layer.id].accepted()
        truth = np.logical_or.reduce([net.mask for net in reference.nets])
        correct = int((accepted & truth).sum())
        rows = [r for r in graph.areas if r.layer_id == layer.id]
        proposals = np.zeros_like(accepted)
        for candidate in layer.candidates:
            if candidate.status == "pending":
                x, y, w, h = candidate.bbox
                proposals[y : y + h, x : x + w] |= state.pixels[layer.id].patches[candidate.id]
        proposals &= ~accepted
        labels = graph.labels[layer.id]
        regions = {region.id: region for region in graph.regions[layer.id]}
        per_net: list[NetMetric] = []
        for net in reference.nets:
            ids = [r.id for r in regions.values() if r.status == "assigned" and r.net == net.name]
            inferred = np.isin(labels, ids)
            overlap = int((inferred & net.mask).sum())
            per_net.append(
                {
                    "net": net.name,
                    "truth_px": int(net.mask.sum()),
                    "assigned_px": int(inferred.sum()),
                    "correct_px": overlap,
                    "net_recall": overlap / max(1, int(net.mask.sum())),
                }
            )
        terminals: list[TerminalMetric] = []
        for terminal in reference.terminals:
            rid = contact(
                labels,
                Marker(
                    id=terminal.name, kind=terminal.kind, x=terminal.x, y=terminal.y, radius=terminal.radius
                ),
            )
            region = regions.get(rid)
            terminals.append(
                {
                    "terminal": terminal.name,
                    "expected": terminal.net,
                    "assigned": region.net if region else None,
                    "correct": bool(region and region.status == "assigned" and region.net == terminal.net),
                }
            )
        result.append(
            {
                "stage": stage,
                "layer": reference.name,
                "precision": correct / max(1, int(accepted.sum())),
                "recall_pristine": correct / max(1, int(truth.sum())),
                "iou_pristine": correct / max(1, int((accepted | truth).sum())),
                "observed_px": int(state.pixels[layer.id].observed.sum()),
                "inferred_px": int((accepted & ~state.pixels[layer.id].observed).sum()),
                "conflict_px": sum(r.total_px for r in rows if r.status == "conflict"),
                "unassigned_px": sum(r.total_px for r in rows if r.status == "unassigned"),
                "assigned_nets": sorted({r.net for r in rows if r.status == "assigned"}),
                "pending_candidates": sum(c.status == "pending" for c in layer.candidates),
                "candidate_fill_px": int(proposals.sum()),
                "candidate_true_missing_px": int((proposals & truth).sum()),
                "terminals": terminals,
                "per_net": per_net,
            }
        )
    return result


def run_benchmark(output: Path) -> Path:
    """Write clean/damaged/severe PNGs, load their bytes and run the ordinary pipeline."""
    output.mkdir(parents=True, exist_ok=True)
    fixture = bga_fixture()
    (output / "ballmap.csv").write_text(ballmap_input(fixture).csv + "\n", encoding="utf-8")
    store = Store(output / "projects")
    all_metrics: list[LayerMetric] = []
    manifest = {
        "pitch_mm": fixture.pitch_px * fixture.mm_per_pixel,
        "mm_per_pixel": fixture.mm_per_pixel,
        "power_plane_ratios": [],
        "inputs": [],
        "annotations": [
            {"balls_or_pads": [asdict(t) for t in layer.terminals], "vias": [asdict(v) for v in layer.vias]}
            for layer in fixture.layers
        ],
    }
    for index, layer in enumerate(fixture.layers):
        areas = {net.name: int(net.plane_mask.sum()) for net in layer.nets if net.plane_mask.any()}
        total = sum(areas.values())
        manifest["power_plane_ratios"].append(
            {
                "layer": layer.name,
                "areas_px": areas,
                "fractions": {net: count / total for net, count in areas.items()},
            }
        )
        ids = np.zeros((fixture.height, fixture.width), dtype=np.uint8)
        names = []
        for number, net in enumerate(layer.nets, 1):
            ids[net.mask] = number
            names.append(net.name)
        np.savez_compressed(output / f"truth-L{index + 1}.npz", labels=ids, names=names)
    profiles: tuple[Profile, ...] = ("clean", "damaged", "severe")
    for profile in profiles:
        state = store.create(f"BGA PNG benchmark · {profile}")
        for index, reference in enumerate(fixture.layers):
            rendered = render_layer(reference, profile, index)
            path = output / f"{profile}-L{index + 1}.png"
            Image.fromarray(rendered.image).save(path)
            # This is the same byte boundary used by ordinary PNG uploads.
            layer = add_image(state, store, path.read_bytes(), path.stem)
            assert not state.pixels[layer.id].accepted().any()
            analyze_layer(state, store, layer.id, Analyze())
            manifest["inputs"].append(
                {
                    "file": path.name,
                    "sha256": layer.source_sha256,
                    "events": [asdict(event) for event in rendered.events],
                    "removed_px": int(rendered.removed.sum()),
                    "faded_gap_px": int(rendered.faded_gap.sum()),
                }
            )
        stages = evaluate(state, fixture, "png_only")
        install_annotations(state, fixture)
        stages.extend(evaluate(state, fixture, "supplied_ballmap_and_vias"))
        apply_ballmap(state, state.project.layers[0].id, ballmap_input(fixture, restore=True))
        stages.extend(evaluate(state, fixture, "explicit_land_restore"))
        store.save(state)
        for result in stages:
            result["profile"] = profile
        all_metrics.extend(stages)
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    path = output / "metrics.json"
    path.write_text(json.dumps(all_metrics, indent=2), encoding="utf-8")
    lines = [
        "# BGA PNG 재입력 시험",
        "",
        "정답 mask는 평가에만 사용. 인식 입력은 저장 후 다시 읽은 PNG.",
        "NET 이름은 별도 제공한 L1 ballmap에서만 시작하며 L2 pad/via에는 이름을 주입하지 않음.",
        "원본 PNG만으로는 임의의 DQ/VSS 이름을 알아낼 수 없으므로 png_only는 전부 미할당이 정상.",
        "",
        "Plane 비율은 pristine plane-only 면적. 아래 recall/IoU는 손상 전 전체 copper 기준.",
        "",
        "|입력|단계|층|Copper precision|Copper recall|IoU|충돌 px|미할당 px|정확한 terminal|",
        "|---|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in all_metrics:
        terminals = row["terminals"]
        count = sum(t["correct"] for t in terminals)
        lines.append(
            f"|{row['profile']}|{row['stage']}|{row['layer']}|"
            f"{row['precision']:.4%}|{row['recall_pristine']:.4%}|{row['iou_pristine']:.4%}|"
            f"{row['conflict_px']:,}|{row['unassigned_px']:,}|{count}/{len(terminals)}|"
        )
    lines.extend(
        [
            "",
            "복원 후보는 자동 승인하지 않음. "
            "명시적 land 보충은 known populated ball disk만 추가하며 "
            "숨겨진 escape trace를 만들지 않음. Severe의 흐려진 gap은 단일 PNG에서 정보가 소실될 수 있어 "
            "단락·미할당을 실패로 기록하고 사람 교정 대상으로 남김.",
            "",
            "실물 PCB 정답 netlist나 Cadence/Siwave 검증을 대신하는 시험이 아님.",
        ]
    )
    lines.extend(
        [
            "",
            "## 복원 후보의 오탐",
            "",
            "|입력|층|후보 수|제안 추가 px|정답상 빠진 copper px|",
            "|---|---|---:|---:|---:|",
        ]
    )
    for row in all_metrics:
        if row["stage"] == "supplied_ballmap_and_vias":
            lines.append(
                f"|{row['profile']}|{row['layer']}|{row['pending_candidates']}|"
                f"{row['candidate_fill_px']}|{row['candidate_true_missing_px']}|"
            )
    lines.extend(
        [
            "",
            "두 마지막 열의 차이는 의도적 gap/void에 대한 오탐입니다. "
            "후보 100개는 생성 상한이며 전체 후보 수가 아닙니다. "
            "Clean에도 후보가 생기므로 일괄 승인은 부적절합니다.",
            "",
            "Ballmap 재입력: ballmap.csv, Origin(336,528)px, pitch160px=5mm, land radius24px. "
            "좌표는 합성 샘플용이며 실제 PCB에 적용하면 안 됩니다.",
        ]
    )
    (output / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


if __name__ == "__main__":
    print(run_benchmark(Path(__file__).resolve().parent.parent / "outputs" / "bga-benchmark"))
