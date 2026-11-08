"""Dense synthetic ground truth, deliberately separate from observed raster evidence."""

from dataclasses import dataclass

import cv2
import numpy as np
from numpy.typing import NDArray
from PIL import Image, ImageDraw
from scipy import ndimage

Mask = NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class DemoNet:
    name: str
    mask: Mask
    seed: tuple[int, int]


@dataclass(frozen=True, slots=True)
class DenseFixture:
    image: NDArray[np.uint8]
    nets: tuple[DemoNet, ...]
    protected: Mask
    trace_gap: Mask
    plane_hole: Mask
    plane_scratch: Mask
    signal_y: tuple[int, ...]


def dense_fixture(index: int) -> DenseFixture:
    """1200x900 optical example; masks describe pristine intended copper, not inferred truth."""
    height, width = 900, 1200
    yy, xx = np.ogrid[:height, :width]
    signal_y = tuple(180 + 19 * i for i in range(20))
    signals = []
    corridors = np.zeros((height, width), dtype=bool)
    clearance = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))
    offset = 12 if index == 0 else -12
    for i, y in enumerate(signal_y):
        drawing = Image.new("1", (width, height))
        pen = ImageDraw.Draw(drawing)
        points = [(160, y), (350, y), (430, y + offset), (750, y + offset), (830, y), (1040, y)]
        pen.line(points, fill=1, width=(2, 3, 5)[i % 3])
        for cx in (160, 1040):
            pen.ellipse((cx - 2, y - 2, cx + 2, y + 2), fill=1)
        if index == 1:
            pen.rectangle((1007, y - 2, 1013, y + 2), fill=1)
        mask = np.array(drawing, dtype=bool)
        signals.append(DemoNet(f"DQ{i}", mask, (160, y)))
        corridors |= cv2.dilate(mask.astype(np.uint8), clearance).astype(bool)
    protected = (xx - 100) ** 2 + (yy - 700) ** 2 <= 16**2
    planes = []
    for name, top, bottom, seed in (
        ("VSS", 60, 300, (100, 120)),
        ("VDD", 306, 440, (100, 380)),
        ("VDDQ", 446, 840, (100, 650)),
    ):
        plane = (xx >= 60) & (xx < 1140) & (yy >= top) & (yy < bottom)
        plane &= ~corridors & ~protected
        # Boundary-straddling corridors can leave floating slivers; these are not planes.
        labels, _ = ndimage.label(plane)
        plane = labels == labels[seed[1], seed[0]]
        planes.append(DemoNet(name, plane, seed))
    protected |= ((yy >= 300) & (yy < 306) | (yy >= 440) & (yy < 446)) & (xx >= 60) & (xx < 1140)
    signal_union = np.logical_or.reduce([net.mask for net in signals])
    protected &= ~signal_union
    protected |= corridors & ~signal_union & (xx >= 500) & (xx < 540)
    nets = tuple(planes + signals)
    metal = np.logical_or.reduce([net.mask for net in nets])
    trace_gap = np.zeros_like(metal)
    plane_hole = np.zeros_like(metal)
    plane_scratch = np.zeros_like(metal)
    if index == 0:
        trace_gap[:, 620:622] = signals[6].mask[:, 620:622]
        plane_hole[94:100, 86:94] = True
        plane_scratch[60:300, 1090:1092] = True
        metal &= ~(trace_gap | plane_hole | plane_scratch)
    image = np.full((height, width, 3), (20, 23, 27), dtype=np.uint8)
    shade = np.broadcast_to((10 * np.sin(np.arange(width) / 110)).astype(np.int16), metal.shape)
    for channel, base in enumerate((182, 136, 70)):
        image[..., channel][metal] = (base + shade[metal]).astype(np.uint8)
    # Intensity-only polishing marks remain copper; true missing metal is modeled above.
    texture = metal & (((xx + 3 * yy + index * 19) % 173) < 2)
    image[texture] = (128, 100, 50)
    return DenseFixture(image, nets, protected, trace_gap, plane_hole, plane_scratch, signal_y)
