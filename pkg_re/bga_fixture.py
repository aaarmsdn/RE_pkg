"""Pristine two-layer BGA geometry, kept outside the observation pipeline."""

from dataclasses import dataclass
from heapq import heappop, heappush
from typing import Literal

import cv2
import numpy as np
from numpy.typing import NDArray
from scipy import ndimage

Mask = NDArray[np.bool_]


@dataclass(frozen=True, slots=True)
class BgaTerminal:
    name: str
    kind: Literal["ball", "pad"]
    net: str
    x: int
    y: int
    radius: int


@dataclass(frozen=True, slots=True)
class BgaVia:
    id: str
    net: str
    x: int
    y: int
    radius: int


@dataclass(frozen=True, slots=True)
class BgaNet:
    name: str
    mask: Mask
    plane_mask: Mask
    seed: tuple[int, int]


@dataclass(frozen=True, slots=True)
class BgaLayer:
    name: str
    nets: tuple[BgaNet, ...]
    terminals: tuple[BgaTerminal, ...]
    vias: tuple[BgaVia, ...]


@dataclass(frozen=True, slots=True)
class BgaFixture:
    layers: tuple[BgaLayer, BgaLayer]
    width: int = 1792
    height: int = 1536
    pitch_px: int = 160
    mm_per_pixel: float = 0.03125


POWER = ("VSS", "VDDQ", "VDD")
NAMES = (*POWER, *(f"DQ{i}" for i in range(16)))
SHAPE = (1536, 1792)
STEP = 8
Node = tuple[int, int, int]
Copper = dict[str, list[NDArray[np.uint8]]]


