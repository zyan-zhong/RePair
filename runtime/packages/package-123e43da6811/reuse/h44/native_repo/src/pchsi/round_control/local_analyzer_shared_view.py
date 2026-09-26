"""Shared Local-Analyzer model-facing view for training and shadow runtime.

This module materializes the exact Analyzer view validated by Stage6W.

Scientific-stage routing:
- L-A0 / L-A1: Stage6O V1 semantic projection followed by Stage6Q V2 exact
  structural factorization.
- every other Analyzer stage: preserve the original user projection.

The routing does not inspect assistant targets, token lengths, example hashes,
or training-only state, so the same function is valid for Local Analyzer
training and Local Analyzer shadow/runtime.

Source evidence remains immutable. No truncation, chunking, list sampling, or
example dropping is performed.
"""
from __future__ import annotations

import copy
import json
import re
from collections.abc import Mapping
from typing import Any

_SHA_RE = re.compile(r"^[0-9a-f]{64}$")

LOCAL_ANALYZER_COMPACT_STAGES_V1 = frozenset({"L-A0", "L-A1"})

_STAGE6O_SCIENTIFIC_SOURCE_SHA256 = (
    "dd5fc30b444090b0169af61fc6979d59da60b4dd7fa2c44964a210dd0e458370"
)
_STAGE6Q_ANALYZER_SOURCE_SHA256 = (
    "39798567157dff038a80b852832e6162aafd9bf305a7286404feb4ffbf17c5d3"
)


def _mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be object")
    return dict(value)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _value_table(values: list[object]) -> tuple[list[object], list[int]]:
    """Dictionary-encode exact canonical-JSON values without information loss."""
    by_text: dict[str, object] = {}
    for value in values:
        text = _canonical_json(value)
        by_text.setdefault(text, copy.deepcopy(value))
    ordered = sorted(by_text)
    table = [by_text[text] for text in ordered]
    index = {text: position for position, text in enumerate(ordered)}
    refs = [index[_canonical_json(value)] for value in values]
    return table, refs


def _compact_analyzer_stage6o_v1(
    user_projection: Mapping[str, object],
) -> dict[str, object]:
    """Stage6O Analyzer V1 semantics, materialized verbatim in repository form."""
    src = dict(user_projection)
    pack = _mapping(src.get("evidence_pack"), "evidence_pack")
    trajectory = pack.get("trajectory")
    if not isinstance(trajectory, list):
        raise ValueError("Analyzer evidence_pack.trajectory must be array")

    compact_rows: list[dict[str, object]] = []
    omitted_counts = {
        "public_task_goal": 0,
        "executed_history": 0,
        "policy_prompt_text": 0,
    }
    for index, raw in enumerate(trajectory):
        row = _mapping(raw, f"trajectory[{index}]")
        out: dict[str, object] = {}
        for key, value in row.items():
            if key in omitted_counts:
                omitted_counts[key] += 1
                continue
            out[key] = copy.deepcopy(value)
        compact_rows.append(out)

    compact_pack = dict(pack)
    compact_pack["trajectory"] = compact_rows

    return {
        "schema_id": "LOCAL_RI_ANALYZER_COMPACT_VIEW_V1",
        "source_projection_schema": "ANALYZER_LOCAL_PROJECTION",
        "source_evidence_pack_sha256": src.get("evidence_pack_sha256"),
        "evidence_pack_view": compact_pack,
        "evidence_reference_catalog": copy.deepcopy(
            src.get("evidence_reference_catalog")
        ),
        "local_repair_contract": copy.deepcopy(
            src.get("local_repair_contract")
        ),
        "memory_pack_sha256": src.get("memory_pack_sha256"),
        "projection_contract": {
            "source_evidence_pack_remains_immutable": True,
            "trajectory_row_count_preserved": len(compact_rows),
            "omitted_per_call_fields": list(omitted_counts),
            "omitted_field_occurrence_counts": omitted_counts,
            "observations_preserved": True,
            "admissible_commands_preserved": True,
            "raw_model_responses_preserved": True,
            "executed_actions_preserved": True,
            "resulting_state_preserved": True,
            "budget_state_preserved": True,
            "mechanical_evidence_preserved": True,
            "evidence_reference_catalog_preserved": True,
            "automatic_truncation_used": False,
            "automatic_chunking_used": False,
            "example_drop_used": False,
        },
    }


