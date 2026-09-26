"""Schema-completion adapter for legacy Human PRE bottleneck rows.

The approved Human scientific decision predates the strict runtime
HUMAN_RESEARCHER_PRE_V1 bottleneck row schema.  This adapter may add only
schema-required metadata that was absent from the legacy row; it must never
invent scientific estimates, evidence, counterevidence, or costs.

Completion policy:
- preserve all pre-existing scientific fields exactly;
- use UNKNOWN for unregistered value/risk classes;
- use null for unregistered resource estimates;
- use empty evidence/counterevidence arrays rather than fabricate references;
- include explicit basis text that records the lack of a registered
  bottleneck-level estimate.

The source Reference Trace remains bound to the legacy Human PRE candidate.
This adapter is used only at the runtime freeze boundary.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib

from pchsi.reference_loop.canonical import canonical_json_bytes
from pchsi.cognitive_runtime.researcher import finalize_human_pre


_ADDED_KEYS = (
    "evidence_sha256s",
    "counterevidence_sha256s",
    "expected_value_class",
    "expected_value_basis",
    "expected_environment_steps",
    "expected_model_logical_calls",
    "expected_transport_attempts",
    "expected_gpu_hours",
    "expected_api_cost_usd",
    "risk_class",
    "risk_basis",
)

_VALUE_BASIS = (
    "No bottleneck-level expected-value class was registered in the approved "
    "Human scientific adjudication. Runtime schema completion preserves this "
    "quantity as UNKNOWN and does not infer it from state-level repair scores."
)
_RISK_BASIS = (
    "No bottleneck-level risk class was registered in the approved Human "
    "scientific adjudication. Runtime schema completion preserves this "
    "quantity as UNKNOWN and does not infer it from repair-level Harm estimates."
)


def _complete_bottleneck(row: Mapping[str, object]) -> dict[str, object]:
    forbidden_overlap = sorted(set(row).intersection(_ADDED_KEYS))
    if forbidden_overlap:
        raise ValueError(
            "legacy bottleneck unexpectedly already contains completion fields: "
            + repr(forbidden_overlap)
        )

    out = dict(row)
    out.update(
        {
            "evidence_sha256s": [],
            "counterevidence_sha256s": [],
            "expected_value_class": "UNKNOWN",
            "expected_value_basis": _VALUE_BASIS,
            "expected_environment_steps": None,
            "expected_model_logical_calls": None,
            "expected_transport_attempts": None,
            "expected_gpu_hours": None,
            "expected_api_cost_usd": None,
            "risk_class": "UNKNOWN",
            "risk_basis": _RISK_BASIS,
        }
    )
    return out


def complete_human_pre_runtime_schema_v1(
    legacy_human_pre: Mapping[str, object],
) -> tuple[dict[str, object], dict[str, object]]:
    rows = legacy_human_pre.get("candidate_bottlenecks")
    if not isinstance(rows, list) or not rows:
        raise ValueError("legacy Human PRE lacks candidate_bottlenecks")

    completed = dict(legacy_human_pre)
    completed["candidate_bottlenecks"] = [
        _complete_bottleneck(row)
        if isinstance(row, Mapping)
        else (_ for _ in ()).throw(
            TypeError("candidate bottleneck must be object")
        )
        for row in rows
    ]

    # Validate the actual runtime contract before anything is written.
    finalized = finalize_human_pre(completed)

    # The finalizer adds only schema identity/version and pre_record_sha256.
    # Return the input payload, not the finalized record, because freeze_pre()
    # remains the sole write/identity authority.
    source_bytes = canonical_json_bytes(dict(legacy_human_pre))
    completed_bytes = canonical_json_bytes(completed)

    receipt = {
        "schema_id": "HUMAN_PRE_RUNTIME_SCHEMA_COMPLETION_RECEIPT_V1",
        "schema_version": 1,
        "source_human_pre_candidate_sha256": hashlib.sha256(
            source_bytes
        ).hexdigest(),
        "completed_human_pre_candidate_sha256": hashlib.sha256(
            completed_bytes
        ).hexdigest(),
        "candidate_bottleneck_count": len(rows),
        "added_fields_per_bottleneck": list(_ADDED_KEYS),
        "scientific_fields_preserved": True,
        "invented_evidence_refs": False,
        "invented_counterevidence_refs": False,
        "invented_expected_value": False,
        "invented_risk": False,
        "invented_cost": False,
        "unknown_value_and_risk_policy": "EXPLICIT_UNKNOWN",
        "unregistered_cost_policy": "NULL",
        "runtime_schema_validation_passed": True,
        "finalized_preview_pre_record_sha256": finalized[
            "pre_record_sha256"
        ],
    }
    return completed, receipt
