"""Physical scoring must not mistake a NET label for an electrical connection."""

import numpy as np
import pytest

from pkg_re import batch_review, operations
from pkg_re.bga_fixture import BgaFixture, BgaLayer, BgaNet, BgaTerminal, BgaVia
from pkg_re.die_benchmark import algorithm, score, terminal_pairs
from pkg_re.models import Layer, Marker
from pkg_re.store import Pixels, State


def fixture_pair():
    mask = np.zeros((12, 12), bool)
    mask[3, 2:10] = True
    other = np.zeros_like(mask)
    other[8, 2:10] = True
    nets = tuple(
        BgaNet(name, value, np.zeros_like(mask), (2, y))
        for name, value, y in (("A", mask, 3), ("B", other, 8))
    )
    via = BgaVia("via", "A", 5, 3, 1)
    layers = tuple(
        BgaLayer(
            f"L{i}",
            nets,
            (BgaTerminal(f"a{i}", "pad", "A", 2, 3, 1), BgaTerminal(f"b{i}", "pad", "B", 2, 8, 1)),
            (via, BgaVia("bvia", "B", 5, 8, 1)),
        )
        for i in range(2)
    )
    return BgaFixture(layers, width=12, height=12), mask | other


def test_terminal_pairs_detect_islands_shorts_and_missing_contacts():
    fixture, mask = fixture_pair()
    assert terminal_pairs([mask, mask], fixture)["false_open"] == 0
    broken = mask.copy()
    broken[3, 4] = False
    assert terminal_pairs([mask, broken], fixture)["false_open"] == 1
    short = mask.copy()
    short[3:9, 3] = True
    assert terminal_pairs([mask, short], fixture)["false_short"] == 4
    empty = np.zeros_like(mask)
    assert terminal_pairs([empty, empty], fixture)["false_open"] == 2


def test_algorithm_restores_functions_even_on_exception():
    original = operations.propose_repairs, batch_review.refresh_recommendations
    with pytest.raises(RuntimeError), algorithm("baseline"):
        assert operations.propose_repairs is not original[0]
        raise RuntimeError("interrupted benchmark")
    assert (operations.propose_repairs, batch_review.refresh_recommendations) == original


def test_pixel_metrics_separate_correct_recovery_from_false_copper():
    from pkg_re.models import Project

    fixture, mask = fixture_pair()
    layers = [
        Layer(
            id=str(i),
            name=f"L{i}",
            width=12,
            height=12,
            markers=[Marker(id=f"seed{i}", kind="pad", x=2, y=3, net="A", confirmed=True)],
        )
        for i in range(2)
    ]
    pixels = {layer.id: Pixels.blank(layer) for layer in layers}
    for px in pixels.values():
        px.observed[:] = mask
        px.observed[3, 3] = False
        px.added[3, 3] = True
        px.added[10, 10] = True
    state = State(Project(id="test", name="metric", layers=layers), pixels)
    rows = score(state, fixture, "test")
    assert all(row["missing_copper_recovered_px"] == 1 for row in rows)
    assert all(row["false_added_copper_px"] == 1 for row in rows)
    assert all(row["missing_copper_px"] == 0 for row in rows)
    assert all(row["per_net"][0]["area_error_px"] == 0 for row in rows)
