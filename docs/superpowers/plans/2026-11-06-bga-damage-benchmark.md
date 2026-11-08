# BGA PNG damage benchmark implementation plan

> **For agentic workers:** Use the existing approved reconstruction design and scoped parallel tasks; no new architecture or dependency installation.

**Goal:** Build and test the user's specific two-layer package as pristine and damaged PNG inputs, and diagnose raw-PCB net failures.

**Architecture:** Generate independent intended geometry, render optical PNGs, ingest PNG bytes through the normal image boundary, and analyze pixels using the normal engine. Ballmap and via locations are explicit supplied annotations; intended copper masks never initialize observed/accepted/protected geometry. A separate benchmark compares output with truth and reports failures.

**Tech Stack:** Existing Python, NumPy/SciPy/OpenCV/Pillow, FastAPI, React/TypeScript.

**Spec:** User's 2026-11-06 request plus approved `docs/superpowers/specs/2026-11-06-package-reconstruction-design.md`.

## Constraints and interpretation

- L1: centered 8-column × 4-row grid; 5mm pitch; 16 unique DQ0–15, 8 VSS, 4 VDD, 4 VDDQ balls.
- L2: DQ0–7 bottom and DQ8–15 top (correct duplicate DQ7 from the request); VSS/VDDQ alternate between DQ pads.
- User clarification: VDD pads total6, left/center/right on each edge row; center between bottom DQ3/4 and top DQ10/11.
- Signal exactly1 interlayer via pernet; each power net at least15 vias. No hidden direct upper-net seeds.
- Plane-only areas target50% VSS,25% VDDQ,25% VDD; excludes traces/terminals/via copper. Report raster measurement/tolerance separately from total net copper area.
- Inputs stay ≤4Mpx per layer. Do not downsample native thin routes. 5mm pitch remains literal.
- Keep old dense demo and saved user projects intact. New sample modes clean/damaged/severe.

## Review focus

- Net masks touching creates accidental shorts: test independent per-net occupancy and physical whole-stack terminal connectivity.
- Damaged source should not access pristine geometry during recognition: raw PNG upload starts with empty geometry; metadata-only seed stage is explicit.
- Missing/half balls: compare observed loss and explicit populated-grid land inference; do not invent escape traces.
- Faded tight gaps can be optically ambiguous: measure merges/conflicts and recall, never silently claim recovery.
- Public PCB lacks known net labels and may violate brightness/chroma assumptions: reproduce both, distinguish extraction from identity.

## Tasks

- [x] Geometry worker: `pkg_re/bga_fixture.py`, `tests/test_bga_fixture.py`; exact counts, pitch, pad order, plane ratios, disjoint copper and via contacts.
- [x] Root: `pkg_re/bga_sample.py`, `pkg_re/bga_benchmark.py`, focused tests; seeded repeatable noise, scratches/holes, absent/half lands, edge blur, narrow/faded gaps; export PNG files and reopen normal ingestion.
- [x] Root: `models.py`/`routes.py` sample selector API preserving `demo:true` compatibility; benchmark metadata/CSV/JSON and saved GUI examples.
- [x] Frontend worker: explicit sample selector and extraction/seed/net diagnostics, retain repair review spatial controls.
- [x] PCB worker: native ROI and OCR/seed/material measurements with source crops and truthful diagnosis; fix only a reproduced defect.
- [x] Run targeted tests then full Python/frontend/build; manual GUI verify new sample generation and analysis; source review and saved screenshots/report.
