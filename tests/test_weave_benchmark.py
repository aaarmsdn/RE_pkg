"""Woven report denominators and clean-case failure gate remain honest."""

from copy import deepcopy

import pytest

from pkg_re.weave_benchmark import clean_errors, write_readme


def report_rows():
    return [
        {
            "layout": "micro32",
            "profile": "clean",
            "stage": "automatic_after_land_restore",
            "layer": f"L{index + 1}",
            "terminals": [{}] * count,
            "correct_terminals": count,
            "physical_pairs": {"false_open": 0, "false_short": 0, "expected_connected_pairs": 47},
            "false_added_copper_px": 0,
            "false_copper_px": 0,
            "missing_copper_px": 0,
            "conflict_px": 0,
        }
        for index, count in enumerate((41, 38))
    ]


def test_summary_uses_actual_terminal_count_and_stack_totals(tmp_path):
    rows = report_rows()
    rows[0].update(profile="damaged", missing_copper_px=17, false_added_copper_px=2)
    rows[1].update(profile="damaged", missing_copper_px=23, false_added_copper_px=3)
    write_readme(tmp_path, rows)
    text = (tmp_path / "README.md").read_text()
    assert "|micro32|damaged|38/38|0|0|5|40|" in text
    assert "Clean-case gate: PASS" in text


@pytest.mark.parametrize(
    "failure",
    [
        "incorrect_terminals",
        "false_open",
        "false_short",
        "false_added_copper_px",
        "false_copper_px",
        "missing_copper_px",
        "conflict_px",
    ],
)
def test_clean_gate_reports_each_actual_error(failure, tmp_path):
    rows = report_rows()
    assert clean_errors(rows) == []
    broken = deepcopy(rows)
    if failure == "incorrect_terminals":
        broken[1]["correct_terminals"] -= 1
    elif failure in {"false_open", "false_short"}:
        broken[1]["physical_pairs"][failure] = 1
    else:
        broken[1][failure] = 1
    assert clean_errors(broken) == [f"micro32/automatic_after_land_restore/L2: {failure}=1"]
    write_readme(tmp_path, broken)
    assert "Clean-case gate: FAIL" in (tmp_path / "README.md").read_text()
