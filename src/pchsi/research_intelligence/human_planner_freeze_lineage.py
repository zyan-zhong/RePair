"""Approval-safe lineage binding for Human PRE freeze.

The Human scientific PRE decision is fixed before user approval.  Approval is
governance metadata and must not silently create a new source Reference Trace
after Strong blind evidence has already been hydrated/audited.

This module preserves the pre-approval scientific trace identity while binding
the approved adjudication separately for governance and role-neutral
supervision.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib

from pchsi.reference_loop.canonical import canonical_json_bytes
from pchsi.research_intelligence.human_planner_adjudication import (
    build_role_neutral_human_pre_decision_v1,
    compile_human_planner_artifacts_v1,
)
from pchsi.research_intelligence.repair_portfolio import (
    ResearchRepairPortfolioV1,
)


_PENDING = "ASSISTANT_PREPARED_REQUIRES_USER_APPROVAL"
_APPROVED = "APPROVED"
_INVARIANT_KEYS = (
    "repair_portfolio",
    "human_pre_input",
    "strong_blind_input",
)


def _approval_status(value: Mapping[str, object]) -> str:
    approval = value.get("human_approval")
    if not isinstance(approval, Mapping):
        raise ValueError("human_approval missing")
    status = approval.get("status")
    if not isinstance(status, str):
        raise ValueError("human_approval.status missing")
    return status


def _without_approval(value: Mapping[str, object]) -> dict[str, object]:
    result = dict(value)
    result.pop("human_approval", None)
    return result


def validate_approval_only_transition_v1(
    *,
    candidate: Mapping[str, object],
    approved: Mapping[str, object],
) -> None:
    if _approval_status(candidate) != _PENDING:
        raise ValueError("candidate is not pending Human approval")
    if _approval_status(approved) != _APPROVED:
        raise ValueError("approved adjudication is not APPROVED")
    if canonical_json_bytes(_without_approval(candidate)) != canonical_json_bytes(
        _without_approval(approved)
    ):
        raise ValueError("approval transition changed scientific decision content")


def compile_preapproval_freeze_artifacts_v1(
    *,
    candidate: Mapping[str, object],
    approved: Mapping[str, object],
    dossier: Mapping[str, object],
    shared_input: Mapping[str, object],
    expected_source_trace_v2_sha256: str,
) -> dict[str, object]:
    """Compile freeze inputs without rebasing the audited trace on approval.

    The pre-approval candidate produced the Reference Trace V2 that was later
    hydrated into Trace V3.  We therefore:
      1) compile that exact pending scientific decision;
      2) require its trace SHA to match Trace V3.source_reference_trace_v2;
      3) prove approval does not alter portfolio/Human PRE/Strong blind input;
      4) bind the approved adjudication only in the role-neutral supervision
         artifact and approval record.
    """

    validate_approval_only_transition_v1(
        candidate=candidate,
        approved=approved,
    )

    source_artifacts = compile_human_planner_artifacts_v1(
        adjudication=candidate,
        dossier=dossier,
        shared_input=shared_input,
    )
    source_trace = source_artifacts["reference_trace"]["trace_sha256"]
    if source_trace != expected_source_trace_v2_sha256:
        raise ValueError(
            "pre-approval Reference Trace V2 does not match Trace V3 source"
        )

    # Compile the approved variant only as an invariance audit.  It is NOT used
    # as the source trace, because approval metadata was added after the
    # scientific PRE decision and after Strong blind hydration.
    approved_artifacts = compile_human_planner_artifacts_v1(
        adjudication=approved,
        dossier=dossier,
        shared_input=shared_input,
    )
    for key in _INVARIANT_KEYS:
        if canonical_json_bytes(source_artifacts[key]) != canonical_json_bytes(
            approved_artifacts[key]
        ):
            raise ValueError(
                "Human approval changed approval-invariant scientific artifact: "
                + key
            )

    portfolio = ResearchRepairPortfolioV1.from_dict(
        source_artifacts["repair_portfolio"]
    )
    portfolio.validate()
    approved_role_neutral = build_role_neutral_human_pre_decision_v1(
        adjudication=approved,
        portfolio=portfolio,
    )

    approved_sha = hashlib.sha256(
        canonical_json_bytes(dict(approved))
    ).hexdigest()

    return {
        "source_artifacts": source_artifacts,
        "approved_role_neutral_pre_decision": approved_role_neutral.to_dict(),
        "preapproval_reference_trace_v2_sha256": source_trace,
        "approved_human_adjudication_sha256": approved_sha,
        "approval_invariant_artifact_keys": list(_INVARIANT_KEYS),
    }
