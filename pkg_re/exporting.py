"""Neutral exports and safe self-contained project archives."""

import csv
import io
import json
import re
import uuid
import zipfile
from dataclasses import asdict
from xml.sax.saxutils import escape

import numpy as np
from fastapi import HTTPException
from PIL import Image

from pkg_re.engine import mask_polygons
from pkg_re.graph import affine_for, analyze_graph, project_view
from pkg_re.store import State, Store, decode_state, encode_state


def neutral_export(state: State, store: Store) -> bytes:
    graph = analyze_graph(state)
    out = project_view(state, store).model_dump()
    out["coordinate_convention"] = "calibrated: mm x-right/y-up; uncalibrated: image px x-right/y-down"
    out["geometry"] = {}
    for layer in state.project.layers:
        groups = {}
        for region in graph.regions[layer.id]:
            groups.setdefault((region.net, region.status), []).append(region.id)
        entries = []
        for (net, status), ids in groups.items():
            mask = np.isin(graph.labels[layer.id], ids)
            polygons = mask_polygons(mask, affine_for(layer.calibration))
            entries.append({"net": net, "status": status, "polygons": [asdict(p) for p in polygons]})
        out["geometry"][layer.id] = {
            "units": "mm" if affine_for(layer.calibration) else "px",
            "groups": entries,
        }
    out["export_status"] = "NEUTRAL_PROTOTYPE_NOT_MCM_OR_SIMULATION_VALIDATED"
    return json.dumps(out, ensure_ascii=False, allow_nan=False).encode()


def csv_export(state: State) -> bytes:
    rows = analyze_graph(state).areas
    out = io.StringIO()
    fields = [
        "layer_id",
        "net",
        "status",
        "observed_px",
        "inferred_px",
        "total_px",
        "observed_mm2",
        "inferred_mm2",
        "total_mm2",
        "islands",
    ]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in rows:
        values = row.model_dump()
        if row.net.startswith(("=", "+", "-", "@")):
            values["net"] = "'" + row.net
        writer.writerow(values)
    return ("\ufeff" + out.getvalue()).encode()


def svg_export(state: State, lid: str) -> bytes:
    layer = state.layer(lid)
    polygons = mask_polygons(state.pixels[lid].accepted())
    paths = []
    for polygon in polygons:
        rings = [polygon.exterior, *polygon.holes]
        commands = []
        for ring in rings:
            commands.append("M" + " L".join(f"{x:g},{y:g}" for x, y in ring) + " Z")
        paths.append(f'<path d="{" ".join(commands)}" fill="#bc975b" fill-rule="evenodd"/>')
    title = escape(f"{layer.name}: native pixel overlay; physical calibration is stored in JSON")
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {layer.width} {layer.height}">'
        f"<title>{title}</title>{''.join(paths)}</svg>"
    ).encode()


def bundle_export(state: State, store: Store) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("state.zip", encode_state(state))
        archive.writestr("areas.csv", csv_export(state))
        archive.writestr(
            "README.txt",
            "Package RE project v1. Native sources and accepted/inferred/protected masks. "
            "Includes current state and edit audit log; local undo snapshots are not included. "
            "Not an MCM file. Export JSON separately for physical polygons.",
        )
        for layer in state.project.layers:
            for suffix in ("png", "original"):
                path = store.folder(state.project.id) / f"{layer.id}.{suffix}"
                if path.is_file():
                    archive.writestr(f"sources/{layer.id}.{suffix}", path.read_bytes())
    return out.getvalue()


def import_bundle(payload: bytes, store: Store) -> State:
    if len(payload) > 150_000_000:
        raise HTTPException(413, "Project archive exceeds 150 MB")
    try:
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            infos = archive.infolist()
            if sum(i.file_size for i in infos) > 250_000_000 or len(infos) > 130:
                raise HTTPException(413, "Project archive expanded size/count exceeds limits")
            permitted = re.compile(
                r"(?:state\.zip|areas\.csv|README\.txt|sources/[0-9a-f]{32}\.(?:png|original))"
            )
            if any(not permitted.fullmatch(i.filename) for i in infos):
                raise HTTPException(422, "Unexpected archive path")
            nested = archive.read("state.zip")
            with zipfile.ZipFile(io.BytesIO(nested)) as inner:
                if sum(i.file_size for i in inner.infolist()) > 250_000_000:
                    raise HTTPException(413, "Expanded state exceeds limits")
            state = decode_state(nested)
            if len(state.project.layers) > 24:
                raise HTTPException(413, "At most 24 layers supported")
            sources = {}
            for layer in state.project.layers:
                data = archive.read(f"sources/{layer.id}.png")
                with Image.open(io.BytesIO(data)) as image:
                    if image.size != (layer.width, layer.height):
                        raise HTTPException(422, "Source dimensions do not match layer")
                    image.verify()
                sources[f"{layer.id}.png"] = data
                original = f"sources/{layer.id}.original"
                if original in archive.namelist():
                    sources[f"{layer.id}.original"] = archive.read(original)
    except (zipfile.BadZipFile, KeyError, ValueError, OSError) as exc:
        raise HTTPException(422, "Invalid project archive") from exc
    state.project.id = uuid.uuid4().hex
    state.project.revision += 1
    store.save(state)
    for name, data in sources.items():
        (store.folder(state.project.id) / name).write_bytes(data)
    return state
