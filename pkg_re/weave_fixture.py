"""Engineered, planar meanders and four dense pad banks; evaluation truth only."""

from dataclasses import dataclass
from typing import Literal, TypedDict, assert_never

import cv2
import numpy as np
from scipy import ndimage

from pkg_re.bga_fixture import POWER, SHAPE, BgaFixture, BgaLayer, BgaNet, BgaTerminal, BgaVia
from pkg_re.weave_planes import PlaneMetrics, plane_metrics, pour_planes

WeaveLayout = Literal["weave16", "weave32", "micro32"]
Point = tuple[int, int]


class WeaveMetadata(TypedDict):
    layout: str
    plane_layers: list[PlaneMetrics]
    signal_count: int
    ball_count: int
    pad_count: int
    pad_width_px: int
    pad_height_px: int
    pad_pitch_px: int
    trace_width_px: int
    minimum_gap_px: int
    pad_bounds: list[int]
    mapping: list[dict[str, str | int]]
    mapping_order_inversions: int
    minimum_signal_bends: int
    signal_route_lengths_px: dict[str, int]


def _dimensions(layout: WeaveLayout) -> tuple[int, int, int, int, int]:
    match layout:
        case "weave16":
            return 16, 4, 8, 10, 3
        case "weave32":
            return 32, 4, 8, 10, 3
        case "micro32":
            return 32, 2, 4, 6, 1
        case unreachable:
            assert_never(unreachable)


@dataclass(frozen=True, slots=True)
class _Signal:
    name: str
    ball: Point
    via: Point
    pad: Point
    lower: tuple[Point, ...]
    upper: tuple[Point, ...]


