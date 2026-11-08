"""Local-only annotation suggestions and explicit populated ball grids."""

import csv
import io
import shutil
import uuid
from typing import assert_never

import cv2
import numpy as np
import pytesseract
from fastapi import HTTPException
from numpy.typing import NDArray
from PIL import Image
from pydantic import ValidationError

from pkg_re.engine import stroke_mask
from pkg_re.models import Ballmap, Calibration, Detect, Marker
from pkg_re.store import State, Store


def detect_annotations(state: State, store: Store, lid: str, options: Detect) -> None:
    layer = state.layer(lid)
    with Image.open(store.folder(state.project.id) / f"{lid}.png") as image:
        rgb = np.array(image)
    suggestions = []
    if options.green_markers:
        hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
        lime = cv2.inRange(hsv, np.array([30, 75, 80]), np.array([90, 255, 255]))
        contours, _ = cv2.findContours(lime, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
            area = cv2.contourArea(contour)
            if area < 12 or area > 50000:
                continue
            x, y, w, h = cv2.boundingRect(contour)
            perimeter = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.03 * perimeter, True)
            kind = "pad" if len(approx) == 4 else "via"
            if kind == "via" and not 0.65 < w / h < 1.5:
                continue
            suggestions.append(
                Marker(
                    id=uuid.uuid4().hex,
                    kind=kind,
                    x=x + w / 2,
                    y=y + h / 2,
                    radius=min(500, max(w, h) / 2),
                    source="detected",
                    bbox=(x, y, w, h),
                )
            )
        layer.warnings.append(
            "Green shape detections are suggestions: original soldermask may look similar; confirm manually."
        )
    if options.ocr:
        if not shutil.which("tesseract"):
            layer.warnings.append("Tesseract unavailable: enter net labels manually.")
        else:
            if layer.width * layer.height > 4_000_000:
                layer.warnings.append("OCR limited to the current <=4M native ROI. Set an ROI first.")
            x, y, w, h = layer.roi or (0, 0, layer.width, layer.height)
            if w * h <= 4_000_000:
                source = rgb[y : y + h, x : x + w]
                for attempt in range(2):
                    if attempt:
                        gray = cv2.cvtColor(source, cv2.COLOR_RGB2GRAY)
                        source = 255 - cv2.threshold(gray, 210, 255, cv2.THRESH_BINARY)[1]
                        layer.warnings.append(
                            "Raw OCR had no usable text; tried native-resolution "
                            "bright-text threshold fallback."
                        )
                    try:
                        tsv = pytesseract.image_to_data(source, config="--psm 11", timeout=30)
                    except (pytesseract.TesseractError, RuntimeError) as exc:
                        raise HTTPException(422, f"Local OCR failed: {exc}") from exc
                    rows = [
                        row
                        for row in csv.DictReader(io.StringIO(tsv), delimiter="\t")
                        if (row.get("text") or "").strip() and float(row["conf"]) >= 25
                    ]
                    if rows:
                        break
                for row in rows:
                    text = row["text"].strip()
                    left, top, width, height = (int(row[n]) for n in ("left", "top", "width", "height"))
                    cx, cy = x + left + width / 2, y + top + height / 2
                    balls = [m for m in layer.markers if m.kind == "ball"]
                    closest = min(balls, key=lambda m: (m.x - cx) ** 2 + (m.y - cy) ** 2, default=None)
                    if (
                        closest
                        and (closest.x - cx) ** 2 + (closest.y - cy) ** 2 <= max(30, closest.radius * 2) ** 2
                    ):
                        cx, cy = closest.x, closest.y
                    suggestions.append(
                        Marker(
                            id=uuid.uuid4().hex,
                            kind="net",
                            x=cx,
                            y=cy,
                            net=text,
                            radius=min(500, max(1, height / 2)),
                            source="ocr",
                            bbox=(x + left, y + top, width, height),
                            confidence=float(row["conf"]),
                        )
                    )
                layer.warnings.append(
                    "OCR labels need confirmation. Text-covered pixels are not proof of underlying copper; "
                    "use raw image where possible. Label center may be occluded: "
                    "review the populated ball land "
                    "or set an explicit contact radius, confirm the label, then reanalyze."
                )
    layer.markers = [
        m for m in layer.markers if m.confirmed or m.source not in ("ocr", "detected")
    ] + suggestions[:1000]


