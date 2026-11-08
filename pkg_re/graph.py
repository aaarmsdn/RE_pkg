"""Connected copper graph, physical via contacts, and per-net planar areas."""

import math
from dataclasses import dataclass
from typing import Literal

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, Field

from pkg_re.engine import connected_regions
from pkg_re.models import Calibration, Layer, Marker, Project
from pkg_re.net_colors import net_color
from pkg_re.store import State, Store

Status = Literal["assigned", "unassigned", "conflict"]


class RegionView(BaseModel):
    id: int
    net: str
    status: Status
    pixels: int
    bbox: tuple[int, int, int, int]


class AreaRow(BaseModel):
    layer_id: str
    net: str
    status: Status
    observed_px: int = 0
    inferred_px: int = 0
    total_px: int = 0
    observed_mm2: float | None = None
    inferred_mm2: float | None = None
    total_mm2: float | None = None
    islands: int = 0


class NetLegend(BaseModel):
    net: str
    status: Status
    color: str
    pixels: int
    islands: int


class LayerView(Layer):
    image_url: str
    overlay_url: str
    candidate_url: str
    protect_url: str
    net_overlay_url: str
    net_legend: list[NetLegend] = Field(default_factory=list)
    regions: list[RegionView] = Field(default_factory=list)


class ProjectView(Project):
    layers: list[LayerView]
    areas: list[AreaRow]
    history_count: int
    redo_count: int
    ocr_available: bool
    simulation_ready: Literal[False] = False


@dataclass(frozen=True, slots=True)
class GraphResult:
    regions: dict[str, list[RegionView]]
    labels: dict[str, NDArray[np.int32]]
    areas: list[AreaRow]
    warnings: list[str]


def affine_for(calibration: Calibration) -> tuple[float, float, float, float, float, float] | None:
    if calibration.affine is not None:
        return calibration.affine
    if calibration.mm_per_pixel is None:
        return None
    c = calibration
    angle = math.radians(c.rotation_deg)
    s, m = c.mm_per_pixel, -1 if c.mirror_x else 1
    return (
        s * m * math.cos(angle),
        s * math.sin(angle),
        s * m * math.sin(angle),
        -s * math.cos(angle),
        c.offset_x_mm,
        c.offset_y_mm,
    )


def contact(labels: NDArray[np.int32], marker: Marker, metric: NDArray[np.float64] | None = None) -> int:
    x, y = int(math.floor(marker.x)), int(math.floor(marker.y))
    h, w = labels.shape
    if not 0 <= x < w or not 0 <= y < h:
        return 0
    center = int(labels[y, x])
    if center or marker.contact_radius is None:
        return center
    metric = np.eye(2) if metric is None else metric
    r = min(max(h, w), int(math.ceil(marker.contact_radius / np.linalg.svd(metric, compute_uv=False)[-1])))
    x0, x1, y0, y1 = max(0, x - r), min(w, x + r + 1), max(0, y - r), min(h, y + r + 1)
    yy, xx = np.ogrid[y0:y1, x0:x1]
    dx, dy = xx - marker.x, yy - marker.y
    distance = (metric[0, 0] * dx + metric[0, 1] * dy) ** 2 + (metric[1, 0] * dx + metric[1, 1] * dy) ** 2
    found = np.unique(labels[y0:y1, x0:x1][distance <= marker.contact_radius**2])
    values = found[found > 0]
    return int(values[0]) if len(values) == 1 else 0


