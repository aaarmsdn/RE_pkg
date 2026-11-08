"""Loopback-only application entry point and read/export routes."""

import io
import os
import shutil
import zipfile
from pathlib import Path
from urllib.parse import urlsplit

import anyio
import numpy as np
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from pkg_re.exporting import bundle_export, csv_export, neutral_export, svg_export
from pkg_re.graph import analyze_graph, project_view
from pkg_re.images import mask_png
from pkg_re.models import Project
from pkg_re.net_colors import net_color, rgb_color
from pkg_re.routes import mutations
from pkg_re.store import Store

ROOT = Path(__file__).resolve().parent.parent


def create_app(data_root: Path | None = None) -> FastAPI:
    store = Store(data_root or Path(os.environ.get("PKG_RE_DATA", str(ROOT / ".pkg-re"))))
    app = FastAPI(title="Package RE local workbench", version="0.1.0")
    lock = anyio.Lock()

    @app.middleware("http")
    async def local_requests(request: Request, call_next):
        if request.url.hostname not in {"127.0.0.1", "localhost", "::1", "testserver"}:
            return JSONResponse(status_code=403, content={"detail": "Local hosts only"})
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).netloc != request.headers.get("host"):
                return JSONResponse(status_code=403, content={"detail": "Cross-origin mutations rejected"})
        if request.url.path.startswith("/api"):
            async with lock:
                response = await call_next(request)
            response.headers["Cache-Control"] = "no-store"
            return response
        return await call_next(request)

    app.include_router(mutations(store, ROOT / "references"))

    @app.get("/api/health")
    def health():
        return {"status": "ok", "ocr_available": shutil.which("tesseract") is not None}

    @app.get("/api/projects")
    def projects():
        result = []
        for path in sorted(store.root.glob("*/state.zip"), key=lambda p: p.stat().st_mtime, reverse=True):
            with zipfile.ZipFile(path) as archive:
                p = Project.model_validate_json(archive.read("project.json"))
                result.append({"id": p.id, "name": p.name})
        return result

    @app.get("/api/projects/{pid}")
    def project(pid: str):
        return project_view(store.load(pid), store)

    @app.get("/api/projects/{pid}/layers/{lid}/image")
    def image(pid: str, lid: str):
        store.load(pid).layer(lid)
        return FileResponse(store.folder(pid) / f"{lid}.png", media_type="image/png")

    @app.get("/api/projects/{pid}/layers/{lid}/overlay")
    def overlay(pid: str, lid: str):
        from PIL import Image

        state = store.load(pid)
        state.layer(lid)
        pixels = state.pixels[lid]
        accepted = pixels.accepted()
        rgba = np.zeros((*accepted.shape, 4), dtype=np.uint8)
        rgba[accepted & pixels.observed] = (225, 170, 73, 155)
        rgba[accepted & ~pixels.observed] = (95, 230, 175, 210)
        out = io.BytesIO()
        Image.fromarray(rgba).save(out, format="PNG")
        return Response(out.getvalue(), media_type="image/png")

    @app.get("/api/projects/{pid}/layers/{lid}/protect.png")
    def protect(pid: str, lid: str):
        state = store.load(pid)
        state.layer(lid)
        return Response(mask_png(state.pixels[lid].protected, (235, 104, 117, 150)), media_type="image/png")

    @app.get("/api/projects/{pid}/layers/{lid}/nets.png")
    def nets(pid: str, lid: str, net: str | None = None):
        from PIL import Image

        state = store.load(pid)
        state.layer(lid)
        graph = analyze_graph(state)
        regions = graph.regions[lid]
        colors = np.zeros((len(regions) + 1, 4), dtype=np.uint8)
        for region in regions:
            opacity = 240 if net is None or region.net == net else 35
            colors[region.id] = (*rgb_color(net_color(region.net, region.status)), opacity)
        out = io.BytesIO()
        Image.fromarray(colors[graph.labels[lid]]).save(out, format="PNG")
        return Response(out.getvalue(), media_type="image/png")

    @app.get("/api/projects/{pid}/layers/{lid}/candidates.png")
    def candidates(pid: str, lid: str):
        from PIL import Image

        state = store.load(pid)
        layer = state.layer(lid)
        rgba = np.zeros((layer.height, layer.width, 4), dtype=np.uint8)
        for c in layer.candidates:
            if c.status == "pending":
                x, y, w, h = c.bbox
                patch = state.pixels[lid].patches[c.id]
                color = (243, 153, 145, 230) if c.kind == "short_split" else (90, 190, 255, 210)
                rgba[y : y + h, x : x + w][patch] = color
        rgba[state.pixels[lid].protected] = 0
        out = io.BytesIO()
        Image.fromarray(rgba).save(out, format="PNG")
        return Response(out.getvalue(), media_type="image/png")

    @app.get("/api/projects/{pid}/export/{format}")
    def export(pid: str, format: str, layer_id: str | None = None):
        state = store.load(pid)
        match format:
            case "json":
                payload, mime = neutral_export(state, store), "application/json"
            case "csv":
                payload, mime = csv_export(state), "text/csv; charset=utf-8"
            case "zip":
                payload, mime = bundle_export(state, store), "application/zip"
            case "svg":
                if layer_id is None:
                    raise HTTPException(422, "Select a layer for SVG export")
                payload, mime = svg_export(state, layer_id), "image/svg+xml"
            case _:
                raise HTTPException(404, "Export format not supported; MCM adapter is not implemented")
        return Response(
            payload,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="package-re.{format}"'},
        )

    frontend = ROOT / "frontend" / "dist"
    if frontend.is_dir():
        app.mount("/", StaticFiles(directory=frontend, html=True), name="workbench")
    return app


app = create_app()
