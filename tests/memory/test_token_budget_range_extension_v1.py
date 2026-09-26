from __future__ import annotations

import pytest

from pchsi.memory import token_budget_contract as module


FM1_COUNTS = (
    360,
    382,
    403,
    412,
    414,
    414,
    415,
    421,
    421,
    434,
    451,
    490,
    505,
    616,
    682,
    718,
    749,
    805,
    818,
    836,
    840,
    846,
    850,
    867,
    3073,
    3626,
    4061,
    4437,
    5017,
    5789,
)

LIBRARY_COUNTS = (
    360,
    371,
    386,
    389,
    390,
    395,
    396,
    402,
    409,
    420,
)


def test_extended_single_record_candidate_grid():
    assert module.SINGLE_RECORD_CANDIDATES_V1 == (
        256,
        384,
        512,
        640,
        768,
        1024,
        2048,
        4096,
    )

    assert (
        module.MAX_SUPPORTED_SINGLE_RECORD_HARD_CEILING_V1
        == 4096
    )


def test_frozen_empirical_fm1_lengths_select_4096():
    assert module.required_coverage_count_v1(
        len(FM1_COUNTS)
    ) == 27

    selected = module.choose_smallest_ceiling_v1(
        observed_token_counts=FM1_COUNTS,
        candidates=module.SINGLE_RECORD_CANDIDATES_V1,
        coverage_target=module.COVERAGE_TARGET_V1,
    )

    assert selected == 4096

    assert sum(
        value <= 4096
        for value in FM1_COUNTS
    ) == 27

    assert sum(
        value <= 2048
        for value in FM1_COUNTS
    ) == 24


def test_frozen_library_lengths_still_select_512():
    selected = module.choose_smallest_ceiling_v1(
        observed_token_counts=LIBRARY_COUNTS,
        candidates=module.LIBRARY_TOTAL_CANDIDATES_V1,
        coverage_target=module.COVERAGE_TARGET_V1,
    )

    assert selected == 512

    assert all(
        value <= 512
        for value in LIBRARY_COUNTS
    )


def test_range_extension_remains_fail_closed_above_4096():
    with pytest.raises(ValueError):
        module.choose_smallest_ceiling_v1(
            observed_token_counts=(5000,) * 30,
            candidates=module.SINGLE_RECORD_CANDIDATES_V1,
            coverage_target=module.COVERAGE_TARGET_V1,
        )
