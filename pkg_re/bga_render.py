"""Repeatable optical corruption of reference copper; never used for inference."""

from dataclasses import dataclass
from typing import Literal, assert_never

import cv2
import numpy as np
from numpy.typing import NDArray
from scipy import ndimage

from pkg_re.bga_fixture import BgaLayer

Profile = Literal["clean", "damaged", "severe", "diagonal"]


@dataclass(frozen=True, slots=True)
class DamageEvent:
    kind: str
    bbox: tuple[int, int, int, int]
    removed_px: int
    note: str


@dataclass(frozen=True, slots=True)
class RenderedLayer:
    image: NDArray[np.uint8]
    removed: NDArray[np.bool_]
    faded_gap: NDArray[np.bool_]
    events: tuple[DamageEvent, ...]


def render_layer(layer: BgaLayer, profile: Profile, index: int) -> RenderedLayer:
    """Apply damage before PNG encoding, preserving separate evaluation truth."""
    copper = np.logical_or.reduce([net.mask for net in layer.nets])
    height, width = copper.shape
    removed = np.zeros_like(copper)
    faded_gap = np.zeros_like(copper)
    events: list[DamageEvent] = []

    def remove(kind: str, patch: NDArray[np.bool_], note: str) -> None:
        selected = patch & copper
        yy, xx = np.where(selected)
        if len(xx):
            removed[:] |= selected
            events.append(
                DamageEvent(
                    kind,
                    (
                        int(xx.min()),
                        int(yy.min()),
                        int(xx.max() - xx.min() + 1),
                        int(yy.max() - yy.min() + 1),
                    ),
                    int(selected.sum()),
                    note,
                )
            )

    match profile:
        case "clean":
            sigma, blur, fade = 0.0, 0.0, 0.0
        case "damaged":
            sigma, blur, fade = 4.0, 0.55, 0.25
        case "diagonal":
            sigma, blur, fade = 4.0, 0.55, 0.0
            yy, xx = np.ogrid[:height, :width]
            remove("diagonal_scratch", (2 * yy - xx + 31) % 181 < 7, "Uniform parallel full-frame scratches")
        case "severe":
            sigma, blur, fade = 9.0, 1.15, 0.70
        case unreachable:
            assert_never(unreachable)
    if profile in {"damaged", "severe"}:
        for terminal in layer.terminals:
            if terminal.kind != "ball" or terminal.net not in {"DQ2", "DQ5", "VSS", "VDDQ"}:
                continue
            kind = "missing_ball" if terminal.net in {"DQ2", "VSS"} else "half_ball"
            if any(e.kind == kind and e.note == terminal.net for e in events):
                continue
            patch = np.zeros_like(copper, dtype=np.uint8)
            cv2.circle(patch, (terminal.x, terminal.y), terminal.radius, 1, -1)
            if kind == "half_ball":
                patch[:, : terminal.x] = 0
            remove(kind, patch.astype(bool), terminal.net)
        for net in layer.nets:
            if not net.plane_mask.any():
                continue
            distance = ndimage.distance_transform_edt(net.plane_mask)
            y, x = np.unravel_index(np.argmax(distance), distance.shape)
            radius = int(distance[y, x])
            length = max(4, min(100, radius - 2))
            patch = np.zeros_like(copper)
            patch[max(0, y - 1) : y + 1, max(0, x - length) : min(width, x + length)] = True
            remove("plane_scratch", patch, net.name)
            patch[:] = False
            patch[max(0, y + 7) : min(height, y + 13), max(0, x - 4) : x + 4] = True
            remove("plane_hole", patch, net.name)
        # A thin trace interruption, selected from geometry only to construct the test input.
        for net in layer.nets:
            if net.name != "DQ6":
                continue
            ys, xs = np.where(net.mask)
            x, y = int(np.median(xs)), int(np.median(ys))
            candidates = np.argmin((xs - x) ** 2 + (ys - y) ** 2)
            x, y = int(xs[candidates]), int(ys[candidates])
            patch = np.zeros_like(copper)
            patch[max(0, y - 1) : y + 1, max(0, x - 12) : min(width, x + 13)] = True
            remove("trace_gap", patch, net.name)
        signals = (
            np.logical_or.reduce([n.mask for n in layer.nets if n.name.startswith("DQ")])
            if any(n.name.startswith("DQ") for n in layer.nets)
            else np.zeros_like(copper)
        )
        near_signals = cv2.dilate(signals.astype(np.uint8), np.ones((11, 11), np.uint8)).astype(bool)
        faded_gap = near_signals & ~copper
        faded_gap[:, : width // 3] = False
        faded_gap[:, 2 * width // 3 :] = False
        if faded_gap.any():
            yy, xx = np.where(faded_gap)
            events.append(
                DamageEvent(
                    "faded_gap",
                    (
                        int(xx.min()),
                        int(yy.min()),
                        int(xx.max() - xx.min() + 1),
                        int(yy.max() - yy.min() + 1),
                    ),
                    0,
                    "Optical gap contrast reduced; intended copper geometry unchanged.",
                )
            )
    yy, xx = np.ogrid[:height, :width]
    lighting = 1 + 0.09 * np.sin(xx / 143) + 0.05 * np.cos(yy / 97)
    rgb = np.full((height, width, 3), (19, 21, 25), dtype=np.float32)
    visible = copper & ~removed
    metal = np.array([184, 139, 70], dtype=np.float32)
    rgb[visible] = metal * np.broadcast_to(lighting, copper.shape)[visible, None]
    rgb[faded_gap] = np.array([19, 21, 25]) * (1 - fade) + metal * fade
    if blur:
        rgb = cv2.GaussianBlur(rgb, (0, 0), blur)
        rng = np.random.default_rng(20261106 + index)
        rgb += rng.normal(0, sigma, rgb.shape).astype(np.float32)
    return RenderedLayer(np.clip(rgb, 0, 255).astype(np.uint8), removed, faded_gap, tuple(events))
