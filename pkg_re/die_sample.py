"""Small dense die-pad examples ingested through ordinary PNG bytes."""

import io

from PIL import Image

from pkg_re.bga_fixture import BgaFixture
from pkg_re.bga_render import Profile
from pkg_re.bga_sample import install_annotations
from pkg_re.die_fixture import DieLayout, die_fixture, die_fixture_metadata
from pkg_re.die_render import render_die_layer
from pkg_re.images import add_image
from pkg_re.store import State, Store


def create_die_sample(state: State, store: Store, layout: DieLayout, profile: Profile) -> BgaFixture:
    fixture = die_fixture(layout)
    for index, reference in enumerate(fixture.layers):
        rendered = render_die_layer(reference, profile, index)
        data = io.BytesIO()
        Image.fromarray(rendered.image).save(data, format="PNG")
        add_image(state, store, data.getvalue(), f"DIE {layout} {profile.upper()} L{index + 1}")
    install_annotations(state, fixture)
    metadata = die_fixture_metadata(fixture, layout)
    state.project.warnings.extend(
        [
            f"SYNTHETIC DIE {layout} / {profile}: 32 balls, 16 DQ + VSS/VDD/VDDQ. "
            "L2 has 22 pads (16 signal + 6 power), each 6×12 px on 16 px nominal pitch; "
            "L1 ball diameter 49 px. Original BGA example still has its separate 36-pad arrangement.",
            f"Native fine traces are 3 px; minimum blank gap {metadata['minimum_gap_px']} px. "
            "Center array includes a deliberate 1 px resolution stress. Inspect at 100% or higher.",
            "PNG input only. Confirmed L1 ball names plus unnamed via/pad coordinates are supplied; "
            "pristine copper and damage locations are not reconstruction inputs.",
            "5 mm ball pitch is synthetic calibration, not a production die-pad size claim. "
            "Power plane ratios differ from the original 50/25/25 example. "
            "Missing land restoration is separate.",
        ]
    )
    return fixture
