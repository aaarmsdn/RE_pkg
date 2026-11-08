"""Disk persistence with atomic files and mask-only undo snapshots."""

import io
import os
import re
import uuid
import zipfile
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from fastapi import HTTPException
from numpy.typing import NDArray

from pkg_re.models import Layer, Project

Mask = NDArray[np.bool_]


@dataclass(slots=True)
class Pixels:
    """Mutable raster buffers; accepted evidence is derived, not overwritten."""

    observed: Mask
    added: Mask
    erased: Mask
    protected: Mask
    patches: dict[str, Mask] = field(default_factory=dict)
    grid_added: Mask | None = None

    @classmethod
    def blank(cls, layer: Layer):
        shape = (layer.height, layer.width)
        return cls(*(np.zeros(shape, dtype=bool) for _ in range(4)))

    def accepted(self) -> Mask:
        return (self.observed | self.inferred()) & ~self.erased & ~self.protected

    def inferred(self) -> Mask:
        return self.added if self.grid_added is None else self.added | self.grid_added


@dataclass(slots=True)
class State:
    """A transaction's mutable project and native-resolution masks."""

    project: Project
    pixels: dict[str, Pixels]

    def layer(self, lid: str) -> Layer:
        for layer in self.project.layers:
            if layer.id == lid:
                return layer
        raise HTTPException(404, "Layer not found")


class Store:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def folder(self, pid: str) -> Path:
        if not re.fullmatch(r"[0-9a-f]{32}", pid):
            raise HTTPException(404, "Project not found")
        return self.root / pid

    def create(self, name: str) -> State:
        state = State(Project(id=uuid.uuid4().hex, name=name), {})
        self.save(state)
        return state

    def load(self, pid: str) -> State:
        path = self.folder(pid) / "state.zip"
        if not path.is_file():
            raise HTTPException(404, "Project not found")
        return decode_state(path.read_bytes())

    def save(self, state: State) -> None:
        folder = self.folder(state.project.id)
        folder.mkdir(exist_ok=True)
        tmp = folder / "state.tmp"
        tmp.write_bytes(encode_state(state))
        os.replace(tmp, folder / "state.zip")

    def mutate(self, pid: str, operation: Callable[[State], None], action: str = "edit") -> State:
        state = self.load(pid)
        previous = encode_state(state)
        operation(state)
        state.project.revision += 1
        state.project.edit_log.append(
            f"{datetime.now(UTC).isoformat()} revision={state.project.revision} {action}"
        )
        for layer in state.project.layers:
            layer.revision = state.project.revision
        self.save(state)
        self._push(pid, "undo", previous)
        for path in (self.folder(pid) / "redo").glob("*.zip"):
            path.unlink()
        return state

    def _push(self, pid: str, kind: str, payload: bytes) -> None:
        import time

        folder = self.folder(pid) / kind
        folder.mkdir(exist_ok=True)
        (folder / f"{time.time_ns()}.zip").write_bytes(payload)
        for path in sorted(folder.glob("*.zip"))[:-12]:
            path.unlink()

    def history(self, pid: str, undo: bool) -> State:
        source, target = ("undo", "redo") if undo else ("redo", "undo")
        files = sorted((self.folder(pid) / source).glob("*.zip"))
        if not files:
            raise HTTPException(409, "No history available")
        current = self.load(pid)
        restored = decode_state(files[-1].read_bytes())
        restored.project.revision = current.project.revision + 1
        restored.project.edit_log = [
            *current.project.edit_log,
            f"revision={restored.project.revision} {source}",
        ]
        for layer in restored.project.layers:
            layer.revision = restored.project.revision
        self.save(restored)
        self._push(pid, target, encode_state(current))
        files[-1].unlink()
        return restored

    def history_count(self, pid: str, kind: str) -> int:
        return len(list((self.folder(pid) / kind).glob("*.zip")))


