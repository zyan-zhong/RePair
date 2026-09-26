from __future__ import annotations

import copy

import pytest

from pchsi.evaluation.schema_contract import (
    load_schema,
    validate_payload_against_schema,
    validate_schema_definition,
)


def _public_payload() -> dict[str, object]:
    digest = "a" * 64
    return {
        "schema_id": "E1_PUBLIC_TRANSITION_RECORD_V1",
        "schema_version": 1,
        "scheduled_cell_id": "e1-t0000-s0000000017",
        "execution_attempt_id": "e1-t0000-s0000000017-a000",
        "model_call_index": 0,
        "environment_step_index": 0,
        "submitted_action": "look",
        "pre_action_observation": "before",
        "pre_action_observation_sha256": digest,
        "pre_action_admissible_commands": ["look", "inventory"],
        "pre_action_admissible_commands_sha256": digest,
        "resulting_observation": "after",
        "resulting_observation_sha256": digest,
        "resulting_admissible_commands": ["inventory", "go north"],
        "resulting_admissible_commands_sha256": digest,
        "done": False,
        "won": False,
        "score": 0,
        "pre_action_visibility": "POLICY_VISIBLE_BEFORE_ACTION",
        "resulting_visibility": "POST_ACTION_PUBLIC_AUDIT_ONLY",
    }


def test_unknown_and_missing_fields_are_rejected() -> None:
    payload = _public_payload()
    validate_payload_against_schema(
        schema_id="E1_PUBLIC_TRANSITION_RECORD_V1",
        payload=payload,
    )

    with_unknown = dict(payload)
    with_unknown["unknown"] = 1
    with pytest.raises(ValueError, match="unknown"):
        validate_payload_against_schema(
            schema_id="E1_PUBLIC_TRANSITION_RECORD_V1",
            payload=with_unknown,
        )

    missing = dict(payload)
    del missing["won"]
    with pytest.raises(ValueError, match="required"):
        validate_payload_against_schema(
            schema_id="E1_PUBLIC_TRANSITION_RECORD_V1",
            payload=missing,
        )


def test_schema_validator_rejects_unsupported_keywords() -> None:
    schema = copy.deepcopy(
        load_schema("E1_PUBLIC_TRANSITION_RECORD_V1")
    )
    schema["unevaluatedProperties"] = False

    with pytest.raises(ValueError, match="unsupported"):
        validate_schema_definition(schema)


def test_schema_validator_is_strict_about_bool_integer_and_finite_number() -> None:
    payload = _public_payload()
    payload["model_call_index"] = True

    with pytest.raises(ValueError, match="integer"):
        validate_payload_against_schema(
            schema_id="E1_PUBLIC_TRANSITION_RECORD_V1",
            payload=payload,
        )

    payload = _public_payload()
    payload["score"] = float("nan")

    with pytest.raises(ValueError, match="finite"):
        validate_payload_against_schema(
            schema_id="E1_PUBLIC_TRANSITION_RECORD_V1",
            payload=payload,
        )