def _compact_evidence_reference_catalog_v2(
    catalog: Mapping[str, object],
) -> dict[str, object]:
    src = dict(catalog)
    if src.get("schema_id") != "ANALYZER_EVIDENCE_REFERENCE_CATALOG_V1":
        raise ValueError("unexpected evidence reference catalog schema")
    pack_sha = src.get("evidence_pack_sha256")
    if not isinstance(pack_sha, str) or _SHA_RE.fullmatch(pack_sha) is None:
        raise ValueError("catalog evidence_pack_sha256 invalid")

    expected = {
        "trajectory_calls": ("TRAJECTORY_CALL", "DETERMINISTIC_FACT"),
        "mechanical_facts": ("MECHANICAL_FACT", "DETERMINISTIC_FACT"),
        "counterexamples": ("COUNTEREXAMPLE", "SEMANTIC_HYPOTHESIS"),
    }
    selectors: dict[str, list[str]] = {}
    for field, (kind, authority) in expected.items():
        rows = src.get(field)
        if not isinstance(rows, list):
            raise ValueError(f"catalog {field} must be array")
        out: list[str] = []
        for raw in rows:
            row = _mapping(raw, field)
            if row.get("artifact_sha256") != pack_sha:
                raise ValueError("catalog pack identity mismatch")
            if row.get("evidence_kind") != kind:
                raise ValueError("catalog evidence kind mismatch")
            if row.get("authority") != authority:
                raise ValueError("catalog authority mismatch")
            selector = row.get("local_selector")
            if not isinstance(selector, str) or not selector:
                raise ValueError("catalog selector invalid")
            out.append(selector)
        selectors[field] = out

    return {
        "schema_id": "ANALYZER_EVIDENCE_REFERENCE_CATALOG_COMPACT_V2",
        "source_schema_id": src["schema_id"],
        "evidence_pack_sha256": pack_sha,
        "copy_policy": src.get("copy_policy"),
        "mechanical_selector_policy": src.get(
            "mechanical_selector_policy"
        ),
        "trajectory_selectors": selectors["trajectory_calls"],
        "mechanical_selectors": selectors["mechanical_facts"],
        "counterexample_selectors": selectors["counterexamples"],
        "selector_contract": {
            "trajectory": {
                "evidence_kind": "TRAJECTORY_CALL",
                "authority": "DETERMINISTIC_FACT",
            },
            "mechanical": {
                "evidence_kind": "MECHANICAL_FACT",
                "authority": "DETERMINISTIC_FACT",
            },
            "counterexample": {
                "evidence_kind": "COUNTEREXAMPLE",
                "authority": "SEMANTIC_HYPOTHESIS",
            },
        },
    }


def _reconstruct_evidence_reference_catalog_v1(
    compact: Mapping[str, object],
) -> dict[str, object]:
    src = dict(compact)
    if src.get("schema_id") != (
        "ANALYZER_EVIDENCE_REFERENCE_CATALOG_COMPACT_V2"
    ):
        raise ValueError("compact catalog schema mismatch")
    pack = src["evidence_pack_sha256"]

    def rows(
        selectors: object,
        kind: str,
        authority: str,
    ) -> list[dict[str, str]]:
        if not isinstance(selectors, list):
            raise ValueError("selector array required")
        return [
            {
                "artifact_sha256": str(pack),
                "evidence_kind": kind,
                "local_selector": str(selector),
                "authority": authority,
            }
            for selector in selectors
        ]

    return {
        "schema_id": "ANALYZER_EVIDENCE_REFERENCE_CATALOG_V1",
        "evidence_pack_sha256": pack,
        "copy_policy": src.get("copy_policy"),
        "mechanical_selector_policy": src.get(
            "mechanical_selector_policy"
        ),
        "trajectory_calls": rows(
            src.get("trajectory_selectors"),
            "TRAJECTORY_CALL",
            "DETERMINISTIC_FACT",
        ),
        "mechanical_facts": rows(
            src.get("mechanical_selectors"),
            "MECHANICAL_FACT",
            "DETERMINISTIC_FACT",
        ),
        "counterexamples": rows(
            src.get("counterexample_selectors"),
            "COUNTEREXAMPLE",
            "SEMANTIC_HYPOTHESIS",
        ),
    }


_TRAJECTORY_FACTORED_FIELDS_V2 = (
    "observation_before",
    "admissible_commands",
    "resulting_observation",
    "resulting_admissible_commands",
    "budget_before",
    "budget_after",
)


