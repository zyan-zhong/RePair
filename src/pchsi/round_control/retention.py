from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .common import hashed_payload


class ArtifactKindV1(str, Enum):
    CODE = "CODE"
    SCHEMA = "SCHEMA"
    CONTRACT = "CONTRACT"
    TEST = "TEST"
    INFRASTRUCTURE = "INFRASTRUCTURE"
    TASK_SPECIFIC_REPAIR = "TASK_SPECIFIC_REPAIR"
    FAILURE_MEMORY_CONTENT = "FAILURE_MEMORY_CONTENT"
    STRONG_STRUCTURED_TRACE = "STRONG_STRUCTURED_TRACE"
    LOCAL_STRUCTURED_TRACE = "LOCAL_STRUCTURED_TRACE"
    VERIFIED_TRAINING_EVIDENCE = "VERIFIED_TRAINING_EVIDENCE"
    BENCHMARK_RESULT = "BENCHMARK_RESULT"


@dataclass(frozen=True)
class RetentionDecisionV1:
    allowed: bool
    destination: str
    reason: str
    decision_sha256: str


_ALWAYS_REUSABLE = {
    ArtifactKindV1.CODE,
    ArtifactKindV1.SCHEMA,
    ArtifactKindV1.CONTRACT,
    ArtifactKindV1.TEST,
    ArtifactKindV1.INFRASTRUCTURE,
}


def decide_cross_round_retention(
    *,
    origin_round_role: str,
    artifact_kind: ArtifactKindV1,
    access_class: str,
) -> RetentionDecisionV1:
    if artifact_kind in _ALWAYS_REUSABLE:
        allowed = True
        destination = "CROSS_ROUND_ENGINEERING_ASSET"
        reason = "generic engineering asset is reusable"

    elif origin_round_role == "PILOT_ENGINEERING_ROUND_V1":
        allowed = False
        destination = "PILOT_ARCHIVE_ONLY"
        reason = "pilot semantic artifacts are excluded from clean experiment"

    elif artifact_kind is ArtifactKindV1.STRONG_STRUCTURED_TRACE:
        if access_class in {
            "TRAIN_UPDATE",
            "TRAIN_REFERENCE_ROUND",
            "TRAIN_RESEARCH_INTELLIGENCE",
        }:
            allowed = True
            destination = "LOCALIZATION_SUPERVISION"
            reason = (
                "registered train-side Strong reference/update trace retained "
                "for local Analyzer/Research Planner distillation"
            )
        elif access_class == "TRAIN_AUDIT":
            allowed = True
            destination = "LOCAL_SHADOW_AUDIT_HISTORY"
            reason = (
                "TRAIN_AUDIT Strong trace retained for takeover audit only; "
                "it is not localization supervision"
            )
        else:
            raise ValueError(
                "Strong structured trace may enter localization only from "
                "TRAIN_UPDATE, TRAIN_REFERENCE_ROUND, or "
                "TRAIN_RESEARCH_INTELLIGENCE; TRAIN_AUDIT is audit-history only"
            )

    elif artifact_kind is ArtifactKindV1.LOCAL_STRUCTURED_TRACE:
        if not access_class.startswith("TRAIN_"):
            raise ValueError("local trace must be train-side")
        allowed = True
        destination = "LOCAL_SHADOW_AUDIT_HISTORY"
        reason = "local shadow trace retained for takeover audit"

    elif artifact_kind is ArtifactKindV1.VERIFIED_TRAINING_EVIDENCE:
        if access_class != "TRAIN_UPDATE":
            raise ValueError("verified training evidence must originate in TRAIN_UPDATE")
        allowed = True
        destination = "POLICY_TRAINING_EVIDENCE"
        reason = "verified clean-train evidence may be internalized"

    elif artifact_kind is ArtifactKindV1.FAILURE_MEMORY_CONTENT:
        if access_class not in {
            "TRAIN_UPDATE",
            "TRAIN_REFERENCE_ROUND",
            "TRAIN_AUTONOMOUS_ROUND",
        }:
            raise ValueError("failure memory must stay train-side")
        allowed = True
        destination = "CROSS_ROUND_FAILURE_MEMORY"
        reason = "train-side procedural failure experience may persist"

    elif artifact_kind is ArtifactKindV1.BENCHMARK_RESULT:
        allowed = False
        destination = "SEALED_BENCHMARK_ARCHIVE"
        reason = "benchmark result cannot enter adaptive loop"

    else:
        allowed = False
        destination = "ROUND_LOCAL_ONLY"
        reason = "artifact has no approved cross-round retention path"

    payload = {
        "schema_id": "CROSS_ROUND_RETENTION_DECISION_V1",
        "schema_version": 1,
        "origin_round_role": origin_round_role,
        "artifact_kind": artifact_kind.value,
        "access_class": access_class,
        "allowed": allowed,
        "destination": destination,
        "reason": reason,
    }
    hashed = hashed_payload(
        domain="CROSS_ROUND_RETENTION_DECISION_V1",
        hash_field="decision_sha256",
        payload=payload,
    )
    return RetentionDecisionV1(
        allowed=allowed,
        destination=destination,
        reason=reason,
        decision_sha256=hashed["decision_sha256"],
    )
