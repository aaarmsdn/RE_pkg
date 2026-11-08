# Dense die pad examples and damage recovery implementation plan

> For agentic workers: implement independent fixture and reconstruction tasks; root integrates and verifies. Existing approved image-processing + physical NET constraints + human review design remains in force. User explicitly requested strategy and execution.

Goal: add several small dense L2 die-pad stacks, including center-concentrated pads and thin power routes, and improve measured damaged-PNG recovery without inventing shorts.

Architecture: deterministic reference geometry renders actual PNG inputs; truth is evaluation-only. Existing graph and atomic batch guard remain the authority for approving changes. Improve bounded repair coverage and local geometric evidence rather than indiscriminate mask closing.

Tech stack: current Python/NumPy/OpenCV/SciPy + React. No new runtime dependency.
Spec: docs/superpowers/specs/2026-11-06-package-reconstruction-design.md; current request extends fixtures and damage handling.

## Constraints and choices
- Keep existing BGA example and saved projects compatible.
- New cases: dense edge pads, center two-bank pads, center compact staggered/array pads; >=16DQ plus VSS/VDD/VDDQ. Pad width roughly1/6–1/10 of ball diameter; traces/gaps2–4px plus explicit1px stress. Values are test assumptions pending user's physical dimensions; original5mm ball pitch is a synthetic calibration, not a claimed production package.
- Preserve32-ball8x4 populations and nominal pitch where possible. Via connectivity must be real on both layers; power has>=15 vias per net and includes thin feeder routes to planes. Declare actual dimensions and layer plane ratios, don't fake density by zooming a screenshot.
- Save clean/damaged/severe PNGs, reingest ordinary bytes and supplied lower ball labels + unnamed via/pad coordinates. No pristine mask or damage locations enter reconstruction.
- No unrestricted morphological closing/upscaling as evidence. Native pixels, protected clearances, explicit erases, annotation unknowns, contacts and cross-NET rejection retained.
- Benchmark before/after: terminal NET correctness, false open/short, per-net area, added copper precision, recovered missing copper. Clean must not gain false shorts or bogus copper. Severe unrecoverable boundaries remain review.

## Tasks
- [x] Reproduce original damaged BGA failures by event/candidate/NET contact before edits; retain baseline artifact.
- [x] Add independent dense die fixtures/rendering with no overlaps, connected intended NETs and small pads/feeder dimensions verified.
- [x] Improve repair proposal coverage: preserve thin long scratches and small trace gaps under a bounded budget; diagnose candidate starvation before choosing prioritization.
- [x] Improve local continuity recommendation from measured flanks/direction and physical NETs; preserve ambiguous antipads and parallel gaps. Test negative cases and contact survival first.
- [x] Wire examples into sample picker/API using existing controls, expose dimensions/constraints clearly.
- [x] Reopen PNG suite and compare original + new layouts across damage levels. Publish actual successful/failed cases and strategy for remaining severe failures.
- [x] Full tests/build, browser QA of central-pad and damaged cases, independent source review.

## Review focus
Wrongly closing interleaved signal/power gaps; omitted tiny candidate under100limit; thin power becoming orphaned; multipleNET hints in one blurred component; inference leaking from renderer truth; legacy state/API compatibility.
