from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
)


FINALIZER = Path(
    "scripts/memory/finalize_approved_source_failures_v1.py"
)


def _load_finalizer():
    spec = importlib.util.spec_from_file_location(
        "_finalizer_alias_regression",
        FINALIZER,
    )
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    return module


def test_source_attempt_id_binds_to_case_execution_attempt_id(
    tmp_path,
):
    module = _load_finalizer()

    root = tmp_path / "human_panel"
    root.mkdir()

    panel_sha = "1" * 64
    ledger_sha = "2" * 64
    selected_sha = "3" * 64

    panel_cases = []
    decisions = []

    for index in range(3):
        case_id = f"CASE-{index}"

        case_dir = (
            root
            / "cases"
            / case_id
        )
        case_dir.mkdir(
            parents=True
        )

        receipt_sha = hashlib.sha256(
            f"receipt-{index}".encode()
        ).hexdigest()

        bundle_sha = hashlib.sha256(
            f"bundle-{index}".encode()
        ).hexdigest()

        case_summary = {
            "case_id": case_id,
            "execution_attempt_id": (
                f"attempt-{index}"
            ),
            "source_task_id": (
                f"task-{index}"
            ),
            "source_panel_manifest_sha256":
                panel_sha,
            "source_collection_ledger_sha256":
                ledger_sha,
            "selected_failure_panel_sha256":
                selected_sha,
            "case_receipt_sha256":
                receipt_sha,
            "attempt_bundle_sha256":
                bundle_sha,
            "valid_model_call_index_max":
                9,
        }

        case_raw = canonical_json_bytes(
            case_summary
        )

        (
            case_dir
            / "case_summary.json"
        ).write_bytes(
            case_raw
        )

        panel_cases.append(
            {
                "case_id": case_id,
            }
        )

        decisions.append(
            {
                "case_id":
                    case_id,
                "case_summary_sha256":
                    hashlib.sha256(
                        case_raw
                    ).hexdigest(),
                "source_panel_manifest_sha256":
                    panel_sha,
                "source_collection_ledger_sha256":
                    ledger_sha,
                "selected_failure_panel_sha256":
                    selected_sha,
                "case_receipt_sha256":
                    receipt_sha,
                "attempt_bundle_sha256":
                    bundle_sha,
                "source_attempt_id":
                    f"attempt-{index}",
                "source_task_id":
                    f"task-{index}",
                "source_round":
                    "SOURCE_COLLECTION_V1",
                "source_condition":
                    "P4-R1-Q2-BAD-TRAIN17",
                "relevant_start_model_call_index":
                    0,
                "registered_failure_onset_model_call_index":
                    1,
                "final_model_call_index":
                    2,
                "registered_recovery_start_model_call_index":
                    None,
                "registered_recovery_final_model_call_index":
                    None,
                "activation_condition_text":
                    "activation",
                "release_condition_text":
                    "release",
                "non_applicability_condition_text":
                    "",
                "candidate_mechanism_text":
                    "",
                "proposed_recovery_steps":
                    [],
                "reviewer_notes":
                    "",
            }
        )

    panel_index = {
        "schema_id":
            "FAILURE_MEMORY_HUMAN_REGISTRATION_PANEL_V2",
        "schema_version":
            2,
        "source_panel_manifest_sha256":
            panel_sha,
        "source_collection_ledger_sha256":
            ledger_sha,
        "selected_failure_panel_sha256":
            selected_sha,
        "selection_rule":
            "FIRST_THREE_FAILURES_IN_FROZEN_PANEL_ORDER_V1",
        "performance_estimand":
            "NO_PERFORMANCE_ESTIMAND",
        "cases":
            panel_cases,
        "scientific_registration_authority_created":
            False,
    }

    panel_raw = canonical_json_bytes(
        panel_index
    )

    (
        root
        / "PANEL_INDEX.json"
    ).write_bytes(
        panel_raw
    )

    approval = {
        "schema_id":
            "FAILURE_MEMORY_HUMAN_REGISTRATION_APPROVAL_V1",
        "schema_version":
            1,
        "approval_token":
            "HUMAN_FAILURE_MEMORY_REGISTRATION_APPROVED_V1",
        "reviewer_decision":
            "APPROVED",
        "reviewer_id":
            "reviewer",
        "human_panel_index_sha256":
            hashlib.sha256(
                panel_raw
            ).hexdigest(),
        "source_panel_manifest_sha256":
            panel_sha,
        "source_collection_ledger_sha256":
            ledger_sha,
        "selected_failure_panel_sha256":
            selected_sha,
        "decisions":
            decisions,
    }

    approval_path = (
        tmp_path
        / "approval.json"
    )

    approval_path.write_bytes(
        canonical_json_bytes(
            approval
        )
    )

    _, _, _, observed, _ = (
        module._validate_approval(
            path=approval_path,
            human_panel_root=root,
        )
    )

    assert len(observed) == 3


def test_source_collection_commit_may_be_ancestor_of_finalizer():
    module = _load_finalizer()

    repo = Path(".").resolve()

    head = subprocess.check_output(
        [
            "git",
            "-C",
            str(repo),
            "rev-parse",
            "HEAD",
        ],
        text=True,
    ).strip()

    parent = subprocess.check_output(
        [
            "git",
            "-C",
            str(repo),
            "rev-parse",
            "HEAD^",
        ],
        text=True,
    ).strip()

    module._validate_source_collection_code_commit_ancestry(
        repo_root=repo,
        source_collection_code_commit=parent,
        authority_commit=head,
    )
