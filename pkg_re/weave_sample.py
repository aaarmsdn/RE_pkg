"""Ingest complex reference examples as PNGs with supplied contact annotations."""

import io

from PIL import Image

from pkg_re.bga_fixture import BgaFixture
from pkg_re.bga_render import Profile
from pkg_re.bga_sample import install_annotations
from pkg_re.images import add_image
from pkg_re.store import State, Store
from pkg_re.weave_fixture import WeaveLayout, weave_fixture, weave_metadata
from pkg_re.weave_render import render_weave_layer


def create_weave_sample(state: State, store: Store, layout: WeaveLayout, profile: Profile) -> BgaFixture:
    """Expose only PNG bytes, lower ball names and unnamed upper contacts to analysis."""
    fixture = weave_fixture(layout)
    for index, reference in enumerate(fixture.layers):
        rendered = render_weave_layer(reference, profile, index, layout)
        data = io.BytesIO()
        Image.fromarray(rendered.image).save(data, format="PNG")
        add_image(state, store, data.getvalue(), f"DIE {layout} {profile.upper()} L{index + 1}")
    install_annotations(state, fixture)
    metadata = weave_metadata(fixture, layout)
    state.project.warnings.extend(
        [
            f"SYNTHETIC {layout} / {profile}: {metadata['signal_count']} DQ signals, "
            f"{len(fixture.layers[0].terminals)} balls, {len(fixture.layers[1].terminals)} upper pads. "
            "Ball-to-pad mapping and routes differ from the original straight fanout examples.",
            f"Native pad {metadata['pad_width_px']}×{metadata['pad_height_px']} px, "
            f"pitch {metadata['pad_pitch_px']} px, trace width {metadata['trace_width_px']} px, "
            f"minimum gap {metadata['minimum_gap_px']} px. Synthetic dimensions, not manufacturing rules.",
            "Ordinary PNG input with confirmed ball names and unnamed via/pad positions. "
            "Reference masks, upper NET names and damage locations are evaluation-only. "
            "Missing ball land restoration remains a separate operation.",
            "Inspect native pixels: optical blur can erase small gaps or break narrow routes. "
            "Unresolved NET conflicts are failures, not a completed reconstruction.",
        ]
    )
    return fixture
