"""Dense-pad optical damage with evaluation-only locations and removed masks."""

from dataclasses import replace

import numpy as np

from pkg_re.bga_fixture import BgaLayer
from pkg_re.bga_render import DamageEvent, Profile, RenderedLayer, render_layer


def render_die_layer(layer: BgaLayer, profile: Profile, index: int) -> RenderedLayer:
    """Interrupt one fine power feeder and, in severe inputs, remove one tiny pad."""
    if profile == "clean" or not any(t.kind == "pad" for t in layer.terminals):
        return render_layer(layer, profile, index)
    copper = np.logical_or.reduce([n.mask for n in layer.nets])
    removed = np.zeros_like(copper)
    events = []
    power = next(t for t in layer.terminals if t.net == "VSS")
    # Fixture geometry is allowed only here: it creates an adversarial input, never a repair hint.
    y = (power.y + 736) // 2
    power_net = next(n for n in layer.nets if n.name == power.net)
    feeder = np.flatnonzero(power_net.mask[y, power.x - 16 : power.x])
    x = power.x - 16 + int(np.median(feeder))
    removed[y - 1 : y + 1, x - 2 : x + 3] = copper[y - 1 : y + 1, x - 2 : x + 3]
    events.append(DamageEvent("fine_power_gap", (x - 2, y - 1, 5, 2), int(removed.sum()), "VSS"))
    if profile == "severe":
        pad = next(t for t in layer.terminals if t.net == "DQ3")
        selected = copper[pad.y - 6 : pad.y + 6, pad.x - 3 : pad.x + 3]
        removed[pad.y - 6 : pad.y + 6, pad.x - 3 : pad.x + 3] |= selected
        events.append(
            DamageEvent("missing_die_pad", (pad.x - 3, pad.y - 6, 6, 12), int(selected.sum()), "DQ3")
        )
    damaged_layer = replace(layer, nets=tuple(replace(n, mask=n.mask & ~removed) for n in layer.nets))
    rendered = render_layer(damaged_layer, profile, index)
    return replace(rendered, removed=rendered.removed | removed, events=(*rendered.events, *events))