def encode_state(state: State) -> bytes:
    # Revalidate mutable metadata before persistence; model_copy may bypass validators.
    Project.model_validate(state.project.model_dump())
    array_bytes = 0
    for p in state.pixels.values():
        arrays = [p.observed, p.added, p.erased, p.protected, *p.patches.values()]
        if p.grid_added is not None:
            arrays.append(p.grid_added)
        array_bytes += sum(a.nbytes + 256 for a in arrays)
    if array_bytes > 250_000_000:
        raise HTTPException(413, "Expanded masks exceed 250 MB; use fewer/smaller layers")
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("project.json", state.project.model_dump_json())
        for layer in state.project.layers:
            p = state.pixels[layer.id]
            buf = io.BytesIO()
            grid = {"grid_added": p.grid_added} if p.grid_added is not None else {}
            np.savez_compressed(
                buf,
                observed=p.observed,
                added=p.added,
                erased=p.erased,
                protected=p.protected,
                **grid,
                **p.patches,
            )
            archive.writestr(f"{layer.id}.npz", buf.getvalue())
    return out.getvalue()


def decode_state(payload: bytes) -> State:
    with zipfile.ZipFile(io.BytesIO(payload)) as archive:
        project = Project.model_validate_json(archive.read("project.json"))
        if len(project.layers) > 24 or len({layer.id for layer in project.layers}) != len(project.layers):
            raise HTTPException(422, "Invalid layer count or duplicate identifiers")
        pixels = {}
        expanded = 0
        for layer in project.layers:
            if not re.fullmatch(r"[0-9a-f]{32}", layer.id):
                raise HTTPException(422, "Invalid layer identifier")
            names = ("observed", "added", "erased", "protected")
            expected = {name: (layer.height, layer.width) for name in names}
            for candidate in layer.candidates:
                x, y, w, h = candidate.bbox
                if (
                    candidate.id in expected
                    or min(x, y) < 0
                    or min(w, h) <= 0
                    or x + w > layer.width
                    or y + h > layer.height
                ):
                    raise HTTPException(422, "Invalid candidate bounds or identifier")
                expected[candidate.id] = (h, w)
            raw = archive.read(f"{layer.id}.npz")
            with zipfile.ZipFile(io.BytesIO(raw)) as arrays:
                infos = arrays.infolist()
                if "grid_added.npy" in arrays.namelist():
                    expected["grid_added"] = (layer.height, layer.width)
                if len(infos) != len(expected) or {i.filename for i in infos} != {
                    f"{n}.npy" for n in expected
                }:
                    raise HTTPException(422, "Unexpected mask arrays")
                expanded += sum(i.file_size for i in infos)
                if expanded > 250_000_000:
                    raise HTTPException(413, "Expanded masks exceed 250 MB")
                for info in infos:
                    with arrays.open(info) as stream:
                        version = np.lib.format.read_magic(stream)
                        if version != (1, 0):
                            raise HTTPException(422, "Unsupported mask array format")
                        shape, _, dtype = np.lib.format.read_array_header_1_0(stream, max_header_size=10000)
                        required = expected[info.filename[:-4]]
                        if (
                            dtype != np.dtype(bool)
                            or shape != required
                            or info.file_size != stream.tell() + required[0] * required[1]
                        ):
                            raise HTTPException(422, "Invalid mask header, dimensions or dtype")
            with np.load(io.BytesIO(raw), allow_pickle=False) as data:
                masks = [data[n] for n in names]
                if any(m.dtype != bool or m.shape != (layer.height, layer.width) for m in masks):
                    raise HTTPException(422, "Invalid mask dimensions or dtype")
                patches = {n: data[n] for n in data.files if n not in (*names, "grid_added")}
                for candidate in layer.candidates:
                    x, y, w, h = candidate.bbox
                    patch = patches.get(candidate.id)
                    if patch is None or patch.dtype != bool or patch.shape != (h, w):
                        raise HTTPException(422, "Invalid candidate patch")
                    if min(x, y) < 0 or w <= 0 or h <= 0 or x + w > layer.width or y + h > layer.height:
                        raise HTTPException(422, "Invalid candidate bounds")
                pixels[layer.id] = Pixels(
                    *masks, patches, data["grid_added"] if "grid_added" in data else None
                )
    return State(project, pixels)
