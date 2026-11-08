"""Untrusted mask headers and physical via contact footprint regressions."""

import io
import zipfile

import numpy as np
import pytest
from fastapi import HTTPException

from pkg_re.graph import contact
from pkg_re.models import Layer, Marker
from pkg_re.store import Pixels, Store, decode_state, encode_state


def test_nested_npz_rejects_oversized_shape_before_allocation(tmp_path):
    store = Store(tmp_path)
    state = store.create("archive")
    layer = Layer(id="a" * 32, name="L1", width=10, height=10)
    state.project.layers.append(layer)
    state.pixels[layer.id] = Pixels.blank(layer)
    original = encode_state(state)
    forged = io.BytesIO()
    with zipfile.ZipFile(io.BytesIO(original)) as src, zipfile.ZipFile(forged, "w") as dst:
        for name in src.namelist():
            if name.endswith(".npz"):
                arrays = io.BytesIO()
                with zipfile.ZipFile(io.BytesIO(src.read(name))) as old, zipfile.ZipFile(arrays, "w") as new:
                    for member in old.namelist():
                        blob = old.read(member)
                        if member == "observed.npy":
                            header = io.BytesIO()
                            np.lib.format.write_array_header_1_0(
                                header, {"descr": "|b1", "fortran_order": False, "shape": (10**9, 10**9)}
                            )
                            blob = header.getvalue()
                        new.writestr(member, blob)
                dst.writestr(name, arrays.getvalue())
            else:
                dst.writestr(name, src.read(name))
    with pytest.raises(HTTPException, match="Invalid mask header"):
        decode_state(forged.getvalue())


def test_contact_radius_not_rounded_outward_and_transforms_to_source_pixels():
    labels = np.zeros((30, 30), dtype=np.int32)
    labels[10, 13] = 1
    marker = Marker(id="via", kind="via", x=10, y=10, contact_radius=2.1)
    assert contact(labels, marker) == 0
    # Target pixels half the physical size: source radius 2.1 covers 4.2 target px.
    assert contact(labels, marker, np.eye(2) * 0.5) == 1
    labels[10, 6] = 2
    assert contact(labels, marker, np.eye(2) * 0.5) == 0
