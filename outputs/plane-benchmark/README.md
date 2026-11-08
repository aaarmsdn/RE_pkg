# Plane-dominant package saved-PNG benchmark

|Layout|Profile|Upper correct|Pair opens|Pair shorts|False added px|Missing copper px|
|---|---|---:|---:|---:|---:|---:|
|weave16|clean|19/19|0|0|0|0|
|weave16|damaged|17/19|6|0|0|2780|
|weave16|severe|0/19|15|1035|0|8570|
|weave16|diagonal|0/19|59|0|0|191501|
|weave32|clean|35/35|0|0|0|0|
|weave32|damaged|33/35|6|0|0|2752|
|weave32|severe|0/35|15|3019|0|8169|
|weave32|diagonal|0/35|76|0|0|190566|
|micro32|clean|35/35|0|0|0|0|
|micro32|damaged|33/35|6|0|0|2701|
|micro32|severe|0/35|38|1501|0|20750|
|micro32|diagonal|0/35|76|0|0|190224|

Clean-case gate: PASS.

Run: `uv run python -m pkg_re.weave_benchmark`.

24 PNG inputs: 3 layouts × clean/damaged/severe/diagonal × 2 layers. Every case reopens the saved PNG bytes through ordinary ingestion with empty observed/inferred/protected masks. Only supplied lower ball names and unnamed upper contacts/vias enter reconstruction. Source/input SHA256 and actual supplied annotations are in manifest.json. Geometry, damage events and NET mapping are evaluation-only in evaluation-oracle.json and *-evaluation-mapping.csv; none is loaded by reconstruction.

Table values are final, after explicit ball-land restoration and automatic review. Copper counts sum both layers. Physical pair counts are stack-wide, using connected copper and contacting vias; matching NET names cannot join separate islands. metrics.json retains supplied_hints, explicit_land_restore and automatic_after_land_restore stages plus dynamic per-NET area and routing metrics. Directional scratch proposals are enabled for every profile; actual changes still require the existing NET, contact and protection checks. Correct terminal names do not establish complete copper recovery. False added counts only inferred false copper; false_copper_px in metrics.json also includes observed false copper from blur.

native-pad-crops.png contains unscaled crops of the actual saved L2 PNGs, all four profiles. Crop boxes are recorded in manifest.json. full-layer-overview.png is a labelled reduced overview of the clean L1/L2 images; original PNGs retain native detail. Native pad dimensions, pitch, resolution, measured plane coverage and its denominator are recorded per layout in evaluation-oracle.json. Temporary projects are discarded; this output contains no project dumps.
