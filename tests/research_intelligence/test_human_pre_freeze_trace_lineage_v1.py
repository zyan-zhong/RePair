from __future__ import annotations

import copy
import hashlib
import importlib.util
from pathlib import Path

import pytest

from pchsi.reference_loop.canonical import canonical_json_bytes
from pchsi.research_intelligence.human_planner_adjudication import (
    compile_human_planner_artifacts_v1,
)
from pchsi.research_intelligence.human_planner_freeze_lineage import (
    compile_preapproval_freeze_artifacts_v1,
    validate_approval_only_transition_v1,
)


def _load_existing_fixture():
    path = Path(__file__).with_name("test_human_planner_adjudication_v1.py")
    spec = importlib.util.spec_from_file_location(
        "_human_planner_existing_fixture",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load existing Human Planner fixture")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._fixture()


def _approve(candidate):
    approved = copy.deepcopy(candidate)
    approved["human_approval"] = {
        "status": "APPROVED",
        "reviewer": "USER_PROJECT_CHAT_APPROVAL",
        "approval_timestamp": "2026-08-29T07:47:38Z",
        "approval_note": "approved before Strong shadow/F0F1",
    }
    return approved


def test_approval_only_transition_preserves_scientific_decision():
    candidate, dossier, shared = _load_existing_fixture()
    approved = _approve(candidate)

    validate_approval_only_transition_v1(
        candidate=candidate,
        approved=approved,
    )


def test_approval_only_transition_rejects_scientific_mutation():
    candidate, dossier, shared = _load_existing_fixture()
    approved = _approve(candidate)
    approved["single_principal_change_id"] = "FORBIDDEN_MUTATION"

    with pytest.raises(ValueError, match="scientific decision content"):
        validate_approval_only_transition_v1(
            candidate=candidate,
            approved=approved,
        )


def test_freeze_preserves_preapproval_trace_v2_lineage():
    candidate, dossier, shared = _load_existing_fixture()
    approved = _approve(candidate)

    pending = compile_human_planner_artifacts_v1(
        adjudication=candidate,
        dossier=dossier,
        shared_input=shared,
    )
    expected_trace = pending["reference_trace"]["trace_sha256"]

    result = compile_preapproval_freeze_artifacts_v1(
        candidate=candidate,
        approved=approved,
        dossier=dossier,
        shared_input=shared,
        expected_source_trace_v2_sha256=expected_trace,
    )

    assert result["preapproval_reference_trace_v2_sha256"] == expected_trace
    source = result["source_artifacts"]

    approved_full = compile_human_planner_artifacts_v1(
        adjudication=approved,
        dossier=dossier,
        shared_input=shared,
    )

    for key in (
        "repair_portfolio",
        "human_pre_input",
        "strong_blind_input",
    ):
        assert canonical_json_bytes(source[key]) == canonical_json_bytes(
            approved_full[key]
        )

    expected_approved_sha = hashlib.sha256(
        canonical_json_bytes(approved)
    ).hexdigest()
    assert result["approved_human_adjudication_sha256"] == expected_approved_sha
    assert result["approved_role_neutral_pre_decision"][
        "raw_artifact_sha256"
    ] == expected_approved_sha


def test_freeze_rejects_wrong_trace_v3_source_binding():
    candidate, dossier, shared = _load_existing_fixture()
    approved = _approve(candidate)

    with pytest.raises(ValueError, match="Trace V3 source"):
        compile_preapproval_freeze_artifacts_v1(
            candidate=candidate,
            approved=approved,
            dossier=dossier,
            shared_input=shared,
            expected_source_trace_v2_sha256="f" * 64,
        )