def annotation_unknown_mask(
    rgb: NDArray[np.uint8], markers: list[Marker], origin: tuple[int, int]
) -> NDArray[np.bool_]:
    """Identify occluded pixels without asserting dielectric or removing edits.

    OCR bounds remain in source coordinates even when the label snaps to a ball.
    Dark pixels inside detected lime shapes may be painted center indicators.
    """
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    unknown = cv2.inRange(hsv, np.array([30, 75, 80]), np.array([90, 255, 255])) > 0
    ox, oy = origin
    for marker in markers:
        if marker.bbox is None:
            continue
        x, y, width, height = marker.bbox
        left, top = max(0, x - ox), max(0, y - oy)
        right, bottom = min(rgb.shape[1], x + width - ox), min(rgb.shape[0], y + height - oy)
        if left >= right or top >= bottom:
            continue
        match marker.source:
            case "ocr":
                unknown[top:bottom, left:right] = True
            case "detected":
                unknown[top:bottom, left:right] |= np.max(rgb[top:bottom, left:right], axis=2) < 70
            case "manual" | "grid":
                continue
            case unreachable:
                assert_never(unreachable)
    return unknown


def apply_ballmap(state: State, lid: str, data: Ballmap) -> None:
    layer = state.layer(lid)
    try:
        calibration = Calibration.model_validate(
            {
                **layer.calibration.model_dump(),
                "mm_per_pixel": data.pitch_mm / data.pitch_px,
                "affine": None,
            }
        )
    except ValidationError as exc:
        raise HTTPException(422, "Ball pitch ratio is outside the supported calibration range") from exc
    rows = list(csv.DictReader(io.StringIO(data.csv)))
    if not rows or len(rows) > 5000 or not {"row", "col", "net", "populated"}.issubset(rows[0]):
        raise HTTPException(422, "CSV requires row,col,net,populated and 1..5000 rows")
    markers = []
    occupied = set()
    for row in rows:
        try:
            r, c = int(row["row"]), int(row["col"])
            populated = int(row["populated"])
        except (ValueError, TypeError) as exc:
            raise HTTPException(422, "Grid row,col,populated must be integers") from exc
        if populated not in (0, 1) or (r, c) in occupied:
            raise HTTPException(422, "Duplicate grid cell or invalid populated flag")
        occupied.add((r, c))
        if not populated:
            continue
        x, y = data.origin.x + c * data.pitch_px, data.origin.y + r * data.pitch_px
        if not 0 <= x < layer.width or not 0 <= y < layer.height:
            raise HTTPException(422, "Populated grid site outside image")
        markers.append(
            Marker(
                id=uuid.uuid4().hex,
                kind="ball",
                x=x,
                y=y,
                net=row["net"].strip(),
                radius=data.radius_px,
                source="grid",
                confirmed=True,
            )
        )
    pixels = state.pixels[lid]
    grid_added = np.zeros((layer.height, layer.width), dtype=bool)
    if data.restore_missing:
        for marker in markers:
            disk = stroke_mask((layer.height, layer.width), [(marker.x, marker.y)], marker.radius)
            grid_added |= disk & ~pixels.observed & ~pixels.protected & ~pixels.erased
    layer.markers = [m for m in layer.markers if m.source != "grid"] + markers
    layer.calibration = calibration
    pixels.grid_added = grid_added
    if data.restore_missing:
        layer.warnings.append(
            "Populated ball lands restored as inferred disks; no hidden escape traces were invented."
        )
