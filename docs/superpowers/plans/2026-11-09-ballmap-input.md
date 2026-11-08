# Ballmap input and pitch Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans for backend integration and superpowers:dispatching-parallel-agents for the independently owned frontend against the interface below.

**Goal:** Upload a 2D Unicode NPY ballmap, inspect its labeled grid, enter ball pitch, and persist its placement in a photo project.

**Architecture:** A stateless backend preview validates NPY before allocation. The existing transactional ballmap apply route accepts either CSV or a decoded grid and persists the input on the layer; the GUI displays a colored logical grid and physical scale controls.

**Tech Stack:** Existing FastAPI, NumPy, Pydantic, React, TypeScript, Zod.

**Spec:** `docs/superpowers/specs/2026-11-08-diagonal-severe-npy-design.md` (NPY input section only).

## Constraints and interfaces

- Unicode strings only, shape `(rows, columns)`, 1–5000 cells, names ≤160 characters, upload ≤4 MiB, header ≤10 KiB, no pickle. Preserve NET spelling; trim surrounding whitespace.
- Empty string means no ball; `?` and `NC` mean a physical ball without a NET seed. Repeated named NETs remain valid.
- `POST /api/ballmaps/preview`, multipart `file`, returns `{grid: string[][], rows: number, cols: number}`. It does not change a project.
- Existing apply route takes `{grid?: string[][], csv?: string, origin:{x,y}, pitch_px, pitch_mm, radius_px, restore_missing}` with exactly one of grid/CSV.
- Persist the same validated input as nullable `layer.ballmap`, including grid/CSV and pitch. Older projects default to null. A square pitch is used in both axes; row increases downward, column rightward. This axis-aligned placement resets the affine scale, matching existing CSV behavior; explain this in the GUI.
- No automatic registration, new recovery algorithm, or dependency changes in this task.

## Review focus

- Malformed/oversized/object NPY must fail without mutating the current map.
- Missing sites, unknown NETs and NC must not become named NET seeds.
- Applied grid and pitch must survive reopen, undo/redo and ZIP export/import.
- Failed apply must not discard the preview; switching layers must not apply stale file responses.
- On narrow screens, the grid scrolls within its panel and retains legible names.

### Task 1: Backend import and persisted placement

**Files:** `pkg_re/ballmaps.py`, `pkg_re/models.py`, `pkg_re/annotations.py`, `pkg_re/routes.py`, `tests/test_ballmap_npy.py`.

- [x] Add failing parser/API tests for rectangular Unicode, reserved cells, payload/header validation, grid application and persistence.
- [x] Run targeted tests and observe the failure before implementing.
- [x] Add bounded parser, preview route, grid validation and persisted input, preserving existing CSV callers.
- [x] Run targeted tests and existing ballmap tests.

### Task 2: Frontend input and preview

**Files:** `frontend/src/Ballmap.tsx`, `frontend/src/api.ts`, `frontend/src/App.tsx`, related styles and frontend tests.

- [x] Use the agreed API to preview a local NPY and render row/column labels, NET colors, ball/NET counts and reserved-cell legend.
- [x] Expose pitch in mm plus image origin/pitch/radius controls before applying; retain CSV under an advanced disclosure.
- [x] Show the feature directly in the input area for the active layer; restore saved settings from layer.ballmap.
- [x] Verify validation and rendering with focused tests, then TypeScript and build.

### Task 3: Integration and handoff

**Files:** `README.md`, `docs/examples/ballmap/README.md`, QA evidence under ignored `.omo/evidence/ballmap-input/`.

- [x] Run the complete backend/frontend suites and lint/build.
- [x] Verify real browser upload, grid display, pitch edit, apply, reload and error state; inspect desktop and narrow layout.
- [x] Review the diff, resolve actionable findings, update usage documentation and prepare the verified change for commit/push within existing authorization.

## Execution evidence

Backend parser/application tests:33 passed, including malformed header fixes found in independent review. Frontend:55 passed, TypeScript/build clean. Browser: actual NPY upload,5 mm apply/reload, invalid upload retention, reserved sites,5000-cell desktop/phone scrolling verified. Evidence:`.omo/evidence/ballmap-input/qa.md`; independent review approved with no blockers. Final full backend result:`.omo/evidence/ballmap-input/pytest-final.txt`.
