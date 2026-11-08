"""Independent dense die geometry; masks are renderer/evaluation truth only."""

from typing import Literal, TypedDict, assert_never

import cv2
import numpy as np

from pkg_re.bga_fixture import NAMES, POWER, SHAPE, BgaFixture, BgaLayer, BgaNet, BgaTerminal, BgaVia

DieLayout = Literal["edge_dense", "center_rows", "center_array"]


class DieMetadata(TypedDict):
    layout: DieLayout
    pad_width_px: int
    pad_height_px: int
    pad_pitch_px: int
    trace_width_px: int
    minimum_gap_px: int
    pad_count: int
    nominal_ball_pitch_mm: float
    plane_area_ratios: dict[str, dict[str, float]]


def die_fixture_metadata(fixture: BgaFixture, layout: DieLayout) -> DieMetadata:
    """Report measured plane proportions rather than imposing the legacy ratio."""
    ratios = {}
    for layer in fixture.layers:
        areas = {n.name: int(n.plane_mask.sum()) for n in layer.nets if n.name in POWER}
        ratios[layer.name] = {name: area / sum(areas.values()) for name, area in areas.items()}
    return {
        "layout": layout,
        "pad_width_px": 6,
        "pad_height_px": 12,
        "pad_pitch_px": 16,
        "trace_width_px": 3,
        "minimum_gap_px": 1 if layout == "center_array" else 2,
        "pad_count": 22,
        "nominal_ball_pitch_mm": fixture.pitch_px * fixture.mm_per_pixel,
        "plane_area_ratios": ratios,
    }


def die_fixture(layout: DieLayout) -> BgaFixture:
    """Build narrow interleaved pad banks and real, isolated two-layer connections."""
    match layout:
        case "edge_dense":
            rows, stagger = (400, 1136), 0
        case "center_rows":
            rows, stagger = (640, 896), 0
        case "center_array":
            rows, stagger = (704, 832), 20
        case unreachable:
            assert_never(unreachable)
    copper = {name: [np.zeros(SHAPE, np.uint8) for _ in range(2)] for name in NAMES}
    planes = {name: [np.zeros(SHAPE, np.uint8) for _ in range(2)] for name in POWER}
    terminals: list[list[BgaTerminal]] = [[], []]
    vias = []
    for row in range(4):
        for col in range(8):
            name = (
                f"DQ{8 + col}"
                if row == 0
                else f"DQ{col}"
                if row == 3
                else "VSS"
                if row == 1
                else "VDDQ"
                if col < 4
                else "VDD"
            )
            x, y = 336 + 160 * col, 528 + 160 * row
            terminals[0].append(BgaTerminal(f"ball-{row + 1}-{col + 1}", "ball", name, x, y, 24))
            cv2.circle(copper[name][0], (x, y), 24, 1, -1)
            if name.startswith("DQ"):
                vy = 64 if row == 0 else 1472
                via = BgaVia(f"via-{name}", name, x, vy, 4)
                vias.append(via)
                cv2.line(copper[name][0], (x, y), (x, vy), 1, 2)
    for bank, (y, first) in enumerate(zip(rows, (8, 0), strict=True)):
        signal = first
        for index in range(11):
            name = {1: "VSS", 5: "VDDQ", 9: "VDD"}.get(index)
            if name is None:
                name = f"DQ{signal}"
                signal += 1
            x = 800 + 16 * index
            py = y + (stagger * (index % 2)) * (1 if bank == 0 else -1)
            terminals[1].append(BgaTerminal(f"pad-{bank + 1}-{index + 1:02d}", "pad", name, x, py, 3))
            copper[name][1][py - 6 : py + 6, x - 3 : x + 3] = 1
            if name.startswith("DQ"):
                via = next(v for v in vias if v.net == name)
                # Short parallel necks make the true narrow trace width directly measurable.
                neck = py - 32 if bank == 0 else py + 32
                cv2.line(copper[name][1], (via.x, via.y), (x, neck), 1, 2)
                cv2.line(copper[name][1], (x, neck), (x, py), 1, 2)
            else:
                turn = py - 24 if bank == 0 else py + 24
                offset = 11 if stagger else 10
                points = np.array([(x, py), (x, turn), (x - offset, turn), (x - offset, 768), (x, 768)])
                cv2.polylines(copper[name][1], [points], False, 1, 2)
    for name, x0, x1 in (("VSS", 780, 836), ("VDDQ", 856, 908), ("VDD", 936, 988)):
        planes[name][1][736:801, x0 : x1 + 1] = 1
        if name == "VSS":
            planes[name][0][650:716, 300:1490] = 1
            planes[name][0][700:801, x0 : x1 + 1] = 1
        else:
            left, right = (300, 917) if name == "VDDQ" else (936, 1490)
            planes[name][0][824:881, left:right] = 1
            planes[name][0][736:850, x0 : x1 + 1] = 1
        for row in range(3):
            for col in range(5):
                vias.append(
                    BgaVia(f"via-{name}-{row * 5 + col:02d}", name, x0 + 6 + col * 10, 746 + row * 18, 3)
                )
    for via in vias:
        for index in range(2):
            cv2.circle(copper[via.net][index], (via.x, via.y), via.radius, 1, -1)
    layers = []
    for index in range(2):
        nets = []
        for name in NAMES:
            features = copper[name][index].astype(bool)
            plane = planes[name][index].astype(bool) & ~features if name in POWER else np.zeros(SHAPE, bool)
            mask = features | plane
            y, x = np.argwhere(mask)[0]
            nets.append(BgaNet(name, mask, plane, (int(x), int(y))))
        layers.append(BgaLayer(f"L{index + 1}", tuple(nets), tuple(terminals[index]), tuple(vias)))
    return BgaFixture((layers[0], layers[1]))
