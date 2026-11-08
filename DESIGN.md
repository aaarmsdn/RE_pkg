# Package RE workbench design contract

## 1. Reference and intent
Approved concrete reference: `.superpowers/brainstorm/2363-1793956470/content/reconstruction-workbench-v2.html`. Preserve dark engineering workbench, native photo center, layer rail, review inspector, and full-width area table. Primary persona: package engineer reviewing ambiguous copper geometry. No invented precision or demonstration values in real projects.

The 2026-11-08 revision makes actual image input primary. A labeled file input/drop zone starts a new project without replacing saved work. The dashed drop-zone border uses the existing mint/control tokens. Analysis appears before the canvas. Native disclosure controls hold synthetic examples, references, advanced analysis, calibration/ballmap and long warnings. Existing repair selection, NET colors and native-pixel canvas controls remain available.

## 2. Tokens
Background #101419; recessed canvas #0b1015; panels #181e25; controls #232b34; border #303a45; text #edf2f6; muted #a5b2bf; mint accent #a7e5c3; active background #244b3e; copper #c5a36b; warning #efc271; danger #f39991. System sans body 14px/1.5; title 20px; section 15px; micro labels 11px; numeric data tabular/monospace. Spacing scale 4/6/8/12/16/20/24px. Radius 4/6px.

## 3. Geometry
Header and evidence notice above a three-column grid: 220px layer rail, flexible viewport, 320px inspector. Each side panel owns vertical scroll; canvas is a fixed-height work surface with independently transformed native coordinates. Area table owns horizontal overflow. Below 1100px inspector flows below center; below 700px all panels stack, keeping layer/input controls accessible.

## 4. Typography and meaning
Korean workflow labels plus exact engineering terms. Original dimensions always px. Unknown calibration shows px² only. Synthetic projects are explicitly labeled; real input results are algorithm outputs, not ground truth. Pending repairs remain amber and require explicit approval.

## 5. Reusable primitives and states
Button (default, hover, focus-visible, pressed, busy/disabled), Field (label, number/text/select, help), Panel (section title and body), Layer row (active/inactive), Candidate row (pending/accepted/rejected), Status banner (working/error/ready), numeric table (empty/real rows). All controls retain text labels. Error text is persistent until next action. Busy prevents duplicate mutation.

## 6. Motion and interaction
No decorative motion. Hover border transition 120ms; reduced-motion removes transition. Pointer canvas pans with pan tool or middle button, zoom anchors cursor. Brush preview and stored strokes share original-pixel transform. Fit and 100% explicit. Candidate selection fits bbox. Native radius never changes with zoom. Pointer cancel discards unfinished stroke.

## 7. Accessibility
Visible mint focus outlines; every input labeled; native buttons/selects and details summaries; status live regions; text labels accompany color states. Canvas operations also have numeric marker fields and candidate centering; freehand brush requires pointer. No shortcut hijacking when typing. Touch-action none confined to canvas.

## 8. Debt and validation boundaries
Desktop precision editing is primary. Screen-reader equivalent of arbitrary freehand geometry remains unavailable. Real browser integration/visual QA owned by root; build alone is not UI QA. Full MCM/Siwave remain explanatory later-stage text. Minimal dependencies requested: dev instrumentation excluded from production; local developer tools can be opted into separately. No external font, telemetry, or cloud inference.

## Dense review revision
NET mode uses server graph palette only; legend entries pair color with net/status/pixel count and expose pressed selection plus clear selection. Default after first extraction: NET colors. Evidence mode retains observed/inferred overlay; Original hides geometry masks. Protection and proposal toggles remain independent in analysis modes. Color is never a net-classification input.

Repair cards pair numbered pending pins with actual source/proposal crops, minimum 96 native pixels of context. Selected card has mint border, main canvas amber padded bbox and numbered callout. Number discs sit outside the defect bbox with a leader line so narrow gaps remain visible. Overview suppresses colliding numbers; selected pins remain prominent. Signal text appears at 100% zoom or on NET selection, while power labels remain visible. The actual candidate bbox stays visible inside context. Minimum display dimensions prevent 1px repairs disappearing. Click a pin with pan tool or select its card; no destructive action on selection. Layer/reanalysis clears selection. Thumbnails never substitute fabricated geometry for image/mask pixels.

## Bulk and NET-assisted review revision
Candidate selection is independent from focus/zoom. The explicit `후보 선택` tool uses a mint rectangle and mint selected outlines; Shift adds to the selection. Pending checkboxes provide a keyboard alternative. A persistent canvas toolbar shows selection count, grouped decisions, NET automatic processing and a summary of actual decisions. Failed batches preserve selection and change no geometry; one Undo reverses a successful group. Layer/project/regeneration invalidates stale selections.

Automatic recommendations display accept/reject/review with reasons and the contacted NET names. Automatic processing is an explicit button or opt-in analysis setting. Short-split candidates use danger pink and removal wording: approval erases suspected observed bridges without changing the source image. Ambiguous voids, unknown names and unclear cuts remain for human review.
