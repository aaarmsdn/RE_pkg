# Dense die PNG benchmark

Run: `uv run python -m pkg_re.die_benchmark`

18 native PNGs: 3 independently routed layouts × clean/damaged/severe × 2 layers. All runs reopen identical saved PNG bytes with blank initial masks, confirmed lower ballmap, and unnamed pads/vias. Truth masks and terminal nets are used only in evaluation.

Baseline files were reconstructed from a captured pre-edit read, not a Git commit. replay_baseline.py reproduced damage-baseline.json exactly; source/replay SHA256 hashes are in manifest.json. Dense fixture baseline measurements were captured now, not before editing.

Native pad width×height 6×12 px, pitch 16 px, fine trace width 3 px. Center-array includes deliberate 1 px gap stress. native-pad-crops.png is a native-resolution 300×600 crop per layout. Edge-dense lower bank lies outside its crop; both center-layout banks are visible. Full PNGs retain all banks.

Physical pair scoring unions only connected copper and contacting vias; equal NET names alone never connect two islands. Expected connectivity comes from synthetic terminal nets. This fixture uses identical registration between layers. Scores include lower and upper terminals.

|Layout|Profile|Algorithm|Stage|Layer|Correct terminals|False added px|Recovered px|Missing px|Conflict px|Pair opens|Pair shorts|
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
|edge_dense|clean|baseline|supplied_hints|L1|32/32|0|0|0|0|0|0|
|edge_dense|clean|baseline|supplied_hints|L2|22/22|0|0|0|0|0|0|
|edge_dense|clean|baseline|explicit_land_restore|L1|32/32|0|0|0|0|0|0|
|edge_dense|clean|baseline|explicit_land_restore|L2|22/22|0|0|0|0|0|0|
|edge_dense|clean|baseline|automatic_after_land_restore|L1|32/32|0|0|0|0|0|0|
|edge_dense|clean|baseline|automatic_after_land_restore|L2|22/22|0|0|0|0|0|0|
|edge_dense|clean|current|supplied_hints|L1|32/32|0|0|0|0|0|0|
|edge_dense|clean|current|supplied_hints|L2|22/22|0|0|0|0|0|0|
|edge_dense|clean|current|explicit_land_restore|L1|32/32|0|0|0|0|0|0|
|edge_dense|clean|current|explicit_land_restore|L2|22/22|0|0|0|0|0|0|
|edge_dense|clean|current|automatic_after_land_restore|L1|32/32|0|0|0|0|0|0|
|edge_dense|clean|current|automatic_after_land_restore|L2|22/22|0|0|0|0|0|0|
|edge_dense|damaged|baseline|supplied_hints|L1|28/32|0|0|5986|0|25|0|
|edge_dense|damaged|baseline|supplied_hints|L2|18/22|0|0|137|0|25|0|
|edge_dense|damaged|baseline|explicit_land_restore|L1|32/32|0|5478|508|0|10|0|
|edge_dense|damaged|baseline|explicit_land_restore|L2|20/22|0|0|137|0|10|0|
|edge_dense|damaged|baseline|automatic_after_land_restore|L1|32/32|0|5478|508|0|1|0|
|edge_dense|damaged|baseline|automatic_after_land_restore|L2|21/22|0|78|59|0|1|0|
|edge_dense|damaged|current|supplied_hints|L1|28/32|0|0|5986|0|25|0|
|edge_dense|damaged|current|supplied_hints|L2|18/22|0|0|137|0|25|0|
|edge_dense|damaged|current|explicit_land_restore|L1|32/32|0|5478|508|0|10|0|
|edge_dense|damaged|current|explicit_land_restore|L2|20/22|0|0|137|0|10|0|
|edge_dense|damaged|current|automatic_after_land_restore|L1|32/32|0|5610|376|0|0|0|
|edge_dense|damaged|current|automatic_after_land_restore|L2|22/22|0|80|57|0|0|0|
|edge_dense|severe|baseline|supplied_hints|L1|4/32|0|0|6156|225903|25|189|
|edge_dense|severe|baseline|supplied_hints|L2|4/22|0|0|443|82496|25|189|
|edge_dense|severe|baseline|explicit_land_restore|L1|3/32|0|5465|691|240910|10|216|
|edge_dense|severe|baseline|explicit_land_restore|L2|3/22|0|0|443|95293|10|216|
|edge_dense|severe|baseline|automatic_after_land_restore|L1|3/32|0|5465|691|240910|10|216|
|edge_dense|severe|baseline|automatic_after_land_restore|L2|3/22|0|0|443|95293|10|216|
|edge_dense|severe|current|supplied_hints|L1|4/32|0|0|6156|225903|25|189|
|edge_dense|severe|current|supplied_hints|L2|4/22|0|0|443|82496|25|189|
|edge_dense|severe|current|explicit_land_restore|L1|3/32|0|5465|691|240910|10|216|
|edge_dense|severe|current|explicit_land_restore|L2|3/22|0|0|443|95293|10|216|
|edge_dense|severe|current|automatic_after_land_restore|L1|3/32|0|5465|691|240910|10|216|
|edge_dense|severe|current|automatic_after_land_restore|L2|3/22|0|0|443|95293|10|216|
|center_rows|clean|baseline|supplied_hints|L1|32/32|0|0|0|0|0|0|
|center_rows|clean|baseline|supplied_hints|L2|22/22|0|0|0|0|0|0|
|center_rows|clean|baseline|explicit_land_restore|L1|32/32|0|0|0|0|0|0|
|center_rows|clean|baseline|explicit_land_restore|L2|22/22|0|0|0|0|0|0|
|center_rows|clean|baseline|automatic_after_land_restore|L1|32/32|0|0|0|0|0|0|
|center_rows|clean|baseline|automatic_after_land_restore|L2|22/22|0|0|0|0|0|0|
|center_rows|clean|current|supplied_hints|L1|32/32|0|0|0|0|0|0|
|center_rows|clean|current|supplied_hints|L2|22/22|0|0|0|0|0|0|
|center_rows|clean|current|explicit_land_restore|L1|32/32|0|0|0|0|0|0|
|center_rows|clean|current|explicit_land_restore|L2|22/22|0|0|0|0|0|0|
|center_rows|clean|current|automatic_after_land_restore|L1|32/32|0|0|0|0|0|0|
|center_rows|clean|current|automatic_after_land_restore|L2|22/22|0|0|0|0|0|0|
|center_rows|damaged|baseline|supplied_hints|L1|28/32|0|0|5986|0|25|0|
|center_rows|damaged|baseline|supplied_hints|L2|18/22|0|0|134|0|25|0|
|center_rows|damaged|baseline|explicit_land_restore|L1|32/32|0|5478|508|0|10|0|
|center_rows|damaged|baseline|explicit_land_restore|L2|20/22|0|0|134|0|10|0|
|center_rows|damaged|baseline|automatic_after_land_restore|L1|32/32|0|5478|508|0|1|0|
|center_rows|damaged|baseline|automatic_after_land_restore|L2|21/22|0|78|56|0|1|0|
|center_rows|damaged|current|supplied_hints|L1|28/32|0|0|5986|0|25|0|
|center_rows|damaged|current|supplied_hints|L2|18/22|0|0|134|0|25|0|
|center_rows|damaged|current|explicit_land_restore|L1|32/32|0|5478|508|0|10|0|
|center_rows|damaged|current|explicit_land_restore|L2|20/22|0|0|134|0|10|0|
|center_rows|damaged|current|automatic_after_land_restore|L1|32/32|0|5610|376|0|0|0|
|center_rows|damaged|current|automatic_after_land_restore|L2|22/22|0|82|52|0|0|0|
|center_rows|severe|baseline|supplied_hints|L1|12/32|0|0|6156|141143|26|181|
|center_rows|severe|baseline|supplied_hints|L2|5/22|0|0|403|94931|26|181|
|center_rows|severe|baseline|explicit_land_restore|L1|12/32|0|5465|691|154389|11|207|
|center_rows|severe|baseline|explicit_land_restore|L2|4/22|0|0|403|112524|11|207|
|center_rows|severe|baseline|automatic_after_land_restore|L1|12/32|0|5465|691|154389|11|207|
|center_rows|severe|baseline|automatic_after_land_restore|L2|4/22|0|0|403|112524|11|207|
|center_rows|severe|current|supplied_hints|L1|12/32|0|0|6156|141143|26|181|
|center_rows|severe|current|supplied_hints|L2|5/22|0|0|403|94931|26|181|
|center_rows|severe|current|explicit_land_restore|L1|12/32|0|5465|691|154389|11|207|
|center_rows|severe|current|explicit_land_restore|L2|4/22|0|0|403|112524|11|207|
|center_rows|severe|current|automatic_after_land_restore|L1|12/32|0|5465|691|154389|11|207|
|center_rows|severe|current|automatic_after_land_restore|L2|4/22|0|0|403|112524|11|207|
|center_array|clean|baseline|supplied_hints|L1|32/32|0|0|0|0|0|0|
|center_array|clean|baseline|supplied_hints|L2|22/22|0|0|0|0|0|0|
|center_array|clean|baseline|explicit_land_restore|L1|32/32|0|0|0|0|0|0|
|center_array|clean|baseline|explicit_land_restore|L2|22/22|0|0|0|0|0|0|
|center_array|clean|baseline|automatic_after_land_restore|L1|32/32|0|0|0|0|0|0|
|center_array|clean|baseline|automatic_after_land_restore|L2|22/22|0|0|0|0|0|0|
|center_array|clean|current|supplied_hints|L1|32/32|0|0|0|0|0|0|
|center_array|clean|current|supplied_hints|L2|22/22|0|0|0|0|0|0|
|center_array|clean|current|explicit_land_restore|L1|32/32|0|0|0|0|0|0|
|center_array|clean|current|explicit_land_restore|L2|22/22|0|0|0|0|0|0|
|center_array|clean|current|automatic_after_land_restore|L1|32/32|0|0|0|0|0|0|
|center_array|clean|current|automatic_after_land_restore|L2|22/22|0|0|0|0|0|0|
|center_array|damaged|baseline|supplied_hints|L1|10/32|0|0|5986|168858|25|62|
|center_array|damaged|baseline|supplied_hints|L2|9/22|0|0|134|22984|25|62|
|center_array|damaged|baseline|explicit_land_restore|L1|12/32|0|5478|508|171572|10|68|
|center_array|damaged|baseline|explicit_land_restore|L2|11/22|0|0|134|22984|10|68|
|center_array|damaged|baseline|automatic_after_land_restore|L1|12/32|0|5478|508|171572|10|68|
|center_array|damaged|baseline|automatic_after_land_restore|L2|11/22|0|0|134|22984|10|68|
|center_array|damaged|current|supplied_hints|L1|10/32|0|0|5986|168858|25|62|
|center_array|damaged|current|supplied_hints|L2|9/22|0|0|134|22984|25|62|
|center_array|damaged|current|explicit_land_restore|L1|12/32|0|5478|508|171572|10|68|
|center_array|damaged|current|explicit_land_restore|L2|11/22|0|0|134|22984|10|68|
|center_array|damaged|current|automatic_after_land_restore|L1|12/32|0|5478|508|171572|10|68|
|center_array|damaged|current|automatic_after_land_restore|L2|11/22|0|0|134|22984|10|68|
|center_array|severe|baseline|supplied_hints|L1|5/32|0|0|6156|222758|27|365|
|center_array|severe|baseline|supplied_hints|L2|3/22|0|0|417|112484|27|365|
|center_array|severe|baseline|explicit_land_restore|L1|6/32|0|5465|691|226401|12|419|
|center_array|severe|baseline|explicit_land_restore|L2|4/22|0|0|417|112484|12|419|
|center_array|severe|baseline|automatic_after_land_restore|L1|6/32|0|5465|691|226401|12|419|
|center_array|severe|baseline|automatic_after_land_restore|L2|4/22|0|0|417|112484|12|419|
|center_array|severe|current|supplied_hints|L1|5/32|0|0|6156|222758|27|365|
|center_array|severe|current|supplied_hints|L2|3/22|0|0|417|112484|27|365|
|center_array|severe|current|explicit_land_restore|L1|6/32|0|5465|691|226401|12|419|
|center_array|severe|current|explicit_land_restore|L2|4/22|0|0|417|112484|12|419|
|center_array|severe|current|automatic_after_land_restore|L1|6/32|0|5465|691|226401|12|419|
|center_array|severe|current|automatic_after_land_restore|L2|4/22|0|0|417|112484|12|419|

