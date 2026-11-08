"""Native-resolution engine value types."""

from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray

Mask = NDArray[np.bool_]
Bounds = tuple[int, int, int, int]
Affine = tuple[float, float, float, float, float, float]


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
    """Keep a local patch; materialize the public full mask only when consumed."""

    kind: Literal["plane_hole_fill", "reconnect"]
    bbox: Bounds
    pixels: int
    reason: str
    _patch: Mask
    _shape: tuple[int, int]

    @property
    def mask(self) -> Mask:
        result = np.zeros(self._shape, dtype=bool)
        x, y, width, height = self.bbox
        result[y : y + height, x : x + width] = self._patch
        return result


@dataclass(frozen=True, slots=True)
class RegionInfo:
    id: int
    pixels: int
    bbox: Bounds


@dataclass(frozen=True, slots=True)
class PolygonData:
    exterior: list[tuple[float, float]]
    holes: list[list[tuple[float, float]]]
    area: float
