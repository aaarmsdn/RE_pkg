"""Stable display colors; electrical identity always comes from the graph."""

import colorsys
import hashlib

POWER_COLORS = {"VSS": "#4da3ff", "VDD": "#ff6b6b", "VDDQ": "#f5c451"}
SIGNAL_COLORS = (
    "#5eead4",
    "#a78bfa",
    "#f472b6",
    "#bef264",
    "#fb923c",
    "#22d3ee",
    "#c084fc",
    "#fda4af",
    "#86efac",
    "#facc15",
    "#818cf8",
    "#2dd4bf",
    "#e879f9",
    "#a3e635",
    "#fdba74",
    "#67e8f9",
)


def net_color(net: str, status: str) -> str:
    if status == "conflict":
        return "#ff33cc"
    if status == "unassigned":
        return "#929aa6"
    if net in POWER_COLORS:
        return POWER_COLORS[net]
    dq_colors = {f"DQ{i}": color for i, color in enumerate(SIGNAL_COLORS)}
    if net in dq_colors:
        return dq_colors[net]
    hue = int.from_bytes(hashlib.sha256(net.encode()).digest()[:2], "big") / 65536
    rgb = colorsys.hls_to_rgb(hue, 0.68, 0.72)
    return "#" + "".join(f"{round(channel * 255):02x}" for channel in rgb)


def rgb_color(color: str) -> tuple[int, int, int]:
    return tuple(int(color[i : i + 2], 16) for i in (1, 3, 5))
