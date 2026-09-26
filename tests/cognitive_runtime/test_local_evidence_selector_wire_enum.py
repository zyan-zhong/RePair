from __future__ import annotations

from collections.abc import Mapping

import pytest

from pchsi.cognitive_runtime.request_renderer import render_stage_request


def _reference(
    selector: str,
    *,
    evidence_kind: str,
) -> dict[str, str]:
    return {
        "artifact_sha256": "a" * 64,
        "evidence_kind": evidence_kind,
        "local_selector": selector,
        "authority": "DETERMINISTIC_FACT",
    }


def _catalog(
    mechanical_selector: str = "mechanical:generic_episode_facts.budget_exhaustion",
) -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_EVIDENCE_REFERENCE_CATALOG_V1",
        "evidence_pack_sha256": "a" * 64,
        "copy_policy": "EXACT_OBJECT_COPY_ONLY",
        "mechanical_selector_policy": "LEAF_ONLY_EXACT_CATALOG_MEMBER",
        "trajectory_calls": [
            _reference(
                "trajectory:0",
                evidence_kind="TRAJECTORY_CALL",
            ),
            _reference(
                "trajectory:1",
                evidence_kind="TRAJECTORY_CALL",
            ),
        ],
        "mechanical_facts": [
            _reference(
                mechanical_selector,
                evidence_kind="MECHANICAL_FACT",
            ),
        ],
        "counterexamples": [],
    }


def _repair_contract() -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_LOCAL_REPAIR_CONTRACT_V1",
        "EXACT_ACTION": {
            "exact_action": "REQUIRED_EXACT_ADMISSIBLE_COMMAND_STRING",
            "option_actions": "EMPTY_ARRAY",
            "termination_condition": "NULL",
            "trainable_rule": "NULL",
        },
        "SHORT_OPTION": {
            "exact_action": "NULL",
            "option_actions": "ARRAY_1_TO_4_FIRST_ACTION_ADMISSIBLE",
            "termination_condition": "REQUIRED_NONEMPTY_STRING",
            "trainable_rule": "NULL",
        },
        "TRAINABLE_RULE": {
            "exact_action": "NULL",
            "option_actions": "EMPTY_ARRAY",
            "termination_condition": "NULL",
            "trainable_rule": "REQUIRED_NONEMPTY_STRING",
        },
        "requires_environment_verification": True,
    }


def _projection(
    mechanical_selector: str = "mechanical:generic_episode_facts.budget_exhaustion",
) -> dict[str, object]:
    return {
        "evidence_pack_sha256": "a" * 64,
        "evidence_pack": {},
        "evidence_reference_catalog": _catalog(mechanical_selector),
        "local_repair_contract": _repair_contract(),
        "memory_pack_sha256": None,
    }


def _local_selector_enums(
    schema: Mapping[str, object],
) -> list[list[str] | None]:
    rows: list[list[str] | None] = []

    def walk(value: object) -> None:
        if isinstance(value, Mapping):
            properties = value.get("properties")
            required = value.get("required")

            if (
                isinstance(properties, Mapping)
                and isinstance(required, list)
                and {
                    "artifact_sha256",
                    "evidence_kind",
                    "local_selector",
                    "authority",
                }.issubset(set(required))
            ):
                local_selector = properties["local_selector"]
                assert isinstance(local_selector, Mapping)
                enum = local_selector.get("enum")
                rows.append(
                    list(enum)
                    if isinstance(enum, list)
                    else None
                )

            for child in value.values():
                walk(child)

        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(schema)
    return rows


def _wire_schema(
    stage_id: str,
    projection: dict[str, object],
) -> dict[str, object]:
    bundle = render_stage_request(
        stage_id=stage_id,
        projection=projection,
    )
    schema = bundle[
        "provider_request"
    ][
        "text"
    ][
        "format"
    ][
        "schema"
    ]
    assert isinstance(schema, dict)
    return schema


def test_local_wire_schema_constrains_every_selector_to_exact_catalog():
    expected = [
        "mechanical:generic_episode_facts.budget_exhaustion",
        "trajectory:0",
        "trajectory:1",
    ]

    schema = _wire_schema(
        "L-A1",
        _projection(),
    )
    rows = _local_selector_enums(schema)

    assert rows
    assert all(row == expected for row in rows)
    assert (
        "mechanical:generic_episode_facts.remaining_environment_budget"
        not in expected
    )


def test_a0_and_a1_receive_the_same_selector_allowlist():
    projection = _projection()

    a0 = _local_selector_enums(
        _wire_schema("L-A0", projection)
    )
    a1 = _local_selector_enums(
        _wire_schema("L-A1", projection)
    )

    assert a0
    assert a0 == a1


def test_selector_catalog_change_changes_wire_request_identity():
    first = render_stage_request(
        stage_id="L-A1",
        projection=_projection(
            "mechanical:generic_episode_facts.budget_exhaustion"
        ),
    )
    second = render_stage_request(
        stage_id="L-A1",
        projection=_projection(
            "mechanical:generic_episode_facts.termination_reason"
        ),
    )

    assert (
        first["request_body_sha256"]
        != second["request_body_sha256"]
    )


def test_empty_local_selector_allowlist_fails_closed():
    projection = _projection()
    projection["evidence_reference_catalog"] = {
        "schema_id": "ANALYZER_EVIDENCE_REFERENCE_CATALOG_V1",
        "evidence_pack_sha256": "a" * 64,
        "copy_policy": "EXACT_OBJECT_COPY_ONLY",
        "mechanical_selector_policy": "LEAF_ONLY_EXACT_CATALOG_MEMBER",
        "trajectory_calls": [],
        "mechanical_facts": [],
        "counterexamples": [],
    }

    with pytest.raises(
        ValueError,
        match="selector allowlist is empty",
    ):
        render_stage_request(
            stage_id="L-A1",
            projection=projection,
        )
