"""Validated transport and persisted project metadata."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pkg_re.ballmaps import validate_grid


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class Point(Input):
    x: float
    y: float


class Ballmap(Input):
    csv: str | None = Field(default=None, max_length=500000)
    grid: list[list[Annotated[str, Field(strict=True, max_length=160)]]] | None = None
    origin: Point
    pitch_px: float = Field(gt=0, le=30000)
    pitch_mm: float = Field(gt=0, le=100)
    radius_px: float = Field(gt=0, le=500)
    restore_missing: bool = False

    @model_validator(mode="after")
    def exactly_one_map(self):
        if (self.csv is None) == (self.grid is None):
            raise ValueError("Provide exactly one of grid or csv")
        if self.grid is not None:
            self.grid = validate_grid(self.grid)
        return self


class Calibration(Input):
    mm_per_pixel: float | None = Field(default=None, gt=0, le=100)
    rotation_deg: float = 0
    mirror_x: bool = False
    offset_x_mm: float = 0
    offset_y_mm: float = 0
    affine: tuple[float, float, float, float, float, float] | None = None

    @model_validator(mode="after")
    def nonsingular(self):
        if self.affine:
            a, b, d, e, _, _ = self.affine
            if abs(a * e - b * d) < 1e-15:
                raise ValueError("Affine transform must be invertible")
        return self


class Marker(Input):
    id: str = Field(min_length=1, max_length=100)
    kind: Literal["ball", "via", "pad", "net"]
    x: float
    y: float
    net: str = Field(default="", max_length=160)
    radius: float = Field(default=4, gt=0, le=500)
    contact_radius: float | None = Field(default=None, gt=0, le=100)
    end_layer_id: str | None = None
    source: Literal["manual", "ocr", "detected", "grid"] = "manual"
    confirmed: bool = False
    bbox: (
        tuple[
            Annotated[int, Field(ge=0, le=30000)],
            Annotated[int, Field(ge=0, le=30000)],
            Annotated[int, Field(gt=0, le=30000)],
            Annotated[int, Field(gt=0, le=30000)],
        ]
        | None
    ) = None
    confidence: float | None = Field(default=None, ge=0, le=100)


class Candidate(Input):
    id: str
    kind: Literal["plane_hole_fill", "reconnect", "short_split"]
    bbox: tuple[int, int, int, int]
    pixels: int
    status: Literal["pending", "accepted", "rejected"] = "pending"
    reason: str
    recommendation: Literal["accept", "reject", "review"] = "review"
    recommendation_reason: str = ""
    hint_nets: list[str] = Field(default_factory=list)
    decision_source: Literal["manual", "automatic"] | None = None
    annotation_overlap: bool | None = None


class Parameters(Input):
    material_mode: Literal["legacy", "red_chroma"] = "legacy"
    chroma_threshold: int = Field(default=14, ge=-255, le=255)
    directional_scratch: bool = False
    threshold: int = Field(default=110, ge=0, le=255)
    max_gap: int = Field(default=4, ge=1, le=20)
    max_hole_area: int = Field(default=200, ge=0, le=10000)


class Analyze(Parameters):
    roi: tuple[int, int, int, int] | None = None
    auto_process: bool = False


class ReviewSummary(Input):
    accepted: int = 0
    rejected: int = 0
    review: int = 0
    source: Literal["manual", "automatic"]


class Layer(Input):
    """Mutable project metadata edited transactionally by the local service."""

    id: str
    name: str
    width: int = Field(gt=0, le=30000)
    height: int = Field(gt=0, le=30000)
    revision: int = 0
    calibration: Calibration = Field(default_factory=Calibration)
    markers: list[Marker] = Field(default_factory=list)
    candidates: list[Candidate] = Field(default_factory=list)
    analyzed: bool = False
    roi: tuple[int, int, int, int] | None = None
    parameters: Parameters = Field(default_factory=Parameters)
    warnings: list[str] = Field(default_factory=list)
    source_sha256: str = ""
    review_summary: ReviewSummary | None = None
    ballmap: Ballmap | None = None

    @model_validator(mode="after")
    def bounded_pixels(self):
        if self.width * self.height > 30_000_000:
            raise ValueError("Image exceeds 30 million pixels")
        return self


class Project(Input):
    """Mutable state is saved atomically after each operation."""

    id: str
    name: str = Field(max_length=200)
    revision: int = 0
    layers: list[Layer] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    version: Literal[1] = 1
    edit_log: list[str] = Field(default_factory=list)


class CreateProject(Input):
    name: str = Field(default="Package reconstruction", min_length=1, max_length=200)
    demo: bool = False
    sample: Literal[
        "dense",
        "bga_clean",
        "bga_damaged",
        "bga_severe",
        "die_edge_dense",
        "die_center_rows",
        "die_center_array",
        "die_weave16",
        "die_weave32",
        "die_micro32",
    ] = "dense"
    damage_profile: Literal["clean", "damaged", "severe", "diagonal"] = "clean"


class Stroke(Input):
    kind: Literal["add", "erase", "protect", "unprotect"]
    points: list[Point] = Field(min_length=1, max_length=10000)
    radius: float = Field(gt=0, le=500)


class Decision(Input):
    id: str
    decision: Literal["accepted", "rejected"]


class BatchDecision(Input):
    ids: list[str] = Field(min_length=1, max_length=200)
    decision: Literal["accepted", "rejected"]
    expected_revision: int = Field(ge=0)


class AutoReview(Input):
    ids: list[str] | None = Field(default=None, min_length=1, max_length=200)
    expected_revision: int = Field(ge=0)


class MarkersInput(Input):
    markers: list[Marker] = Field(max_length=10000)


class Detect(Input):
    ocr: bool = True
    green_markers: bool = True
