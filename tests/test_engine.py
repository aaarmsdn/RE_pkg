import numpy as np
import pytest

from pkg_re.engine import (
    SegmentationOptions,
    connected_regions,
    mask_polygons,
    propose_repairs,
    segment_copper,
    stroke_mask,
)


def test_three_pixel_traces_remain_separate():
    # Given three narrow traces under varying brightness.
    image = np.full((22, 40, 3), 25, dtype=np.uint8)
    for y, color in [(2, (190, 140, 60)), (8, (110, 85, 35)), (14, (235, 210, 145))]:
        image[y : y + 3, 2:38] = color
    # When
    mask = segment_copper(image, SegmentationOptions())
    # Then
    assert mask.sum() == 3 * 3 * 36
    assert len(connected_regions(mask)[1]) == 3


def test_annotation_excluded_even_on_copper():
    # Given
    image = np.full((8, 8, 3), (200, 160, 70), dtype=np.uint8)
    image[2:4, 2:6] = (130, 255, 20)
    # When
    mask = segment_copper(image, SegmentationOptions())
    # Then
    assert mask.sum() == 56
    assert not mask[2:4, 2:6].any()


def test_hole_proposal_preserves_protected_antipad_and_input():
    # Given
    observed = np.zeros((30, 40), dtype=bool)
    observed[2:28, 2:38] = True
    observed[5:8, 5:8] = False
    observed[16:20, 20:24] = False
    protected = np.zeros_like(observed)
    protected[17, 21] = True
    before = observed.copy()
    # When
    proposals = propose_repairs(observed, protected, SegmentationOptions())
    # Then
    fills = [p for p in proposals if p.kind == "plane_hole_fill"]
    assert len(fills) == 1
    assert fills[0].pixels == 9
    assert fills[0].bbox == (5, 5, 3, 3)
    assert not any((p.mask & protected).any() for p in proposals)
    assert not any(p.mask[16:20, 20:24].any() for p in proposals)
    assert not any((p.mask & observed).any() for p in proposals)
    np.testing.assert_array_equal(observed, before)


@pytest.mark.parametrize("gap", [1, 3])
def test_plane_scratch_is_proposed_without_automatic_acceptance(gap):
    # Given
    observed = np.zeros((22, 30), dtype=bool)
    observed[2:20, 2:28] = True
    observed[2:20, 14 : 14 + gap] = False
    before = observed.copy()
    # When
    proposals = propose_repairs(observed, np.zeros_like(observed), SegmentationOptions(max_gap=gap))
    # Then
    assert any(p.kind == "reconnect" and p.mask[10, 14] for p in proposals)
    assert len(connected_regions(observed)[1]) == 2
    np.testing.assert_array_equal(observed, before)


def test_gap_wider_than_limit_not_proposed():
    # Given
    observed = np.zeros((9, 30), dtype=bool)
    observed[3:6, 2:10] = True
    observed[3:6, 16:25] = True
    # When
    proposals = propose_repairs(observed, np.zeros_like(observed), SegmentationOptions(max_gap=4))
    # Then
    assert proposals == []


def test_diagonal_contact_stays_two_regions():
    # Given
    mask = np.eye(2, dtype=bool)
    # When
    labels, regions = connected_regions(mask)
    # Then
    assert [r.pixels for r in regions] == [1, 1]
    assert labels[0, 0] != labels[1, 1]


def test_pixel_polygons_preserve_area_hole_and_disconnected_pixel():
    # Given
    mask = np.zeros((10, 12), dtype=bool)
    mask[1:8, 2:10] = True
    mask[3:5, 4:7] = False
    mask[9, 11] = True
    # When
    polygons = mask_polygons(mask)
    # Then
    assert sum(p.area for p in polygons) == 51
    assert len(polygons) == 2
    assert sum(len(p.holes) for p in polygons) == 1
    assert min(x for p in polygons for x, _ in p.exterior) == 2
    assert max(x for p in polygons for x, _ in p.exterior) == 12


def test_affine_pixel_area_uses_absolute_determinant():
    # Given
    mask = np.ones((2, 3), dtype=bool)
    # When
    polygons = mask_polygons(mask, (2, 1, 0.5, -3, 10, 20))
    # Then
    assert sum(p.area for p in polygons) == pytest.approx(6 * 6.5)
    assert (10, 20) in polygons[0].exterior