def _signals(layout: WeaveLayout) -> list[_Signal]:
    count, _, _, pitch, _ = _dimensions(layout)
    rows = count // 4
    result = []
    for group in range(4):
        right, bottom = group % 2, group // 2
        for rank in range(rows):
            name = f"DQ{((group * rows + rank) * 13 + 7) % count}"
            swapped = count == 32
            via_rank = rank ^ 1 if swapped else rank
            x = (
                128 + (rank // 2 % 2) * 64 + (rank % 2) * 192
                if swapped
                else 128 + ((rank * 3 + group) % 5) * 64
            )
            base_y = 960 if bottom else 128
            y = base_y + rank * 64
            via_y = base_y + via_rank * 64
            via_x = 620
            pad_x = 866
            pad_y = (850 if bottom else 610) + via_rank * pitch - right * 30
            lower: list[Point] = [(x, y)]
            corridor_y = y + (88 if rank % 2 == 0 else -88) if swapped else y
            excursion = 3 if swapped else 12
            if swapped:
                # Wrap outside the adjacent ball, reversing physical endpoint order.
                lower.append((x, corridor_y))
            for step in range(1, 7):
                xx = x + (via_x - x) * step // 7
                yy = corridor_y + (excursion if step % 2 else -excursion)
                lower.extend([(xx, lower[-1][1]), (xx, yy)])
            lower.extend([(via_x, lower[-1][1]), (via_x, via_y)])
            upper: list[Point] = [(via_x, via_y)]
            # Ordered ribbons retain planar rank while compressing toward the die.
            for step in range(1, 25):
                xx = via_x + (pad_x - via_x) * step // 24
                fraction = 1 - (1 - step / 24) ** 2
                yy = round(via_y + (pad_y - via_y) * fraction)
                yy += round(12 * np.sin(step * np.pi / 2)) if step < 16 else 0
                upper.append((xx, yy))
            if right:
                x = 1792 - x
                via_x = 1792 - via_x
                pad_x = 1792 - pad_x
                lower = [(1792 - xx, yy) for xx, yy in lower]
                upper = [(1792 - xx, yy) for xx, yy in upper]
            result.append(_Signal(name, (x, y), (via_x, via_y), (pad_x, pad_y), tuple(lower), tuple(upper)))
    return result


def weave_fixture(layout: WeaveLayout) -> BgaFixture:
    """Build native raster copper with one physical via per signal."""
    count, width, height, _, trace = _dimensions(layout)
    names = (*POWER, *(f"DQ{i}" for i in range(count)))
    copper = {name: [np.zeros(SHAPE, np.uint8) for _ in range(2)] for name in names}
    planes = {name: [np.zeros(SHAPE, bool) for _ in range(2)] for name in names}
    terminals: list[list[BgaTerminal]] = [[], []]
    vias: list[BgaVia] = []
    for signal in _signals(layout):
        bx, by = signal.ball
        vx, vy = signal.via
        px, py = signal.pad
        terminals[0].append(BgaTerminal(f"ball-{signal.name}", "ball", signal.name, bx, by, 16))
        terminals[1].append(
            BgaTerminal(f"pad-{len(terminals[1]):03d}", "pad", signal.name, px, py, width // 2)
        )
        vias.append(BgaVia(f"via-{len(vias):03d}", signal.name, vx, vy, 5))
        for z, points in enumerate((signal.lower, signal.upper)):
            cv2.polylines(
                copper[signal.name][z],
                [np.array(points, np.int32)],
                False,
                1,
                trace if trace == 1 else 2,
                lineType=cv2.LINE_4,
            )
            cv2.circle(copper[signal.name][z], signal.via, 5, 1, -1)
        cv2.circle(copper[signal.name][0], signal.ball, 16, 1, -1)
        copper[signal.name][1][py - height // 2 : py + height // 2, px - width // 2 : px + width // 2] = 1
    for index, name in enumerate(POWER):
        y = 704 + index * 64
        for z in range(2):
            copper[name][z][y - 12 : y + 13, 40:801] = 1
            planes[name][z][y - 12 : y + 13, 40:801] = True
            cv2.line(copper[name][z], (800, y), (896, y), 1, 1, cv2.LINE_4)
        for rank in range(15):
            via = BgaVia(f"via-{len(vias):03d}", name, 64 + rank * 48, y, 5)
            vias.append(via)
            for z in range(2):
                cv2.circle(copper[name][z], (via.x, via.y), via.radius, 1, -1)
        for rank in range(4):
            x = 192 + 192 * rank
            terminals[0].append(BgaTerminal(f"ball-{name}-{rank}", "ball", name, x, y, 16))
            cv2.circle(copper[name][0], (x, y), 16, 1, -1)
        terminals[1].append(BgaTerminal(f"pad-{len(terminals[1]):03d}", "pad", name, 896, y, width // 2))
        copper[name][1][y - height // 2 : y + height // 2, 896 - width // 2 : 896 + width // 2] = 1
    # Extra power balls share signal rows on the same 64px ball lattice.
    for name, point, path in (
        ("VSS", (64, 320), [(64, 320), (64, 704)]),
        ("VDDQ", (1728, 384), [(1728, 384), (1728, 768), (800, 768)]),
        ("VDD", (64, 1152), [(64, 1152), (20, 1152), (20, 832), (40, 832)]),
    ):
        terminals[0].append(BgaTerminal(f"ball-{name}-outer", "ball", name, *point, 16))
        cv2.polylines(copper[name][0], [np.array(path, np.int32)], False, 1, 2, cv2.LINE_4)
        cv2.circle(copper[name][0], point, 16, 1, -1)
    # A thin VSS branch passes two empty pixels from the final upper-left pad.
    last_pad = max((s.pad for s in _signals(layout)[: count // 4]), key=lambda p: p[1])
    near_y = last_pad[1] + height // 2 + 2
    cv2.polylines(
        copper["VSS"][1], [np.array([(840, 704), (840, near_y), (880, near_y)])], False, 1, 1, cv2.LINE_4
    )
    layers = []
    for z in range(2):
        nets = []
        for name in names:
            mask = copper[name][z].astype(bool)
            yy, xx = np.where(mask)
            nets.append(BgaNet(name, mask, planes[name][z], (int(xx[0]), int(yy[0]))))
        layers.append(pour_planes(BgaLayer(f"L{z + 1}", tuple(nets), tuple(terminals[z]), tuple(vias))))
    return BgaFixture((layers[0], layers[1]), pitch_px=64, mm_per_pixel=5 / 64)


def weave_metadata(fixture: BgaFixture, layout: WeaveLayout) -> WeaveMetadata:
    """Report mapping and measured minimum raster clearance, never inference input."""
    count, width, height, pitch, trace = _dimensions(layout)
    pads = fixture.layers[1].terminals
    balls = fixture.layers[0].terminals
    mapping = []
    for pad in pads:
        for ball in balls:
            if ball.net == pad.net:
                mapping.append(
                    dict(
                        net=pad.net,
                        ball=ball.name,
                        ball_x=ball.x,
                        ball_y=ball.y,
                        pad=pad.name,
                        pad_x=pad.x,
                        pad_y=pad.y,
                    )
                )
    signals = _signals(layout)
    lower_order = [s.name for s in sorted(signals, key=lambda s: (s.ball[1], s.ball[0]))]
    upper_order = [s.name for s in sorted(signals, key=lambda s: (s.pad[1], s.pad[0]))]
    ranks = [upper_order.index(name) for name in lower_order]
    inversions = sum(a > b for i, a in enumerate(ranks) for b in ranks[i + 1 :])
    minimum = fixture.width
    for layer in fixture.layers:
        occupied = np.logical_or.reduce([net.mask for net in layer.nets])
        for net in layer.nets:
            distance = ndimage.distance_transform_cdt(~net.mask, metric="chessboard")
            minimum = min(minimum, int(distance[occupied & ~net.mask].min()) - 1)
    return WeaveMetadata(
        layout=layout,
        plane_layers=[plane_metrics(layer) for layer in fixture.layers],
        signal_count=count,
        ball_count=len(balls),
        pad_count=len(pads),
        pad_width_px=width,
        pad_height_px=height,
        pad_pitch_px=pitch,
        trace_width_px=trace,
        minimum_gap_px=minimum,
        pad_bounds=[
            min(t.x for t in pads) - width // 2,
            min(t.y for t in pads) - height // 2,
            max(t.x for t in pads) + width // 2,
            max(t.y for t in pads) + height // 2,
        ],
        mapping=mapping,
        mapping_order_inversions=inversions,
        minimum_signal_bends=min(
            sum(
                (b[0] - a[0]) * (c[1] - b[1]) != (b[1] - a[1]) * (c[0] - b[0])
                for a, b, c in zip(s.lower, s.lower[1:], s.lower[2:], strict=False)
            )
            for s in signals
        ),
        signal_route_lengths_px={
            s.name: sum(
                abs(a[0] - b[0]) + abs(a[1] - b[1])
                for route in (s.lower, s.upper)
                for a, b in zip(route, route[1:], strict=False)
            )
            for s in signals
        },
    )
