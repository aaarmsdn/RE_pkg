"""Normal PNG ingestion plus explicit supplied ball/via/pad annotations."""

import io

from PIL import Image

from pkg_re.annotations import apply_ballmap
from pkg_re.bga_fixture import BgaFixture, bga_fixture
from pkg_re.bga_render import Profile, render_layer
from pkg_re.images import add_image
from pkg_re.models import Ballmap, Calibration, Marker, Point
from pkg_re.store import State, Store


def ballmap_input(fixture: BgaFixture, restore: bool = False) -> Ballmap:
    """The known populated grid is metadata, not observed image evidence."""
    balls = fixture.layers[0].terminals
    x0, y0 = min(t.x for t in balls), min(t.y for t in balls)
    rows = ["row,col,net,populated"]
    for ball in balls:
        row = (ball.y - y0) // fixture.pitch_px
        col = (ball.x - x0) // fixture.pitch_px
        rows.append(f"{row},{col},{ball.net},1")
    return Ballmap(
        csv="\n".join(rows),
        origin=Point(x=x0, y=y0),
        pitch_px=fixture.pitch_px,
        pitch_mm=fixture.pitch_px * fixture.mm_per_pixel,
        radius_px=balls[0].radius,
        restore_missing=restore,
    )


def install_annotations(state: State, fixture: BgaFixture) -> None:
    """Only lower ball names are seeds; upper pad and via nets remain unspecified."""
    lower, upper = state.project.layers[-2:]
    for layer, reference in zip((lower, upper), fixture.layers, strict=True):
        layer.calibration = Calibration(mm_per_pixel=fixture.mm_per_pixel)
        if layer.id == lower.id:
            apply_ballmap(state, lower.id, ballmap_input(fixture))
        else:
            layer.markers = [
                Marker(id=t.name, kind="pad", x=t.x, y=t.y, radius=t.radius, confirmed=True)
                for t in reference.terminals
            ]
    lower.markers.extend(
        Marker(id=v.id, kind="via", x=v.x, y=v.y, radius=v.radius, end_layer_id=upper.id, confirmed=True)
        for v in fixture.layers[0].vias
    )


def create_bga_sample(
    state: State, store: Store, profile: Profile, fixture: BgaFixture | None = None
) -> BgaFixture:
    """Encode then reopen PNGs; no truth mask is passed to the reconstruction state."""
    fixture = fixture or bga_fixture()
    for index, reference in enumerate(fixture.layers):
        rendered = render_layer(reference, profile, index)
        data = io.BytesIO()
        Image.fromarray(rendered.image).save(data, format="PNG")
        add_image(state, store, data.getvalue(), f"BGA {profile.upper()} L{index + 1}")
    install_annotations(state, fixture)
    state.project.warnings.extend(
        [
            f"SYNTHETIC BGA {profile}: 8×4 balls, 5mm pitch; DQ0–7 bottom / DQ8–15 top; "
            "VDD pads 6 (left/center/right on both rows).",
            "PNG encoded and reopened through ordinary ingestion. Only supplied L1 ballmap and "
            "via/pad coordinates are installed. Upper NET names and all copper masks start unknown.",
            "50/25/25 is the pristine plane-only area target, not damaged total net area. "
            "Damaged samples include missing/half balls, scratches, edge blur and faded narrow gaps. "
            "Ballmap land restoration and candidate approvals remain explicit human actions.",
        ]
    )
    return fixture