def analyze_graph(state: State) -> GraphResult:
    labels, components, parents = {}, {}, {}
    warnings = []
    for layer in state.project.layers:
        labels[layer.id], components[layer.id] = connected_regions(state.pixels[layer.id].accepted())
        for region in components[layer.id]:
            key = (layer.id, region.id)
            parents[key] = key

    def root(key: tuple[str, int]) -> tuple[str, int]:
        while parents[key] != key:
            parents[key] = parents[parents[key]]
            key = parents[key]
        return key

    def join(keys: list[tuple[str, int]]) -> None:
        for key in keys[1:]:
            parents[root(key)] = root(keys[0])

    layers = state.project.layers
    positions = {layer.id: i for i, layer in enumerate(layers)}
    for layer in layers:
        for marker in layer.markers:
            if not marker.confirmed or marker.kind != "via" or not marker.end_layer_id:
                continue
            start, end = positions[layer.id], positions.get(marker.end_layer_id, -1)
            transform = affine_for(layer.calibration)
            if end < 0 or transform is None:
                warnings.append(f"Via {marker.id}: span/physical calibration missing")
                continue
            a, b, d, e, tx, ty = transform
            world = np.array([a * marker.x + b * marker.y + tx, d * marker.x + e * marker.y + ty])
            keys = []
            endpoint_ids = set()
            for target in layers[min(start, end) : max(start, end) + 1]:
                target_matrix = affine_for(target.calibration)
                if target_matrix is None:
                    continue
                ta, tb, td, te, ttx, tty = target_matrix
                xy = np.linalg.solve(np.array([[ta, tb], [td, te]]), world - [ttx, tty])
                rid = contact(
                    labels[target.id],
                    marker.model_copy(update={"x": float(xy[0]), "y": float(xy[1])}),
                    np.linalg.solve(np.array([[a, b], [d, e]]), np.array([[ta, tb], [td, te]])),
                )
                if rid:
                    keys.append((target.id, rid))
                    endpoint_ids.add(target.id)
            if layer.id in endpoint_ids and marker.end_layer_id in endpoint_ids:
                join(keys)
            else:
                warnings.append(f"Via {marker.id}: endpoint copper contact unresolved")
    seeds: dict[tuple[str, int], set[str]] = {}
    for layer in layers:
        for marker in layer.markers:
            if marker.confirmed and marker.net.strip():
                rid = contact(labels[layer.id], marker)
                if rid:
                    seeds.setdefault(root((layer.id, rid)), set()).add(marker.net.strip())
                else:
                    warnings.append(f"{layer.name}: marker {marker.id} has no unambiguous copper contact")
    regions, area_rows = {}, []
    for layer in layers:
        regions[layer.id] = []
        rows: dict[tuple[str, Status], AreaRow] = {}
        px = state.pixels[layer.id]
        accepted = px.accepted()
        observed = accepted & px.observed
        obs_counts = np.bincount(labels[layer.id][observed].ravel())
        transform = affine_for(layer.calibration)
        factor = abs(transform[0] * transform[3] - transform[1] * transform[2]) if transform else None
        for region in components[layer.id]:
            names = sorted(seeds.get(root((layer.id, region.id)), set()))
            status: Status = "conflict" if len(names) > 1 else "assigned" if names else "unassigned"
            net = " | ".join(names) if names else "UNASSIGNED"
            regions[layer.id].append(
                RegionView(id=region.id, net=net, status=status, pixels=region.pixels, bbox=region.bbox)
            )
            row = rows.setdefault((net, status), AreaRow(layer_id=layer.id, net=net, status=status))
            count = int(obs_counts[region.id]) if region.id < len(obs_counts) else 0
            row.observed_px += count
            row.inferred_px += region.pixels - count
            row.total_px += region.pixels
            row.islands += 1
        for row in rows.values():
            if factor is not None:
                row.observed_mm2 = row.observed_px * factor
                row.inferred_mm2 = row.inferred_px * factor
                row.total_mm2 = row.total_px * factor
            area_rows.append(row)
    return GraphResult(regions, labels, area_rows, warnings)


def project_view(state: State, store: Store) -> ProjectView:
    import shutil

    from pkg_re.net_review import refresh_recommendations

    graph = analyze_graph(state)
    pid = state.project.id
    layers = []
    for layer in state.project.layers:
        refresh_recommendations(state, layer.id, graph)
        prefix = f"/api/projects/{pid}/layers/{layer.id}"
        revision = f"?revision={state.project.revision}"
        layers.append(
            LayerView(
                **layer.model_dump(),
                image_url=prefix + "/image",
                overlay_url=prefix + "/overlay" + revision,
                candidate_url=prefix + "/candidates.png" + revision,
                protect_url=prefix + "/protect.png" + revision,
                net_overlay_url=prefix + "/nets.png" + revision,
                net_legend=[
                    NetLegend(
                        net=row.net,
                        status=row.status,
                        color=net_color(row.net, row.status),
                        pixels=row.total_px,
                        islands=row.islands,
                    )
                    for row in graph.areas
                    if row.layer_id == layer.id
                ],
                regions=graph.regions[layer.id],
            )
        )
    metadata = state.project.model_dump(exclude={"layers", "warnings"})
    warnings = list(dict.fromkeys([*state.project.warnings, *graph.warnings]))
    return ProjectView(
        **metadata,
        layers=layers,
        warnings=warnings,
        areas=graph.areas,
        history_count=store.history_count(pid, "undo"),
        redo_count=store.history_count(pid, "redo"),
        ocr_available=shutil.which("tesseract") is not None,
    )
