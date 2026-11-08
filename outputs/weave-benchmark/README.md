# Woven-package saved-PNG benchmark

|Layout|Profile|Upper correct|Pair opens|Pair shorts|False added px|Missing copper px|
|---|---|---:|---:|---:|---:|---:|
|weave16|clean|19/19|0|0|0|0|
|weave16|damaged|17/19|6|0|0|479|
|weave16|severe|0/19|17|84|0|1633|
|weave32|clean|35/35|0|0|0|0|
|weave32|damaged|33/35|6|0|0|433|
|weave32|severe|0/35|16|434|0|1801|
|micro32|clean|35/35|0|0|0|0|
|micro32|damaged|33/35|6|0|0|435|
|micro32|severe|0/35|47|112|0|14631|

Clean-case gate: PASS.

Run: `uv run python -m pkg_re.weave_benchmark`.

18 PNG inputs: 3 layouts × clean/damaged/severe × 2 layers. Every case reopens the saved PNG bytes through ordinary ingestion with empty observed/inferred/protected masks. Only supplied lower ball names and unnamed upper contacts/vias enter reconstruction. Source/input SHA256 and actual supplied annotations are in manifest.json. Geometry, damage events and NET mapping are evaluation-only in evaluation-oracle.json and *-evaluation-mapping.csv; none is loaded by reconstruction.

Table values are final, after explicit ball-land restoration and automatic review. Copper counts sum both layers. Physical pair counts are stack-wide, using connected copper and contacting vias; matching NET names cannot join separate islands. metrics.json retains supplied_hints, explicit_land_restore and automatic_after_land_restore stages plus dynamic per-NET area and routing metrics. Correct terminal names do not establish complete copper recovery. False added counts only inferred false copper; false_copper_px in metrics.json also includes observed false copper from blur.

native-pad-crops.png contains unscaled crops of the actual saved L2 PNGs, all three profiles. Crop boxes are recorded in manifest.json. full-layer-overview.png is a labelled reduced overview of the clean L1/L2 images; original PNGs retain native detail. Native pad dimensions, pitch and resolution are recorded per layout in evaluation-oracle.json. Temporary projects are discarded; this output contains no project dumps.
