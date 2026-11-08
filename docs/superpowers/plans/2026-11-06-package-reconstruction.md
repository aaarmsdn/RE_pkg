# Package Reconstruction Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Run a local, editable package photo reconstruction prototype with plane/trace repair proposals, net propagation and reproducible area exports.

**Architecture:** A Python/FastAPI application owns project state and image evidence. Pure NumPy/OpenCV geometry functions produce masks, repair proposals and connected regions. A React/TypeScript workbench edits at original-pixel coordinates through the documented HTTP contract; reference photos and deterministic synthetic examples are distinct.

**Tech Stack:** Python 3.11+, uv, FastAPI/Pydantic, OpenCV, NumPy, SciPy, Shapely, Pillow, local Tesseract; React/TypeScript/Vite.

**Spec:** `docs/superpowers/specs/2026-11-06-package-reconstruction-design.md` (user approved, including plane repairs).

## Global Constraints

- Local-only processing; loopback server; no cloud OCR or model calls.
- Images have native pixel coordinates. Manual scale and optional three-point affine registration give mm coordinates with y-up convention.
- No automatic approval of trace/plane topology repair. Candidate acceptance must preserve protected dielectric masks.
- No pixel information invented by enlargement. Native-resolution ROI processing allowed with explicit bounds.
- Actual MCM/Siwave adapter remains a later validated stage; this prototype exports neutral geometry, masks, images and reports.
- Every area is based on accepted masks with observed/inferred provenance, void subtraction and no double counting.
- Keep product modules focused; pure functions and explicit typed request models.

## Review Focus

1. Uncalibrated source: area in pixels only, mm² remains null; never assumes a scale.
2. Protected void inside a damaged plane: accepted repair cannot overwrite it; test in engine task.
3. Two seeds with different net names in one connected region: return conflict, never silently select first; test in analysis task.
4. Reanalysis/save/reopen must preserve manual add/erase/protection and markers; test in API task.
5. ROI offsets/mirroring and width in native pixels must survive export; test exact rectangular geometry and affine determinant area.

## API / ownership contract

See `docs/api-contract.md`, shared between independent core, API, UI tasks. Contract changes require coordination with root before editing other modules.

### Task 1: Pure image and geometry engine

**Owner/files:** core worker owns `pkg_re/engine/`, `tests/test_engine*.py` only.

**Interfaces:** exact functions/dataclasses defined in `docs/api-contract.md` Engine section. NumPy boolean masks are native resolution. No filesystem/HTTP in engine.

- [x] Write failing tests: 3-pixel separated traces stay separate; plane false hole proposal excludes protected antipad; scratch proposal never accepted automatically; partial annotation mask excluded; observed/inferred area no overlap; affine determinant gives exact cell area; different net seed conflict; via only specified layer range.
- [x] Run `uv run pytest tests/test_engine*.py -q` and record RED.
- [x] Implement segmentation, bounded candidate proposals, edits, connected regions and exact pixel-cell polygons/export primitives.
- [x] Run same suite to GREEN, report evidence and limits.

### Task 2: Local API, storage, annotations, project export

**Owner/files:** root owns `pkg_re/models.py`, `pkg_re/store.py`, `pkg_re/app.py`, additional `pkg_re/*.py` API helpers, pyproject/config, `tests/test_api.py`, `README.md`.

- [x] Write failing API tests for demo creation, image upload, segmentation, candidate decision, protected stroke, recalibration, marker update, net area, JSON/CSV/SVG/project zip export, undo/redo and reopen persistence.
- [x] Run targeted tests and record RED.
- [x] Implement the API contract; preserve source image plus observed/added/erased/protected masks and edit history. Validate filenames, payload bounds, coordinates, layer references, scales, via spans. Reject external origins for mutations.
- [x] Provide local Tesseract text boxes and lime shape marker detection with explicit review; ballmap CSV-to-grid with populated sites and missing land insertion. Do not assume labels are valid.
- [x] Integrate engine, run API tests to GREEN.

### Task 3: Working reconstruction GUI

**Owner/files:** frontend worker owns `frontend/`, `DESIGN.md` only.

- [x] Extract the approved companion mockup tokens/layout into DESIGN.md before components.
- [x] Build typed API client per contract, desktop workbench with source/layer selection, canvas overlay, pan/zoom, pointer strokes, marker/net editing, calibration/registration fields, candidate accept/reject, area table, undo/redo, downloads/save/reload.
- [x] Make synthetic demo explicitly labeled; public references are actual local images with no fake result numbers. Display native pixel dimensions and unknown scale.
- [x] Run TypeScript check and production build. Root then drives real UI end-to-end against the backend.

### Task 4: Integration, regression and handoff

**Owner/files:** root; fresh read-only final reviewer.

- [x] Start loopback application with built UI; verify synthetic plane hole/scratch acceptance, protected void, split stroke, seed conflict, net area, undo/redo and exports through real UI/API.
- [x] Load a native-resolution ROI from actual sanded PCB image; record segmentation and correction behavior without claiming true net accuracy.
- [x] Run complete Python suite, TS check/build. Independent review of final code and evidence, then fix consequential defects with reproducing tests.
- [x] Write README with exact uv/build/run commands, sample provenance, workflow, known domain limitations, and MCM/AEDT validation boundary. Save authored files locally, excluding downloaded restricted images, user projects, caches and dependencies from version control. No commit/push requested.

## Execution decisions

User explicitly approved design and implementation. No additional permission gate is introduced for reversible implementation choices. Independent engine and GUI tasks run in parallel per dispatching-parallel-agents; root owns API/integration to avoid shared-file conflicts. The initial directory had no existing code or git repository; initialize a feature branch in place rather than creating a second empty checkout.

## Progress

- Design approved: 2026-11-06.
- Reference image acquisition: 7 images verified by decode, dimensions, SHA-256.
- Companion mockup: reviewed in real browser; not product code.

## Prototype delivery notes

- Core/API/GUI implemented; independent code review and browser QA in `.omo/evidence/`.
- Native pixel-cell polygons are generated from accepted masks at export; masks remain editable canonical state in this prototype.
- Calibration accepts manual similarity/affine numbers; three-point click fit and automatic ball-grid fitting remain later work.
- Brush geometry editing shipped; advanced polygon handles/trace centerline width controls, uncertainty scenarios, full stackup/padstack/MCM adapter remain later work.
- OCR stores source bbox/confidence and snaps to existing nearby ball marker, then requires user review and reanalysis. No hidden photo detail is recovered automatically.
- Published real references are qualitative input tests; no real DRAM accuracy benchmark claimed.
