from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from pchsi.evaluation.canonical_evidence import strict_json_loads
from pchsi.evaluation.schema_contract import validate_schema_definition
from pchsi.memory.projection_common import (
    ProjectionTokenCountV1,
)


def _fm1_helpers():
    path = Path(
        "tests/memory/test_fm1_matched_raw_view.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_token_budget_fm1_existing_helpers",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_projection_envelope_accepts_pre_outcome_calibrated_ceiling_range():
    value = ProjectionTokenCountV1(
        tokenizer_id="tok",
        tokenizer_revision="rev",
        policy_visible_token_count=600,
        hard_ceiling=640,
    )
    assert value.hard_ceiling == 640

    maximum = ProjectionTokenCountV1(
        tokenizer_id="tok",
        tokenizer_revision="rev",
        policy_visible_token_count=4096,
        hard_ceiling=4096,
    )
    assert maximum.hard_ceiling == 4096

    with pytest.raises(ValueError):
        ProjectionTokenCountV1(
            tokenizer_id="tok",
            tokenizer_revision="rev",
            policy_visible_token_count=1,
            hard_ceiling=4097,
        )


def test_fm1_complete_window_overflow_never_drops_optional_events():
    h = _fm1_helpers()
    module = h._load_target()
    helpers = h._helpers()
    builder = helpers._load_target()

    experience = h._hardening_b_multi_event_experience()
    record = h._eligible(
        helpers._record(
            builder,
            experience=experience,
        )
    )
    tokenizer = h._HardeningBPackingTokenizer()

    result = module.build_fm1_matched_raw_episodic_view_v1(
        record=record,
        experience=experience,
        tokenizer=tokenizer,
        hard_ceiling=256,
    )

    assert (
        result.build_disposition.value
        == "PROJECTION_INELIGIBLE_TOKEN_BUDGET"
    )
    assert result.policy_visible_payload is None
    assert result.token_count is not None
    assert result.token_count.policy_visible_token_count == 400

    # Only the complete registered 2..6 window may be measured. Historical
    # mandatory-anchor / event-dropping fallback calls are forbidden.
    assert tuple(
        indices
        for indices, _ in tokenizer.seen
    ) == ((2, 3, 4, 5, 6),)


def test_projection_schemas_accept_calibrated_ceiling_range():
    for raw_path in (
        "configs/memory/schemas/fm1_matched_raw_episodic_view_v1.json",
        "configs/memory/schemas/failure_memory_policy_projection_v1.json",
    ):
        payload = strict_json_loads(
            Path(raw_path).read_bytes()
        )
        validate_schema_definition(payload)
        hard = (
            payload["properties"]["token_count"]
            ["properties"]["hard_ceiling"]
        )
        assert hard["maximum"] == 4096