Pair counts are stack-wide, repeated on each layer row. Per-net assigned/correct/missing/false area and signed area error are in metrics.json, including thin VDD/VDDQ/VSS routes. Automatic effects must be compared against explicit_land_restore, not supplied_hints: known land completion is a separate authorized metadata operation.

Severe image ambiguity, unresolved missing pads, residual opens, false shorts and lost copper are retained as failures. Synthetic evidence is not production PCB/netlist or field validation.

## Isolated current automatic effects

|Layout|Profile|Upper pads before → after auto|Recovered extra px (both layers)|False added extra px|Final pair opens / shorts|
|---|---|---:|---:|---:|---:|
|edge_dense|clean|22 → 22 /22|0|0|0 / 0|
|edge_dense|damaged|20 → 22 /22|212|0|0 / 0|
|edge_dense|severe|3 → 3 /22|0|0|10 / 216|
|center_rows|clean|22 → 22 /22|0|0|0 / 0|
|center_rows|damaged|20 → 22 /22|214|0|0 / 0|
|center_rows|severe|4 → 4 /22|0|0|11 / 207|
|center_array|clean|22 → 22 /22|0|0|0 / 0|
|center_array|damaged|11 → 11 /22|0|0|10 / 68|
|center_array|severe|4 → 4 /22|0|0|12 / 419|

## Original damaged BGA control

|Algorithm|Stage|Upper correct pads|False added px|Recovered px|
|---|---|---:|---:|---:|
|baseline|supplied_hints|33/36|0|0|
|baseline|explicit_land_restore|35/36|0|0|
|baseline|automatic_after_land_restore|35/36|0|0|
|current|supplied_hints|33/36|0|0|
|current|explicit_land_restore|35/36|0|0|
|current|automatic_after_land_restore|36/36|0|1214|
