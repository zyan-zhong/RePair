from __future__ import annotations

import hashlib
import json

import pytest

from pchsi.research_intelligence.canonical_candidate_pool_v2 import (
    build_canonical_selected_pool_v2,
)
from pchsi.research_intelligence.selected_candidate_authority import (
    discover_selected_candidate_authority_v1,
)


def _sha(prefix: str, index: int) -> str:
    return hashlib.sha256(f"{prefix}:{index}".encode()).hexdigest()


def _candidate(
    index: int,
    state: int,
    *,
    executable: bool = True,
) -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_REPAIR_CANDIDATE_V1",
        "schema_version": 1,
        "candidate_kind": "FAILURE_REPAIR",
        "source_state_sha256": _sha("state", state),
        "menu_sha256": _sha("menu", state),
        "source_proposal_sha256": _sha("proposal", index),
        "candidate_status": (
            "EXECUTABLE_EXACT_ACTION"
            if executable
            else "ABSTAIN"
        ),
        "exact_action": "inventory" if executable else None,
        "option_actions": [],
        "termination_condition": None,
        "requires_environment_verification": True,
        "candidate_sha256": _sha("candidate", index),
        "live_menu_revalidation_required": True,
        "all_intervention_actions_count_against_environment_budget": True,
    }


def _proposal(index: int, state: int) -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_SOURCE_CONDITIONED_PROPOSAL_V1",
        "schema_version": 1,
        "group_manifest_sha256": _sha("group", state),
        "local_result_sha256": _sha("local", state),
        "error_instance_id": f"error-{state}",
        "source_state_sha256": _sha("state", state),
        "menu_sha256": _sha("menu", state),
        "exact_action": "inventory",
        "option_actions": [],
        "termination_condition": None,
        "supporting_evidence_sha256s": [_sha("evidence", index)],
        "source_proposal_sha256": _sha("proposal", index),
    }


def _group(state: int) -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_GROUP_MANIFEST_V1",
        "schema_version": 1,
        "group_id": f"group-{state}",
        "task_family": f"family-{state % 6}",
        "group_manifest_sha256": _sha("group", state),
    }


def _crosscheck(index: int) -> dict[str, object]:
    return {
        "schema_id": "ANALYZER_CROSSCHECK_RESULT_V1",
        "schema_version": 1,
        "target_artifact_sha256": _sha("proposal", index),
        "disposition": "ACCEPT",
        "supporting_evidence_sha256s": [_sha("xev", index)],
        "contradiction_evidence_sha256s": [],
        "residual_case_ids": [],
        "current_evidence_sha256s": [],
        "historical_evidence_sha256s": [],
        "crosscheck_sha256": _sha("crosscheck", index),
    }


def _pool(
    *,
    alternate_selection: bool = False,
) -> dict[str, object]:
    candidates = []
    proposals = []
    groups = []
    crosschecks = []

    final_a2 = []
    final_a3 = []

    index = 0
    for state in range(30):
        a2 = _candidate(index, state)
        candidates.append(a2)
        proposals.append(_proposal(index, state))
        crosschecks.append(_crosscheck(index))
        final_a2.append(
            {
                "candidate_sha256": a2["candidate_sha256"],
                "source_state_sha256": a2["source_state_sha256"],
            }
        )
        index += 1

        a3 = _candidate(index, state)
        candidates.append(a3)
        proposals.append(_proposal(index, state))
        crosschecks.append(_crosscheck(index))
        final_a3.append(
            {
                "candidate_sha256": a3["candidate_sha256"],
                "source_state_sha256": a3["source_state_sha256"],
            }
        )
        index += 1
        groups.append(_group(state))

    # 14 extra executable objects are not selected by the final ledger.
    for extra in range(14):
        extra_index = 1000 + extra
        candidates.append(
            _candidate(extra_index, extra % 7)
        )
        proposals.append(
            _proposal(extra_index, extra % 7)
        )

    pool = {
        "schema_id": "FORMAL_ANALYZER_CANDIDATE_POOL_V1",
        "schema_version": 1,
        "all_repair_objects": candidates,
        "proposals": proposals,
        "groups": groups,
        "crosschecks": crosschecks,
        # Real-world compatibility case: final selection is not named
        # state_condition_outcomes. It is discoverable structurally.
        "final_selected_repairs": {
            "A2": final_a2,
            "A3": final_a3,
        },
        "wrapper_summaries": [
            {
                "candidate_id": f"wrapper-{i}",
                "repair": "summary only",
            }
            for i in range(74)
        ],
    }

    if alternate_selection:
        # Add a second structurally valid but scientifically different ledger.
        alt = json.loads(json.dumps(pool["final_selected_repairs"]))
        alt["A2"][0]["candidate_sha256"] = candidates[60][
            "candidate_sha256"
        ]
        pool["alternate_selected_repairs"] = alt

    return pool


def test_discovers_unique_selection_without_hardcoded_field_name() -> None:
    pool = _pool()
    authority, diagnostics = discover_selected_candidate_authority_v1(
        pool=pool,
        expected_total=60,
        expected_condition_counts={"A2": 30, "A3": 30},
        expected_source_state_count=30,
    )
    assert len(authority.selected_rows) == 60
    assert len(authority.structural_container_paths) >= 1
    assert diagnostics["unique_scientific_signature_count"] == 1


def test_rejects_two_different_structurally_valid_ledgers() -> None:
    pool = _pool(alternate_selection=True)
    with pytest.raises(
        ValueError,
        match="scientifically different",
    ):
        discover_selected_candidate_authority_v1(
            pool=pool,
            expected_total=60,
            expected_condition_counts={"A2": 30, "A3": 30},
            expected_source_state_count=30,
        )


def test_canonical_v2_keeps_60_and_audits_14_extra_executable() -> None:
    pool = _pool()
    authority, _ = discover_selected_candidate_authority_v1(
        pool=pool,
        expected_total=60,
        expected_condition_counts={"A2": 30, "A3": 30},
        expected_source_state_count=30,
    )
    file_sha = hashlib.sha256(
        (
            json.dumps(pool, sort_keys=True)
            + "\n"
        ).encode()
    ).hexdigest()
    canonical = build_canonical_selected_pool_v2(
        pool=pool,
        pool_file_sha256=file_sha,
        authority=authority,
    )
    assert canonical["selected_candidate_count"] == 60
    assert canonical["selected_source_state_count"] == 30
    assert canonical["extra_executable_candidate_count"] == 14
    assert len(canonical["state_pairs"]) == 30
    for pair in canonical["state_pairs"].values():
        assert set(pair) == {"A2", "A3"}


def test_wrapper_summaries_do_not_enter_authority() -> None:
    pool = _pool()
    authority, _ = discover_selected_candidate_authority_v1(
        pool=pool,
        expected_total=60,
        expected_condition_counts={"A2": 30, "A3": 30},
        expected_source_state_count=30,
    )
    selected = {
        row.candidate_sha256 for row in authority.selected_rows
    }
    assert all(
        not wrapper["candidate_id"] in selected
        for wrapper in pool["wrapper_summaries"]
    )
