"""Pure native-resolution image and geometry engine."""

from .geometry import mask_polygons
from .masks import connected_regions, segment_copper, stroke_mask
from .repairs import propose_repairs
from .types import PolygonData, RegionInfo, RepairProposal, SegmentationOptions

__all__ = [
    "PolygonData",
    "RegionInfo",
    "RepairProposal",
    "SegmentationOptions",
    "connected_regions",
    "mask_polygons",
    "propose_repairs",
    "segment_copper",
    "stroke_mask",
]