def _compact_analyzer_stage6q_v2(
    stage6o_candidate: Mapping[str, object],
) -> dict[str, object]:
    """Stage6Q Analyzer V2 exact structural factorization."""
    src = dict(stage6o_candidate)
    if src.get("schema_id") != "LOCAL_RI_ANALYZER_COMPACT_VIEW_V1":
        raise ValueError("expected Stage6O Analyzer compact view V1")

    pack = _mapping(
        src.get("evidence_pack_view"),
        "evidence_pack_view",
    )
    trajectory = pack.get("trajectory")
    if not isinstance(trajectory, list):
        raise ValueError("trajectory must be array")

    rows = [_mapping(row, "trajectory row") for row in trajectory]
    tables: dict[str, list[object]] = {}
    refs_by_field: dict[str, list[int]] = {}

    for field in _TRAJECTORY_FACTORED_FIELDS_V2:
        values = [copy.deepcopy(row.get(field)) for row in rows]
        table, refs = _value_table(values)
        tables[field] = table
        refs_by_field[field] = refs

    compact_rows: list[dict[str, object]] = []
    for index, row in enumerate(rows):
        out = {
            key: copy.deepcopy(value)
            for key, value in row.items()
            if key not in _TRAJECTORY_FACTORED_FIELDS_V2
        }
        for field in _TRAJECTORY_FACTORED_FIELDS_V2:
            out[field + "_ref"] = refs_by_field[field][index]
        compact_rows.append(out)

    compact_pack = dict(pack)
    compact_pack["trajectory"] = compact_rows
    compact_pack["trajectory_value_tables_v2"] = tables

    original_catalog = _mapping(
        src.get("evidence_reference_catalog"),
        "evidence_reference_catalog",
    )
    compact_catalog = _compact_evidence_reference_catalog_v2(
        original_catalog
    )

    result = {
        "schema_id": "LOCAL_RI_ANALYZER_COMPACT_VIEW_V2",
        "source_stage6o_schema_id": src.get("schema_id"),
        "source_evidence_pack_sha256": src.get(
            "source_evidence_pack_sha256"
        ),
        "evidence_pack_view": compact_pack,
        "evidence_reference_catalog": compact_catalog,
        "local_repair_contract": copy.deepcopy(
            src.get("local_repair_contract")
        ),
        "memory_pack_sha256": src.get("memory_pack_sha256"),
        "projection_contract": {
            "source_evidence_pack_remains_immutable": True,
            "stage6o_v1_semantics_preserved": True,
            "trajectory_row_count_preserved": len(rows),
            "factored_fields": list(
                _TRAJECTORY_FACTORED_FIELDS_V2
            ),
            "exact_value_dictionary_encoding": True,
            "evidence_catalog_columnar_normalization": True,
            "source_field_omission_authorized": False,
            "automatic_truncation_used": False,
            "automatic_chunking_used": False,
            "example_drop_used": False,
        },
    }

    reconstructed_rows: list[dict[str, object]] = []
    for row in compact_rows:
        out = {
            key: copy.deepcopy(value)
            for key, value in row.items()
            if not key.endswith("_ref")
        }
        for field in _TRAJECTORY_FACTORED_FIELDS_V2:
            ref = row[field + "_ref"]
            if type(ref) is not int:
                raise ValueError(
                    "trajectory value ref must be integer"
                )
            out[field] = copy.deepcopy(tables[field][ref])
        reconstructed_rows.append(out)

    if _canonical_json(reconstructed_rows) != _canonical_json(rows):
        raise ValueError(
            "Analyzer V2 trajectory reconstruction mismatch"
        )

    reconstructed_catalog = (
        _reconstruct_evidence_reference_catalog_v1(
            compact_catalog
        )
    )
    if _canonical_json(reconstructed_catalog) != _canonical_json(
        original_catalog
    ):
        raise ValueError(
            "Analyzer V2 evidence catalog reconstruction mismatch"
        )

    return result


def build_local_analyzer_shared_user_projection_v1(
    *,
    original_user_projection: Mapping[str, object],
    stage_id: str,
) -> dict[str, object]:
    """Return the one model-facing Analyzer view for train and Local shadow."""
    if not isinstance(stage_id, str) or not stage_id:
        raise ValueError("stage_id required")

    source = copy.deepcopy(dict(original_user_projection))
    if stage_id not in LOCAL_ANALYZER_COMPACT_STAGES_V1:
        return source

    return _compact_analyzer_stage6q_v2(
        _compact_analyzer_stage6o_v1(source)
    )
