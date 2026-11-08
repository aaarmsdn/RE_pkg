# Prototype contract v1

All coordinates below are in original image pixels unless named mm. API base `/api`. JSON errors use `{detail: string}`. APIs are synchronous request/response. Server serves built frontend at `/`. One project can have multiple layers. UI uses active project id in localStorage; all state changes persisted server-side.

## JSON representations

`Point = {x:number,y:number}`.

`Calibration = {mm_per_pixel:number|null, rotation_deg:number, mirror_x:boolean, offset_x_mm:number, offset_y_mm:number}`. Rotation/mirror followed by scale and y-axis flip. Optional explicit `affine:[number,number,number,number,number,number]|null` (Shapely order a,b,d,e,tx,ty) overrides similarity. Default scale null.

`Marker = {id:string,kind:'ball'|'via'|'pad'|'net',x:number,y:number,net:string, radius:number, end_layer_id:string|null, source:'manual'|'ocr'|'detected'|'grid', confirmed:boolean}`. radius is geometry only for explicitly restored ball; via marker radius is not drill size. Via originates at containing layer; end layer explicitly specified. `confirmed=false` never supplies net or via graph edges. Optional `bbox:[x,y,w,h]|null` and `confidence:0..100|null` preserve OCR source evidence before ball snap. Optional `contact_radius` is in the source layer's native pixels; its physical footprint is transformed to target layers. A radius touching multiple islands stays unresolved.

`Candidate = {id:string,kind:'plane_hole_fill'|'reconnect'|'short_split',bbox:[x,y,width,height],pixels:number,status:'pending'|'accepted'|'rejected',reason:string}`. Candidates have stored separate masks. Application requires explicit approval or the opt-in NET-guided automatic review. Selection can center canvas via bbox. Candidate IDs regenerated on analyze; accepted additions remain in manual masks and action log. Up to100 review candidates, balanced across hole/reconnect kinds; directional mode prioritizes narrow directional candidates. Ranking is not confidence.

`AreaRow = {layer_id:string,net:string,status:'assigned'|'unassigned'|'conflict',observed_px:number,inferred_px:number,total_px:number,observed_mm2:number|null,inferred_mm2:number|null,total_mm2:number|null,islands:number}`. Conflict net label is joined names. Areas sum accepted mask, not source truth.

`Region = {id:number,net:string,status:'assigned'|'unassigned'|'conflict',pixels:number,bbox:[x,y,w,h]}`. IDs are local to one analysis revision; stable source/edit IDs are separate.

`Layer = {id,name,width,height,image_url,overlay_url,candidate_url,protect_url,revision,calibration,markers:Marker[],candidates:Candidate[],regions:Region[],analyzed:boolean,roi:[x,y,w,h]|null,parameters:{threshold:number,max_gap:number,max_hole_area:number,material_mode:'legacy'|'red_chroma',chroma_threshold:number,directional_scratch:boolean},warnings:string[]}`.

`Project = {id,name,revision,layers:Layer[],areas:AreaRow[],warnings:string[],history_count:number,redo_count:number,ocr_available:boolean,simulation_ready:false}`.

## Routes

