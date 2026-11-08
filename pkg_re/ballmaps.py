"""Bounded, pickle-free decoding of logical Unicode ball grids."""

import ast
import re
import struct

import numpy as np

MAX_NPY_BYTES = 4 * 1024 * 1024
MAX_GRID_CELLS = 5000


def validate_grid(grid: list[list[str]]) -> list[list[str]]:
    if not grid or not grid[0]:
        raise ValueError("Ballmap must have at least one row and column")
    columns = len(grid[0])
    if len(grid) * columns > MAX_GRID_CELLS or any(len(row) != columns for row in grid):
        raise ValueError("Ballmap must be rectangular with at most 5000 cells")
    if any(not isinstance(name, str) or len(name) > 160 for row in grid for name in row):
        raise ValueError("Ballmap NET names must be strings of at most 160 characters")
    try:
        for row in grid:
            for name in row:
                name.encode("utf-8")
    except UnicodeError as exc:
        raise ValueError("Ballmap contains invalid Unicode") from exc
    return [[name.strip() for name in row] for row in grid]


def decode_npy(payload: bytes) -> list[list[str]]:
    """Check header and exact payload bounds before constructing an array view."""
    if len(payload) > MAX_NPY_BYTES:
        raise ValueError("Ballmap NPY exceeds 4 MiB")
    if len(payload) < 10 or payload[:6] != b"\x93NUMPY":
        raise ValueError("Upload a NumPy .npy file")
    version = tuple(payload[6:8])
    if version not in {(1, 0), (2, 0), (3, 0)}:
        raise ValueError("Unsupported NPY version")
    header_start = 10 if version == (1, 0) else 12
    if len(payload) < header_start:
        raise ValueError("Truncated NPY header")
    header_length = struct.unpack("<H" if version == (1, 0) else "<I", payload[8:header_start])[0]
    data_start = header_start + header_length
    if not 0 < header_length <= 10 * 1024 or data_start > len(payload):
        raise ValueError("NPY header is truncated or exceeds 10 KiB")
    try:
        header = ast.literal_eval(payload[header_start:data_start].decode(
            "utf-8" if version == (3, 0) else "latin1"
        ))
    except (ValueError, TypeError, SyntaxError, UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid NPY header") from exc
    if not isinstance(header, dict) or set(header) != {"descr", "shape", "fortran_order"}:
        raise ValueError("Invalid NPY header fields")
    shape = header["shape"]
    if (not isinstance(shape, tuple) or len(shape) != 2
            or any(type(size) is not int or size < 1 for size in shape)
            or shape[0] * shape[1] > MAX_GRID_CELLS):
        raise ValueError("Ballmap NPY must be a 2D array with 1..5000 cells")
    description = header["descr"]
    match = re.fullmatch(r"[<>=]U([1-9][0-9]{0,2})", description) if isinstance(description, str) else None
    if not match or int(match[1]) > 160:
        raise ValueError("Ballmap NPY requires Unicode strings (U1..U160), not object or numeric data")
    if type(header["fortran_order"]) is not bool:
        raise ValueError("Invalid NPY array order")
    dtype = np.dtype(description)
    count = shape[0] * shape[1]
    if data_start + count * dtype.itemsize != len(payload):
        raise ValueError("NPY payload is truncated or has trailing data")
    codepoints = np.frombuffer(payload, dtype=np.dtype(description[0] + "u4"), offset=data_start)
    if np.any(codepoints > 0x10FFFF) or np.any((codepoints >= 0xD800) & (codepoints <= 0xDFFF)):
        raise ValueError("Invalid NPY Unicode payload")
    try:
        array = np.frombuffer(payload, dtype=dtype, count=count, offset=data_start)
        grid = array.reshape(shape, order="F" if header["fortran_order"] else "C").tolist()
    except (ValueError, UnicodeError) as exc:
        raise ValueError("Invalid NPY Unicode payload") from exc
    return validate_grid(grid)
