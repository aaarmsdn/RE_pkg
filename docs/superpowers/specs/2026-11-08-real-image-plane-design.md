# Real-image workflow and plane-dominant stress cases

User requested implementation and push to https://github.com/aaarmsdn/RE_pkg. This extends the previously approved processing + connectivity constraints + human correction design.

## Outcome

The first action is opening real PNG/JPEG layers. Synthetic examples and public references remain secondary. Existing saved projects, corrections, exports and NET safeguards stay compatible.

New woven examples retain DQ16/DQ32 permutations and micro pads. On each layer, power/ground planes occupy approximately90% (target90%, tolerance1percentage point) of image area outside non-plane routing/contact geometry. Explicit area denominator and measured coverage are exported. Required inter-NET clearance remains dielectric. VSS/VDDQ/VDD allocation aims at50/25/25 where physically feasible; measured allocation is reported rather than fabricated.

Add a diagonal profile with uniform parallel scratches across the full image, crossing both planes and thin routes. Scratch geometry stays evaluation-only. The inference engine cannot read clean masks, net mappings, damage coordinates or the chosen rendering angle.

## Approach

Keep native pixel coordinates and the existing reversible correction workflow. Add evidence-based material selection suitable for real images, including user-tunable copper/background separation rather than assuming all bright pixels are copper. Use direction-aware scratch proposal generation with existing NET conflict/protected-void/annotation checks. Preserve observed and inferred copper separately.

Alternatives considered: broad morphological closing would bridge narrow inter-NET gaps; learned segmentation would require labeled real training/validation data unavailable here. Extend the current explicit heuristic pipeline and expose its uncertainty.

The GUI presents image input, analysis settings, and review in a compact workspace. Advanced calibration/ballmap/ROI and examples remain available through disclosure controls. Never imply that assigning a seed name proves real-world NET correctness.

## Validation and honest pass criteria

1. Independent raster checks: coverage target, connected intended geometry, zero cross-NET touches, required vias and pad dimensions.
2. Saved-PNG roundtrip: clean/damaged/severe/diagonal on allnewlayouts; physical terminal/pair connectivity, false additions, remaining loss and plane-area error. Retain failures.
3. Real public PCB/photo: ordinary upload, native ROI, material extraction, manual confirmed NET hint, propagation, correction and export smoke test. Pixel-level material samples may be manually verified. No groundtruth netlist exists, so no real-image accuracy percentage is claimed.
4. UI desktop/narrow viewport and failure-state tests. Full existing backend/frontend suite.
5. Push source, tests, documentation and compact reproducible metrics. Exclude private projects, local runtime/logs/screenshots, downloaded third-party images and large generated PNGs. Publish no credentials. Remote is currently empty and public.

## Limit

Completely erased boundaries are not uniquely recoverable from one PNG. The strategy must flag ambiguity instead of claiming every severe case passes. Cadence.mcm and Siwave remain follow-up integration.