def _route_power(copper: Copper, terminals: list[list[BgaTerminal]], vias: list[BgaVia]) -> None:
    """Route one actual two-layer copper tree per power net on an eight-pixel lattice."""
    clearance = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (31, 31))
    for name in POWER:
        blocked = np.stack(
            [
                cv2.dilate(
                    np.logical_or.reduce([copper[other][layer] for other in NAMES if other != name]).astype(
                        np.uint8
                    ),
                    clearance,
                )[::STEP, ::STEP].astype(bool)
                for layer in range(2)
            ]
        )
        blocked[:, :3] = blocked[:, -3:] = True
        blocked[:, :, :3] = blocked[:, :, -3:] = True
        targets: list[Node] = [
            (layer, terminal.y // STEP, terminal.x // STEP)
            for layer, row in enumerate(terminals)
            for terminal in row
            if terminal.net == name
        ]
        targets += [
            (layer, via.y // STEP, via.x // STEP) for via in vias if via.net == name for layer in range(2)
        ]
        tree = np.zeros_like(blocked)
        tree[targets[-1]] = True
        for start in targets:
            if tree[start]:
                continue
            heuristic = ndimage.distance_transform_cdt(~np.any(tree, axis=0), metric="taxicab")
            distances = np.full(blocked.shape, np.inf)
            distances[start] = 0
            previous: dict[Node, Node] = {}
            queue = [(int(heuristic[start[1:]]), 0, start)]
            end = start
            while queue:
                _, cost, node = heappop(queue)
                if cost != distances[node]:
                    continue
                if tree[node]:
                    end = node
                    break
                z, y, x = node
                for neighbor, step_cost in (
                    ((z, y - 1, x), 1),
                    ((z, y + 1, x), 1),
                    ((z, y, x - 1), 1),
                    ((z, y, x + 1), 1),
                    ((1 - z, y, x), 12),
                ):
                    if blocked[neighbor] or cost + step_cost >= distances[neighbor]:
                        continue
                    distances[neighbor] = cost + step_cost
                    previous[neighbor] = node
                    heappush(
                        queue, (cost + step_cost + int(heuristic[neighbor[1:]]), cost + step_cost, neighbor)
                    )
            if not tree[end]:
                raise RuntimeError(f"Power route unavailable for {name} at {start}")
            path = [end]
            while path[-1] != start:
                path.append(previous[path[-1]])
            for node in path:
                tree[node] = True
            for a, b in zip(path, path[1:], strict=False):
                za, ya, xa = a
                zb, yb, xb = b
                if za == zb:
                    cv2.line(copper[name][za], (xa * STEP, ya * STEP), (xb * STEP, yb * STEP), 1, 5)
                elif not any(v.net == name and v.x == xa * STEP and v.y == ya * STEP for v in vias):
                    via = BgaVia(
                        f"via-{name}-{sum(v.net == name for v in vias):02d}", name, xa * STEP, ya * STEP, 10
                    )
                    vias.append(via)
                    for layer in range(2):
                        cv2.circle(copper[name][layer], (via.x, via.y), via.radius, 1, -1)


def _planes(features: list[Mask]) -> list[Mask]:
    """Grow from routed copper, tune measured areas, and discard unattached islands."""
    keepout = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    boundary = np.zeros(SHAPE, dtype=bool)
    boundary[24:-24, 24:-24] = True
    distances = []
    for index in range(3):
        other = np.logical_or.reduce([mask for j, mask in enumerate(features) if j != index])
        valid = boundary & ~cv2.dilate(other.astype(np.uint8), keepout).astype(bool)
        distance = ndimage.distance_transform_edt(~features[index]).astype(np.float32)
        distance[~valid] = np.inf
        distances.append(distance)
    fields = np.stack(distances)
    offsets = np.zeros(3, dtype=np.float32)
    targets = np.array([0.5, 0.25, 0.25])
    erosion = np.ones((5, 5), dtype=np.uint8)
    best: list[Mask] = []
    best_error = np.inf
    for iteration in range(70):
        assigned = np.argmin(fields + offsets[:, None, None], axis=0)
        available = np.isfinite(np.min(fields, axis=0))
        planes = []
        for index in range(3):
            region = cv2.erode((available & (assigned == index)).astype(np.uint8), erosion).astype(bool)
            labels, _ = ndimage.label(region | features[index])
            attached = np.unique(labels[features[index]])
            connected = np.isin(labels, attached[attached > 0])
            planes.append(region & connected & ~features[index])
        areas = np.array([int(mask.sum()) for mask in planes])
        error = areas / areas.sum() - targets
        magnitude = np.max(np.abs(error))
        if magnitude < best_error:
            best, best_error = planes, magnitude
        if magnitude <= 0.003:
            break
        offsets += (error * (90 / (1 + iteration / 8))).astype(np.float32)
    # A one-pixel edge trim resolves discrete area jumps when a narrow neck closes.
    for index in range(3):
        if best_error <= 0.003:
            break
        region = ndimage.binary_erosion(best[index] | features[index]) | features[index]
        labels, _ = ndimage.label(region)
        attached = np.unique(labels[features[index]])
        plane = np.isin(labels, attached[attached > 0]) & region & ~features[index]
        candidate = [plane if j == index else mask for j, mask in enumerate(best)]
        areas = np.array([int(mask.sum()) for mask in candidate])
        magnitude = np.max(np.abs(areas / areas.sum() - targets))
        if magnitude < best_error:
            best, best_error = candidate, magnitude
    return best


def bga_fixture() -> BgaFixture:
    """Build the deterministic reference stack; no masks are analyzer inputs."""
    copper = {name: [np.zeros(SHAPE, dtype=np.uint8) for _ in range(2)] for name in NAMES}
    terminals: list[list[BgaTerminal]] = [[], []]
    vias: list[BgaVia] = []
    for row in range(4):
        for col in range(8):
            net = (
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
            ball = BgaTerminal(f"ball-{row + 1}-{col + 1}", "ball", net, x, y, 24)
            terminals[0].append(ball)
            cv2.circle(copper[net][0], (x, y), ball.radius, 1, -1)
    for row, (y, first, middle) in enumerate(((112, 8, 2), (1424, 0, 3))):
        pad_specs = [(176, "VDD"), (1616, "VDD")]
        for col in range(8):
            x = 336 + 160 * col
            pad_specs.append((x, f"DQ{first + col}"))
            if col < 7:
                pad_specs.append((x + (56 if col == middle else 80), "VSS" if col % 2 == 0 else "VDDQ"))
                if col == middle:
                    pad_specs.append((x + 104, "VDD"))
        for index, (x, name) in enumerate(sorted(pad_specs)):
            pad = BgaTerminal(f"pad-{row + 1}-{index + 1:02d}", "pad", name, x, y, 16)
            terminals[1].append(pad)
            cv2.rectangle(copper[name][1], (x - 16, y - 32), (x + 16, y + 32), 1, -1)
    for ball in (terminal for terminal in terminals[0] if terminal.net.startswith("DQ")):
        direction = -1 if ball.y < SHAPE[0] // 2 else 1
        via = BgaVia(f"via-{ball.net}", ball.net, ball.x + 40, ball.y + direction * 64, 10)
        vias.append(via)
        cv2.line(copper[ball.net][0], (ball.x, ball.y), (via.x, via.y), 1, 5)
        pad = next(terminal for terminal in terminals[1] if terminal.net == ball.net)
        bend = pad.y - direction * 72
        points = np.array([(via.x, via.y), (via.x, bend - direction * 40), (pad.x, bend), (pad.x, pad.y)])
        cv2.polylines(copper[ball.net][1], [points], False, 1, 5)
        for layer in range(2):
            cv2.circle(copper[ball.net][layer], (via.x, via.y), via.radius, 1, -1)
    for name, origin in (("VSS", (400, 720)), ("VDDQ", (400, 880)), ("VDD", (1040, 880))):
        for row in range(3):
            for col in range(5):
                via = BgaVia(
                    f"via-{name}-{row * 5 + col:02d}", name, origin[0] + col * 64, origin[1] + row * 40, 10
                )
                vias.append(via)
                for layer in range(2):
                    cv2.circle(copper[name][layer], (via.x, via.y), via.radius, 1, -1)
    _route_power(copper, terminals, vias)
    layers = []
    for index in range(2):
        features = [copper[name][index].astype(bool) for name in NAMES]
        planes = _planes(features)
        nets = []
        for position, name in enumerate(NAMES):
            plane = planes[position] if position < 3 else np.zeros(SHAPE, dtype=bool)
            mask = features[position] | plane
            seed_y, seed_x = np.argwhere(features[position])[0]
            nets.append(BgaNet(name, mask, plane, (int(seed_x), int(seed_y))))
        layers.append(BgaLayer(f"L{index + 1}", tuple(nets), tuple(terminals[index]), tuple(vias)))
    return BgaFixture((layers[0], layers[1]))
