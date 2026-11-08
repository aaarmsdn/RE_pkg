"""Validated image ingestion and deterministic demonstration images."""

import hashlib
import io
import uuid

import numpy as np
from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError

from pkg_re.demo import dense_fixture
from pkg_re.models import Calibration, Layer, Marker
from pkg_re.store import Pixels, State, Store


def add_image(state: State, store: Store, payload: bytes, name: str) -> Layer:
    if len(payload) > 80_000_000:
        raise HTTPException(413, "Image file exceeds 80 MB")
    try:
        with Image.open(io.BytesIO(payload)) as image:
            if image.format not in ("PNG", "JPEG"):
                raise HTTPException(422, "Only PNG/JPEG images are supported")
            if image.width * image.height > 30_000_000:
                raise HTTPException(413, "Image exceeds 30 million pixels")
            rgb = ImageOps.exif_transpose(image).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise HTTPException(422, "Invalid or oversized image") from exc
    lid = uuid.uuid4().hex
    layer = Layer(
        id=lid,
        name=name[:200],
        width=rgb.width,
        height=rgb.height,
        source_sha256=hashlib.sha256(payload).hexdigest(),
    )
    folder = store.folder(state.project.id)
    rgb.save(folder / f"{lid}.png")
    (folder / f"{lid}.original").write_bytes(payload)
    state.project.layers.append(layer)
    state.pixels[lid] = Pixels.blank(layer)
    return layer


def create_demo(state: State, store: Store) -> None:
    """Create new dense source images; saved projects are never regenerated."""
    layers = []
    for index in range(2):
        fixture = dense_fixture(index)
        data = io.BytesIO()
        Image.fromarray(fixture.image).save(data, format="PNG")
        layer = add_image(state, store, data.getvalue(), f"SYNTHETIC DENSE L{index + 1}")
        layer.calibration = Calibration(mm_per_pixel=0.005)
        layer.markers = [
            Marker(
                id=uuid.uuid4().hex, kind="net", x=net.seed[0], y=net.seed[1], net=net.name, confirmed=True
            )
            for net in fixture.nets[:3]
        ]
        layer.markers.append(
            Marker(id=uuid.uuid4().hex, kind="net", x=1110, y=120, net="VSS", confirmed=True)
        )
        for i, y in enumerate(fixture.signal_y):
            layer.markers.append(
                Marker(
                    id=uuid.uuid4().hex,
                    kind="ball" if index == 0 else "pad",
                    x=160 if index == 0 else 1010,
                    y=y,
                    net=f"DQ{i}" if index == 0 else "",
                    radius=2,
                    confirmed=True,
                )
            )
        state.pixels[layer.id].protected |= fixture.protected
        layers.append(layer)
    layers[0].markers += [
        Marker(
            id=uuid.uuid4().hex, kind="via", x=1040, y=y, radius=2, end_layer_id=layers[1].id, confirmed=True
        )
        for y in fixture.signal_y
    ]
    state.project.warnings.append(
        "SYNTHETIC DENSE DEMO: 20 DQ routes and VSS/VDD/VDDQ planes; 2/3/5px traces, "
        "5px nominal plane clearance, 19px bus pitch. Known geometry, not a real package. "
        "L1 deliberate damage: DQ6 gap x620..621, VSS hole x86..93/y94..99, "
        "VSS scratch x1090..1091/y60..299. Candidates may include intentional clearances; "
        "review individually."
    )


def mask_png(mask: np.ndarray, color: tuple[int, int, int, int]) -> bytes:
    rgba = np.zeros((*mask.shape, 4), dtype=np.uint8)
    rgba[mask] = color
    out = io.BytesIO()
    Image.fromarray(rgba).save(out, format="PNG")
    return out.getvalue()
