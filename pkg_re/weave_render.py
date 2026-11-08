"""Geometry-specific optical damage for woven evaluation inputs."""

from dataclasses import replace

import numpy as np

from pkg_re.bga_fixture import BgaLayer
from pkg_re.bga_render import DamageEvent, Profile, RenderedLayer, render_layer
from pkg_re.weave_fixture import WeaveLayout, _dimensions


def render_weave_layer(layer: BgaLayer, profile: Profile, index: int, layout: WeaveLayout) -> RenderedLayer:
    """Damage the actual feeder and pad before applying the shared optical model."""
    if profile in {"clean", "diagonal"} or index != 1:
        return render_layer(layer, profile, index)
    _, width, height, _, _ = _dimensions(layout)
    removed = np.zeros_like(layer.nets[0].mask)
    events: list[DamageEvent] = []
    power = next(net for net in layer.nets if net.name == "VSS")
    pad = next(t for t in layer.terminals if t.net == "VSS")
    patch = np.zeros_like(removed)
    patch[pad.y - 2 : pad.y + 3, pad.x - 68 : pad.x - 65] = True
    selected = patch & power.mask
    removed |= selected
    events.append(DamageEvent("fine_power_gap", (pad.x - 68, pad.y - 2, 3, 5), int(selected.sum()), "VSS"))
    if profile == "severe":
        target = next(t for t in layer.terminals if t.net == "DQ3")
        patch[:] = False
        patch[
            target.y - height // 2 : target.y + height // 2, target.x - width // 2 : target.x + width // 2
        ] = True
        net = next(n for n in layer.nets if n.name == target.net)
        selected = patch & net.mask
        removed |= selected
        events.append(
            DamageEvent(
                "missing_die_pad",
                (target.x - width // 2, target.y - height // 2, width, height),
                int(selected.sum()),
                target.net,
            )
        )
    damaged = replace(layer, nets=tuple(replace(net, mask=net.mask & ~removed) for net in layer.nets))
    rendered = render_layer(damaged, profile, index)
    return replace(rendered, removed=rendered.removed | removed, events=(*rendered.events, *events))
