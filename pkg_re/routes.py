"""State-changing project routes; server owns all geometry decisions."""

from pathlib import Path
from typing import Annotated, assert_never

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from pkg_re.annotations import apply_ballmap, detect_annotations
from pkg_re.ballmaps import MAX_NPY_BYTES, decode_npy
from pkg_re.batch_review import auto_review, decide_batch, validate_selection
from pkg_re.bga_sample import create_bga_sample
from pkg_re.die_sample import create_die_sample
from pkg_re.exporting import import_bundle
from pkg_re.graph import project_view
from pkg_re.images import add_image, create_demo
from pkg_re.models import (
    Analyze,
    AutoReview,
    Ballmap,
    BatchDecision,
    Calibration,
    CreateProject,
    Decision,
    Detect,
    MarkersInput,
    Stroke,
)
from pkg_re.net_review import refresh_recommendations
from pkg_re.operations import analyze_layer, apply_stroke, decide_candidate
from pkg_re.short_splits import add_short_split_candidates
from pkg_re.store import State, Store
from pkg_re.weave_sample import create_weave_sample


def mutations(store: Store, reference_root: Path) -> APIRouter:
    router = APIRouter(prefix="/api")

    @router.post("/ballmaps/preview")
    def preview_ballmap(file: Annotated[UploadFile, File()]):
        try:
            grid = decode_npy(file.file.read(MAX_NPY_BYTES + 1))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc
        return {"grid": grid, "rows": len(grid), "cols": len(grid[0])}

    @router.post("/projects")
    def create(data: CreateProject):
        state = store.create(data.name)
        if data.demo:
            match data.sample:
                case "dense":
                    create_demo(state, store)
                case "bga_clean":
                    create_bga_sample(state, store, "clean")
                case "bga_damaged":
                    create_bga_sample(state, store, "damaged")
                case "bga_severe":
                    create_bga_sample(state, store, "severe")
                case "die_edge_dense":
                    create_die_sample(state, store, "edge_dense", data.damage_profile)
                case "die_center_rows":
                    create_die_sample(state, store, "center_rows", data.damage_profile)
                case "die_center_array":
                    create_die_sample(state, store, "center_array", data.damage_profile)
                case "die_weave16":
                    create_weave_sample(state, store, "weave16", data.damage_profile)
                case "die_weave32":
                    create_weave_sample(state, store, "weave32", data.damage_profile)
                case "die_micro32":
                    create_weave_sample(state, store, "micro32", data.damage_profile)
                case unreachable:
                    assert_never(unreachable)
            store.save(state)
        return project_view(state, store)

    @router.post("/projects/import")
    def import_project(file: Annotated[UploadFile, File()]):
        return project_view(import_bundle(file.file.read(150_000_001), store), store)

    @router.post("/projects/{pid}/layers")
    def upload(pid: str, file: Annotated[UploadFile, File()], name: str = Form("")):
        payload = file.file.read(80_000_001)

        def operation(state: State):
            if len(state.project.layers) >= 24:
                raise HTTPException(422, "At most 24 layers supported")
            add_image(state, store, payload, name or file.filename or "Layer")

        return project_view(store.mutate(pid, operation), store)

    @router.post("/projects/{pid}/references/{rid}")
    def reference(pid: str, rid: str):
        allowed = {"pcb_L1", "pcb_L2", "pcb_L3", "pcb_L4", "package_fig8", "package_fig10", "package_fig12"}
        if rid not in allowed:
            raise HTTPException(404, "Unknown reference")
        path = reference_root / f"{rid}.jpg"
        if not path.is_file():
            raise HTTPException(404, "Reference image not downloaded; see references/README.md")

        def operation(state: State):
            if len(state.project.layers) >= 24:
                raise HTTPException(422, "At most 24 layers supported")
            layer = add_image(state, store, path.read_bytes(), rid)
            layer.warnings.append(
                "Public reference image, no ground-truth netlist. Review copper/background polarity."
            )
            if rid in {"pcb_L3", "pcb_L4"}:
                layer.warnings.append(
                    "Backside view: confirm mirroring and registration before connecting layers."
                )
            if rid.startswith("package_"):
                layer.warnings.append(
                    "Laser-delayered published multipanel figure; crop one panel; not a raw registered layer."
                )

        return project_view(store.mutate(pid, operation), store)

    @router.post("/projects/{pid}/layers/{lid}/analyze")
    def analyze(pid: str, lid: str, data: Analyze):
        def operation(state: State):
            analyze_layer(state, store, lid, data)
            add_short_split_candidates(state, store, lid)
            if data.auto_process:
                auto_review(state, lid, AutoReview(expected_revision=state.project.revision))

        return project_view(
            store.mutate(
                pid,
                operation,
                f"analyze layer={lid} roi={data.roi} auto_process={data.auto_process}",
            ),
            store,
        )

    @router.post("/projects/{pid}/layers/{lid}/candidates/batch")
    def batch(pid: str, lid: str, data: BatchDecision):
        return project_view(
            store.mutate(
                pid,
                lambda state: decide_batch(state, lid, data),
                f"batch layer={lid} {data.model_dump_json()}",
            ),
            store,
        )

    @router.post("/projects/{pid}/layers/{lid}/candidates/auto")
    def automatic(pid: str, lid: str, data: AutoReview):
        return project_view(
            store.mutate(
                pid,
                lambda state: auto_review(state, lid, data),
                f"auto-review layer={lid} {data.model_dump_json()}",
            ),
            store,
        )

    @router.post("/projects/{pid}/layers/{lid}/candidates/evaluate")
    def evaluate(pid: str, lid: str, data: AutoReview):
        def operation(state: State):
            validate_selection(state, lid, data.ids, data.expected_revision)
            add_short_split_candidates(state, store, lid)
            refresh_recommendations(state, lid)

        return project_view(store.mutate(pid, operation, f"evaluate NET hints layer={lid}"), store)

    @router.post("/projects/{pid}/layers/{lid}/calibration")
    def calibrate(pid: str, lid: str, data: Calibration):
        def operation(state: State):
            state.layer(lid).calibration = data

        return project_view(store.mutate(pid, operation), store)

    @router.post("/projects/{pid}/layers/{lid}/stroke")
    def stroke(pid: str, lid: str, data: Stroke):
        return project_view(
            store.mutate(
                pid,
                lambda state: apply_stroke(state, lid, data),
                f"stroke layer={lid} {data.model_dump_json()}",
            ),
            store,
        )

    @router.post("/projects/{pid}/layers/{lid}/candidate")
    def candidate(pid: str, lid: str, data: Decision):
        return project_view(
            store.mutate(
                pid,
                lambda state: decide_candidate(state, lid, data),
                f"candidate layer={lid} {data.model_dump_json()}",
            ),
            store,
        )

    @router.put("/projects/{pid}/layers/{lid}/markers")
    def markers(pid: str, lid: str, data: MarkersInput):
        def operation(state: State):
            layer = state.layer(lid)
            ids = {entry.id for entry in state.project.layers}
            if len({m.id for m in data.markers}) != len(data.markers):
                raise HTTPException(422, "Duplicate marker IDs")
            for marker in data.markers:
                if not 0 <= marker.x < layer.width or not 0 <= marker.y < layer.height:
                    raise HTTPException(422, "Marker outside source image")
                if marker.end_layer_id is not None and marker.end_layer_id not in ids:
                    raise HTTPException(422, "Unknown via end layer")
            layer.markers = data.markers

        return project_view(store.mutate(pid, operation), store)

    @router.post("/projects/{pid}/layers/{lid}/detect")
    def detect(pid: str, lid: str, data: Detect):
        return project_view(
            store.mutate(pid, lambda state: detect_annotations(state, store, lid, data)), store
        )

    @router.post("/projects/{pid}/layers/{lid}/ballmap")
    def ballmap(pid: str, lid: str, data: Ballmap):
        return project_view(
            store.mutate(
                pid,
                lambda state: apply_ballmap(state, lid, data),
                f"ballmap layer={lid} restore={data.restore_missing}",
            ),
            store,
        )

    @router.post("/projects/{pid}/undo")
    def undo(pid: str):
        return project_view(store.history(pid, True), store)

    @router.post("/projects/{pid}/redo")
    def redo(pid: str):
        return project_view(store.history(pid, False), store)

    return router
