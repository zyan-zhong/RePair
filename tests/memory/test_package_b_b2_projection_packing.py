from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from pchsi.memory.projection_packing import (
    PackablePolicyViewV1,
    ProjectionPackingModeV1,
    pack_policy_views_v1,
)


def _helpers():
    path = Path(
        "tests/memory/package_b_direct_test_helpers.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_package_b_direct_helpers_b2",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _CountByItemTokenizer:
    tokenizer_id = "packing"
    tokenizer_revision = "v1"

    def count_tokens(self, text: str) -> int:
        # Exact test uses a deterministic stand-in. Array serialization
        # contains one "payload-" marker per whole record.
        return text.count("payload-") * 250


def _view(index: int):
    return PackablePolicyViewV1(
        representation_id=f"rep-{index}",
        policy_visible_payload={
            "failure_cue": f"payload-{index}",
        },
        policy_visible_token_count=250,
        build_disposition="ELIGIBLE",
        memory_lineage_id=f"{index + 1:064x}",
        record_version=1,
    )


def test_b2_direct_requires_exactly_one_whole_view():
    contract = _helpers().token_budget_contract()
    result = pack_policy_views_v1(
        mode=ProjectionPackingModeV1.DIRECT_SINGLE_RECORD,
        views=(_view(0),),
        tokenizer=_CountByItemTokenizer(),
        token_budget_contract=contract,
    )
    assert len(result.packed_views) == 1
    assert result.packed_token_count == 250
    assert result.hard_ceiling == 640

    with pytest.raises(ValueError):
        pack_policy_views_v1(
            mode=ProjectionPackingModeV1.DIRECT_SINGLE_RECORD,
            views=(),
            tokenizer=_CountByItemTokenizer(),
            token_budget_contract=contract,
        )


def test_b2_library_stops_before_first_nonfitting_whole_record():
    contract = _helpers().token_budget_contract()
    result = pack_policy_views_v1(
        mode=ProjectionPackingModeV1.LIBRARY,
        views=(
            _view(0),
            _view(1),
            _view(2),
        ),
        tokenizer=_CountByItemTokenizer(),
        token_budget_contract=contract,
    )

    # 3x250=750 fits the frozen test contract's 768 library ceiling.
    assert len(result.packed_views) == 3
    assert result.packed_token_count == 750
    assert result.stopped_before_representation_id is None


class _LargeThirdTokenizer:
    tokenizer_id = "packing-large-third"
    tokenizer_revision = "v1"

    def count_tokens(self, text: str) -> int:
        count = text.count("payload-")
        return {
            0: 0,
            1: 250,
            2: 500,
            3: 900,
        }[count]


def test_b2_library_never_partially_truncates_third_record():
    contract = _helpers().token_budget_contract()
    result = pack_policy_views_v1(
        mode=ProjectionPackingModeV1.LIBRARY,
        views=(
            _view(0),
            _view(1),
            _view(2),
        ),
        tokenizer=_LargeThirdTokenizer(),
        token_budget_contract=contract,
    )
    assert tuple(
        item.representation_id
        for item in result.packed_views
    ) == ("rep-0", "rep-1")
    assert result.packed_token_count == 500
    assert result.stopped_before_representation_id == "rep-2"
