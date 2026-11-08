# Dense net visualization and spatial repair review

User requested direct revisions to approved prototype: locate repairs visually, show assigned nets by color, mandatory VSS/VDD/VDDQ and >=16 parallel signals with interleaved plane-connected thin power/ground conductors.

Implementation choices: existing masks/graph remain authoritative. Add a graph-derived net PNG and matching legend; no net identity fabricated from image color. Unknown gray, conflict magenta. Selected-net emphasis is visual only. Candidate thumbnails, numbered pins and selected bbox share native coordinates. Dense synthetic sample remains labeled synthetic and does not overwrite old projects.

## Contract additions
- `LayerView.net_overlay_url`: `/api/projects/{pid}/layers/{lid}/nets.png?revision=...`.
- `LayerView.net_legend`: array `{net:string,status:'assigned'|'unassigned'|'conflict',color:'#rrggbb',pixels:number,islands:number}` for active accepted geometry, grouped by net/status.
- PNG endpoint optional `net` query: selected net fully opaque, other nets dimmed. Matching legend color remains fixed by net across layers/revisions; filter changes no data.

## Work
- Root: graph-derived palette/PNG endpoint and tests for exact pixel ownership, unknown/conflict, stable colors, filter no mutation; integration/browser QA and docs.
- UI worker: frontend source only. Color mode, legend/highlight; spatial numbered repair cards with source/proposal thumbnail and selected highlight on main canvas. Keep brush/provenance modes and view reset; clear stale selection on layer/reanalysis.
- Demo worker: images.py plus optional focused demo module/tests. >=16 parallel thin signals, three powers, narrow connected fingers between signal bundles and surrounding broad planes, realistic intentional clearances/voids plus known scratches/holes. Test no unintended shorts in pristine truth, dense spacing, all required seeded nets after extraction, and bounded proposals.
- Verify full Python/TypeScript/build, real-browser dense sample analyze/color legend/candidate selection/zoom and approvals; record actual limits.
