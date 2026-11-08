"""Connected evaluation pours; routing/contact copper remains non-plane geometry."""

from dataclasses import replace
from typing import TypedDict

import cv2
import numpy as np
from scipy import ndimage

from pkg_re.bga_fixture import POWER, BgaLayer, Mask


class PlaneMetrics(TypedDict):
    layer: str
    plane_area_px: int
    nonplane_area_px: int
    available_area_px: int
    coverage_fraction: float
    net_plane_area_px: dict[str, int]
    net_plane_share: dict[str, float]


def plane_metrics(layer: BgaLayer) -> PlaneMetrics:
    """Measure all canvas pixels except original non-plane routing/contact copper."""
    plane = np.logical_or.reduce([n.plane_mask for n in layer.nets])
    nonplane = np.logical_or.reduce([n.mask & ~n.plane_mask for n in layer.nets])
    area = int(plane.sum())
    available = plane.size - int(nonplane.sum())
    per_net = {n.name: int(n.plane_mask.sum()) for n in layer.nets if n.name in POWER}
    return PlaneMetrics(
        layer=layer.name,
        plane_area_px=area,
        nonplane_area_px=int(nonplane.sum()),
        available_area_px=available,
        coverage_fraction=area / available,
        net_plane_area_px=per_net,
        net_plane_share={name: count / area for name, count in per_net.items()},
    )


def _extend_source(layer: BgaLayer) -> BgaLayer:
    """Reach open outer corridors with connected copper belonging to the pour."""
    paths = (
        [("VSS", [(64, 320), (64, 32), (1770, 32), (1770, 1500)])]
        if layer.name == "L1"
        else [
            ("VDDQ", [(896, 768), (1740, 768), (1740, 1500)]),
            ("VSS", [(800, 704), (800, 740), (1770, 740), (1770, 1500)]),
        ]
    )
    for name, points in paths:
        other = np.logical_or.reduce([n.mask for n in layer.nets if n.name != name])
        forbidden = cv2.dilate(other.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        extension = np.zeros_like(other, dtype=np.uint8)
        cv2.polylines(extension, [np.array(points, np.int32)], False, 1, 1, cv2.LINE_4)
        addition = extension.astype(bool) & ~forbidden
        nets = tuple(
            replace(n, mask=n.mask | addition, plane_mask=n.plane_mask | (addition & ~n.mask))
            if n.name == name
            else n
            for n in layer.nets
        )
        layer = replace(layer, nets=nets)
    return layer


def pour_planes(layer: BgaLayer) -> BgaLayer:
    """Partition available dielectric by nearest power copper, retaining rooted pours."""
    layer = _extend_source(layer)
    powers = [n for n in layer.nets if n.name in POWER]
    original = np.logical_or.reduce([n.mask for n in layer.nets])
    distances = np.stack([ndimage.distance_transform_edt(~n.mask) for n in powers])
    # Fixed geometric weights balance the three existing connected source trees.
    weights = (1.0, 1.0521, 1.1682) if layer.name == "L1" else (1.0, 1.0413, 1.1458)
    owner = np.argmin(distances * np.asarray(weights)[:, None, None], axis=0)
    del distances
    height, width = original.shape
    yy, xx = np.ogrid[:height, :width]
    border_distance = np.minimum(np.minimum(yy, height - 1 - yy), np.minimum(xx, width - 1 - xx))
    protected = np.zeros_like(original)
    # Keep pad dimensions and the isolated test feeder observable after pouring.
    for pad in layer.terminals:
        if pad.kind == "pad":
            protected[pad.y - 9 : pad.y + 10, pad.x - 8 : pad.x + 9] = True
    protected[550:855, 802:910] = True
    candidates: list[Mask] = []
    for index, net in enumerate(powers):
        other = np.logical_or.reduce([n.mask for n in layer.nets if n.name != net.name])
        forbidden = cv2.dilate(other.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        territory = owner == index
        territory = cv2.erode(territory.astype(np.uint8), np.ones((3, 3), np.uint8)).astype(bool)
        candidates.append(territory & ~forbidden & ~protected & ~original)

    def build(margin: int) -> BgaLayer:
        nets = list(layer.nets)
        for index, net in enumerate(powers):
            addition = candidates[index] & (border_distance >= margin)
            labels, _ = ndimage.label(addition | net.mask)
            root = labels[net.seed[1], net.seed[0]]
            addition &= labels == root
            nets[index] = replace(net, mask=net.mask | addition, plane_mask=net.plane_mask | addition)
        return replace(layer, nets=tuple(nets))

    # A weighted Euclidean cell can be cut by a preserved route. Reassign such
    # orphan dielectric through free space to a physically connected source.
    rooted = build(0)
    target = {"VSS": 0.5, "VDDQ": 0.25, "VDD": 0.25}
    metrics = plane_metrics(rooted)
    order = sorted(
        range(3), key=lambda i: metrics["net_plane_share"][powers[i].name] - target[powers[i].name]
    )
    rooted_masks = [n.mask.copy() for n in rooted.nets[:3]]
    signals = np.logical_or.reduce([n.mask for n in layer.nets if n.name not in POWER])
    for index in order:
        other = signals | np.logical_or.reduce([m for i, m in enumerate(rooted_masks) if i != index])
        forbidden = cv2.dilate(other.astype(np.uint8), np.ones((5, 5), np.uint8)).astype(bool)
        allowed = (~forbidden & ~protected) | rooted_masks[index]
        rooted_masks[index] = ndimage.binary_propagation(rooted_masks[index], mask=allowed)
        candidates[index] = rooted_masks[index] & ~original

    low, high = 0, min(height, width) // 2
    best = build(0)
    best_error = abs(plane_metrics(best)["coverage_fraction"] - 0.9)
    while low <= high:
        mid = (low + high) // 2
        proposed = build(mid)
        coverage = plane_metrics(proposed)["coverage_fraction"]
        error = abs(coverage - 0.9)
        if error < best_error:
            best, best_error = proposed, error
        if coverage > 0.9:
            low = mid + 1
        else:
            high = mid - 1
    return best
