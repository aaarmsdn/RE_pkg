# Real-image workflow and plane stress Implementation Plan

> For agentic workers: use the approved extension and parallel ownership below. User requested execution plus Git push; do not add another approval gate.

**Goal:** Plane-dominant realistic stress inputs, diagonal damage recovery, real-photo-first GUI, reproducible validation and GitHub delivery.

**Architecture:** Existing Python/OpenCV/SciPy processing and React GUI. Keep saved-project compatibility and inference/evaluation separation. No new runtime dependency unless existing primitives cannot solve a demonstrated problem.

**Spec:** docs/superpowers/specs/2026-11-08-real-image-plane-design.md

## Tasks and ownership

- [x] Fixture worker: weave_fixture.py / weave_render.py and new plane helper as needed; tests/test_weave_fixture.py. Add measured90%planes preserving routes/contacts. Add diagonal render helper/profile with repeated stripes. Publish schema and measurements. Test independent connectivity, clearance, denominator and deterministic damage.
- [x] Recovery worker: engine segmentation/repairs/continuity, operations.py and NET review only as needed; own models.py/type additions and correspondingbackendtests. Diagnose real-photo failure and add explicit segmentation mode + optional rotation-aware scratch proposals. Keep old defaults compatible. Communicate frontend/API fields before editing. Test realpatches, protected gaps, differentNET veto, unknown/occlusion and native1px traces.
- [x] UI worker: frontend only, all input/analysis/workspace layout and APItypes/tests. Real image upload can start a blankproject directly, inputfirst emptyview, examples collapsed, progress/uncertainty concise, controls readable ondesktop/mobile. Coordinate new analysis fields with recoveryworker; no mocked-useState presentation tests. Root owns realbrowserQA.
- [x] Root: benchmark/profileintegration and realimageevaluation; create strategy/report, run fullverification, capture realupload/analyze/seed/exportbrowser evidence, preserve existingdata. Reviewchangedcode and obtain one independentfinalreview.
- [ ] Root: inspect publicremote, create clean initialcommit(s) containing appsource/directtests/docs/reproduciblemetrics only, pushwithoutforce, verifyremoteSHA andclean trackedstatus.

## Verification

Meaningful failing tests precede algorithm/geometry changes. Existing integration tests must remain. Run pytest, ruff, frontendcheck/test/build, nativePNGbenchmark, APIrealimage smoke test, actualbrowser upload/review. Record failing damage cases without oracle-based fixes. Finalreviewfocus: planeoverlap/islands, hiddentruthinput, profilecompatibility, uploadwithoutproject, brightdielectricfalsepositives, diagonal gapmerging, publication of private/generated files.