- `GET /health` -> `{status:'ok',ocr_available:boolean}`.
- `GET /projects` -> `[{id,name}]`.
- `POST /projects` JSON `{name:string,demo:boolean}` -> Project. Demo creates deterministic two-layer gold/dark image with plane hole/scratch, three close traces, ball pads, via/die markers, scale=0.01 mm/px, net seeds. Unprocessed initial image; user runs Analyze. Demo ground truth is explicit synthetic data.
- `GET /projects/{pid}` -> Project.
- `POST /projects/{pid}/layers` multipart `file`, optional `name` -> Project. Validate PNG/JPEG and max 30M pixels. Adds source. Raw file unchanged; decoded RGB analysis uses EXIF transpose only when present with note.
- `POST /projects/{pid}/references/{reference_id}` -> Project. Allowed ids `pcb_L1..pcb_L4`, `package_fig8`, `package_fig10`, `package_fig12`. Does not fetch online.
- `POST /projects/{pid}/layers/{lid}/analyze` JSON `{threshold:0..255,max_gap:1..20,max_hole_area:0..10000,roi:[x,y,w,h]|null,material_mode:'legacy'|'red_chroma',chroma_threshold:-255..255,directional_scratch:boolean,auto_process:boolean}` -> Project. Analyze native ROI up to 4M pixels. Larger image requires explicit ROI. Threshold is minimum local copper score (0..255), not probability. Outside ROI remains unknown. Existing hand edits retained. Defaults: material_mode=legacy, chroma_threshold=14, directional_scratch=false, auto_process=false. Red chroma uses R-2G+B at native resolution. Optional auto_process runs guarded NET review after candidate generation. Enclosed voids remain review-only, even when surrounded by one NET.
- `POST /projects/{pid}/layers/{lid}/calibration` JSON Calibration -> Project.
- `POST /projects/{pid}/layers/{lid}/stroke` JSON `{kind:'add'|'erase'|'protect',points:Point[],radius:number}` -> Project. Native px radius, brush with round joins. Protect erases metal and prevents future fill. add on protected pixels does not overwrite protection. To remove protection use `{kind:'unprotect',...}`.
- `POST /projects/{pid}/layers/{lid}/candidate` JSON `{id:string,decision:'accepted'|'rejected'}` -> Project. Accept checks protected pixels, conflicting confirmed net contacts reported and blocked (409); region conflicts created manually remain visible. Pending cases remain unknown until review.
- `PUT /projects/{pid}/layers/{lid}/markers` JSON `{markers:Marker[]}` -> Project. Replace explicit marker list; net marker can seed any accepted copper component. No silent nearest copper reassignment.
- `POST /projects/{pid}/layers/{lid}/detect` JSON `{ocr:boolean,green_markers:boolean}` -> Project. Adds unconfirmed suggestions; returns warnings if OCR missing. Suggested labels must be confirmed via markers panel.
- `POST /projects/{pid}/layers/{lid}/ballmap` JSON `{csv:string,origin:Point,pitch_px:number,pitch_mm:number,radius_px:number,restore_missing:boolean}` -> Project. CSV columns `row,col,net,populated`; row/col integer grid offsets, populated 0/1; imported marks are confirmed because explicit user input. Creates only populated sites; adds disk as inferred if restore_missing. Finite positive pitch/radius mandatory. Scale = pitch_mm/pitch_px, validated before save. Previous grid-generated copper is replaced on reapplication; independent manual additions remain. Nonempty existing marker list retained except prior grid marks replaced.
- `POST /projects/{pid}/undo`, `POST /projects/{pid}/redo` -> Project.
- `GET /projects/{pid}/export/{format}` -> attachment; format `json`, `csv`, `svg` (query layer_id), `zip`. JSON includes calibrated physical polygons with holes/markers/net/uncertainty plus metadata; no fabricated MCM. ZIP includes source and all masks plus project metadata for reopen. Unknown scale export stays in px and marks units; calibrated export in mm.
- `POST /projects/import` multipart `file` ZIP -> new Project ID. Never extract paths directly; read only declared safe filenames, validate images/dimensions/models. GUI can reopen server projects via selector or import zip.

The UI must catch HTTP errors, show pending/busy states, and never present fake success for unimplemented routes. Buttons for MCM should be explanatory text, not an enabled export.

## Engine contract (pure Python, core worker ownership)

Package `pkg_re/engine` exports from `__init__.py`:

