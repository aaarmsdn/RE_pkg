# Woven DQ32 Examples Implementation Plan

> For agentic workers: implement the existing approved reconstruction design extension with independent fixture and UI ownership. User explicitly requested execution. No new approval or commit is needed.

**Goal:** Add complex ball-to-pad mappings, 32-signal examples (DQ0–31), and smaller, denser pads, then measure saved-PNG reconstruction.

**Architecture:** New deterministic reference fixtures reuse BgaFixture transport, ordinary PNG ingestion, supplied ball labels and unnamed upper contacts. Reference masks remain confined to rendering/evaluation. Preserve existing examples and reconstruction safety checks.

**Tech Stack:** Existing Python/NumPy/OpenCV/SciPy and React. No new dependency.

**Spec:** Latest user request plus docs/superpowers/specs/2026-11-06-package-reconstruction-design.md and docs/superpowers/specs/2026-11-06-damage-recovery-strategy.md.

## Choices and constraints

- Interpret 32 DQs as DQ0–31, not DQ0–32. Retain VSS/VDD/VDDQ.
- Three new samples: weave16, weave32, micro32. Include actual shuffled ball locations and bent routes to concentrated pads, not only renamed original straight routes.
- Target ordinary woven pads4×8px/pitch10px and micro pads2×4px/pitch6px; fixture implementer may adjust only if needed for physically disjoint geometry and must publish actual native dimensions.
- Two layers, physical contact through vias. Keep one signal via per signal and >=15 power vias per NET. If a routing constraint cannot be met, report it instead of drawing false same-layer crossings.
- Clean reference must have zero inter-NET overlap/touch, all intended terminal connectivity and physically connected vias. Verify actual raster dimensions and mapping permutation/route complexity.
- Save clean/damaged/severe PNGs; reopen bytes with empty masks and supplied lower names/unnamed upper contacts. Truth used only in metrics.
- Report all clean and damaged failures, copper area/false-added metrics and physical false opens/shorts. No claim that connectivity implies complete shape recovery.

## Tasks

- [x] Fixture worker: new pkg_re/weave_fixture.py and weave_render.py, tests/test_weave_fixture.py. Provide WeaveLayout, weave_fixture(layout)->BgaFixture, weave_metadata(fixture,layout)->dict, render_weave_layer(layer,profile,index,layout)->RenderedLayer. Measure and publish mapping and geometry.
- [x] UI worker: extend frontend DieSamples.tsx/api.ts and tests with die_weave16,die_weave32,die_micro32 using existing damage_profile. Show accurate signal count, pad dimensions and resolution stress.
- [x] Root: create weave_sample.py; extend models.py/routes.py; integration tests for newly generated unanalyzed two-layer PNG state and no truth leakage.
- [x] Root/benchmark worker: new weave_benchmark.py reuses current score and physical pair helpers, saves18PNGs+manifest+mapping CSV+summary/crops. No historical baseline reconstruction required for these new inputs.
- [x] Full relevant tests, existing compatibility checks, build, real browser create/analyze/zoom and independent review.

## Review focus

Overlapping same-layer route crossings; renamed-only sample masquerading as geometric complexity; 1px diagonal breaks; fixed16-signal assumptions; metadata dimensions disagreeing with raster; truth or upper NET names leaking into reconstruction; benchmark denominators hardcoded22.

## Completion evidence

See `.omo/evidence/weave/REPORT.md`, `.omo/evidence/weave-code-review.md`, and `outputs/weave-benchmark/README.md`. Python155/frontend38tests pass; actual browser creates allthree new layouts and analyzes weave32Clean through bothlayers. Clean recovery passes; damaged/severe failures are retained in results.