def test_brush_connects_points_roundly_in_native_coordinates():
    # Given
    shape = (20, 20)
    # When
    mask = stroke_mask(shape, [(3, 8), (12, 8), (12, 13)], 2)
    # Then
    assert mask.dtype == bool
    assert mask[8, 1] and mask[13, 14]
    assert mask[8, 6] and mask[11, 12]
    assert not mask[5, 6]
    assert not mask[6, 1]


def test_empty_mask_and_empty_stroke():
    # Given
    mask = np.zeros((4, 5), dtype=bool)
    # When
    result = (mask_polygons(mask), connected_regions(mask)[1], stroke_mask(mask.shape, [], 1))
    # Then
    assert result[0] == [] and result[1] == []
    assert not result[2].any()


def test_candidate_cap_and_compact_storage():
    # Given
    mask = np.ones((100, 100), dtype=bool)
    mask[2:98:5, 2:98:5] = False
    # When
    proposals = propose_repairs(mask, np.zeros_like(mask), SegmentationOptions())
    # Then
    assert len(proposals) == 100
    assert sum(p._patch.nbytes for p in proposals) == 100
    assert all(p.pixels == 1 and p.mask.shape == mask.shape for p in proposals)


def test_protected_scratch_blocks_connected_repair_patch():
    # Given a scratch with an explicit dielectric barrier.
    mask = np.zeros((20, 20), dtype=bool)
    mask[2:18, 2:18] = True
    mask[2:18, 10] = False
    protected = np.zeros_like(mask)
    protected[9:11, 10] = True
    # When
    proposals = propose_repairs(mask, protected, SegmentationOptions())
    # Then
    assert proposals == []


def test_random_pixel_cells_keep_exact_area_without_mutation():
    # Given sparse, diagonal and hole-bearing arbitrary pixel evidence.
    rng = np.random.default_rng(317)
    masks = [rng.random((12, 15)) > density for density in (0.1, 0.4, 0.8)]
    originals = [mask.copy() for mask in masks]
    # When
    results = [mask_polygons(mask) for mask in masks]
    # Then
    for mask, original, polygons in zip(masks, originals, results, strict=True):
        assert sum(p.area for p in polygons) == int(mask.sum())
        np.testing.assert_array_equal(mask, original)


def test_many_tiny_holes_do_not_hide_large_hole_or_plane_scratch():
    # Given more than 100 single-pixel defects plus high-area repairs.
    mask = np.zeros((100, 130), dtype=bool)
    mask[2:98, 2:128] = True
    mask[5:85:5, 5:55:5] = False
    mask[20:28, 65:73] = False
    mask[2:98, 90:92] = False
    before = mask.copy()
    # When
    proposals = propose_repairs(mask, np.zeros_like(mask), SegmentationOptions())
    # Then both high-impact geometries remain reviewable without altering evidence.
    assert len(proposals) == 100
    assert any(p.kind == "plane_hole_fill" and p.pixels == 64 for p in proposals)
    assert any(p.kind == "reconnect" and p.pixels == 192 for p in proposals)
    assert proposals[0].pixels == 192
    np.testing.assert_array_equal(mask, before)


def test_candidate_budget_balances_kinds_even_when_gap_areas_dominate():
    # Given 110 isolated tile planes, each with a 10px scratch and 1px hole.
    tile = np.zeros((14, 18), dtype=bool)
    tile[2:12, 2:16] = True
    tile[2:12, 9] = False
    tile[5, 5] = False
    mask = np.tile(tile, (11, 10))
    # When
    runs = [propose_repairs(mask, np.zeros_like(mask), SegmentationOptions(max_gap=1)) for _ in range(2)]
    # Then each kind gets half of the review budget, in repeatable area order.
    assert all(len(proposals) == 100 for proposals in runs)
    assert sum(p.kind == "plane_hole_fill" for p in runs[0]) == 50
    assert sum(p.kind == "reconnect" for p in runs[0]) == 50
    assert [(p.kind, p.bbox, p.pixels) for p in runs[0]] == [(p.kind, p.bbox, p.pixels) for p in runs[1]]
    assert [p.pixels for p in runs[0]] == sorted((p.pixels for p in runs[0]), reverse=True)