```python
@dataclass(frozen=True, slots=True)
class SegmentationOptions:
    threshold: int = 110
    max_gap: int = 4
    max_hole_area: int = 200
    material_mode: Literal["legacy", "red_chroma"] = "legacy"
    chroma_threshold: int = 14
    directional_scratch: bool = False

@dataclass(frozen=True, slots=True)
class RepairProposal:
    kind: str  # plane_hole_fill or reconnect
    mask: np.ndarray  # bool, same shape as observed mask
    bbox: tuple[int,int,int,int]
    pixels: int
    reason: str

def segment_copper(image: np.ndarray, options: SegmentationOptions) -> np.ndarray:
    # RGB uint8 HxWx3 -> bool HxW; excludes lime annotation pixels.

def propose_repairs(observed: np.ndarray, protected: np.ndarray, options: SegmentationOptions) -> list[RepairProposal]:
    # Pure proposals, bounded gaps/holes; no mutation. Includes interior holes and narrow reconnect gaps.

def stroke_mask(shape: tuple[int,int], points: list[tuple[float,float]], radius: float) -> np.ndarray:
    # bool mask of brush.

def connected_regions(mask: np.ndarray) -> tuple[np.ndarray,list[RegionInfo]]:
    # 4-neighbor conservative edge contact; labels HxW int, background 0.

@dataclass(frozen=True, slots=True)
class RegionInfo:
    id:int
    pixels:int
    bbox:tuple[int,int,int,int]

def mask_polygons(mask: np.ndarray, affine: tuple[float,float,float,float,float,float] | None = None) -> list[PolygonData]:
    # Exact pixel-cell polygon union, no half-pixel loss; retain holes. Physical affine optional.

@dataclass(frozen=True, slots=True)
class PolygonData:
    exterior:list[tuple[float,float]]
    holes:list[list[tuple[float,float]]]
    area:float
```

Core worker tests segmentation/proposals/pixel geometry. Root owns graph across layers and calibration/determinant area. No engine dependency on API models. Correct proposal ambiguity can be surfaced rather than guaranteed segmentation. Every candidate remains pending and repeatable. Avoid storing one full 4M mask per tiny candidate when possible; cap proposals to 100 ordered by pixel count and report cap in API if reached.

## Net display and spatial review (2026-11-06 revision)

LayerView now exposes `net_overlay_url` and `net_legend:[{net,status,color,pixels,islands}]`. These are derived from accepted graph components each revision, not persisted photometric classes. GET `/projects/{pid}/layers/{lid}/nets.png` returns native RGBA with transparent non-copper. Optional `net` query dims other nets without changing geometry or names. Powers have fixed colors; other names have stable palettes. Unknown is gray; conflict magenta. Candidate numbering is per current layer analysis, matching card, thumbnail and canvas. Reanalysis regenerates candidate ids and selection must clear.
# BGA sample modes

`POST /api/projects` accepts `sample: "dense" | "bga_clean" | "bga_damaged" | "bga_severe"` alongside `demo:true`. Default remains `dense` for existing callers. With `demo:false`, sample does not create geometry or images. Every BGA sample encodes/reopens PNGs, installs known lower-ball grid labels and unnamed via/pad coordinates, and starts with empty observation/inference/protection masks.

Analysis warnings distinguish current-ROI copper coverage above 90% from missing confirmed named seeds. These are inspection prompts, not proof of a segmentation defect or a guessed electrical identity.

## Current photo workflow and review (2026-11-08)

Photo-first UI creates a blank project, then posts the image to its layers endpoint. Upload failure retains that blank project for retry; old projects remain available. No synthesis occurs during ordinary file upload.

`POST /projects` also accepts `die_edge_dense`, `die_center_rows`, `die_center_array`, `die_weave16`, `die_weave32`, `die_micro32`. The `damage_profile` is `clean|damaged|severe|diagonal`; the GUI exposes diagonal for the woven layouts. Woven plane coverage is measured against canvas area excluding original non-plane routing/contact copper, approximately90%. Sample geometry is encoded and re-ingested as PNG with empty masks. Supplied upper contacts are unnamed.

- `POST /projects/{pid}/layers/{lid}/candidates/batch`: `{ids:string[],decision:'accepted'|'rejected',expected_revision:number}`. Validate the combined edit, commit atomically, Undo as one operation.
- `POST /projects/{pid}/layers/{lid}/candidates/auto`: `{ids:string[]|null,expected_revision:number}`. Null targets pending candidates. Re-evaluate after each accepted geometry change; reject different-NET joins, retain ambiguous candidates.
- `POST /projects/{pid}/layers/{lid}/candidates/evaluate`: refresh recommendations and weak-short split proposals without applying geometry.

Candidates include `recommendation`, `recommendation_reason`, `hint_nets`, `decision_source`, and `annotation_overlap`. A `short_split` approval removes copper; ordinary repair approval adds copper. Large/strong shorts are not silently partitioned. All modes keep enclosed voids for explicit review: same-NET boundaries and narrow shape alone do not prove damage.
