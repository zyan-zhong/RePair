from __future__ import annotations

import hashlib
from dataclasses import replace
from pathlib import Path

import pytest

from pchsi.evaluation.canonical_evidence import sha256_file
from pchsi.memory.source_collection import (
    COMPLETE_PANEL_ORDER_RULE,
    NO_PERFORMANCE_ESTIMAND,
    OUTCOME_USE,
    SOURCE_BATCH_SIZE,
    SOURCE_CASE_RECEIPT_V1,
    SOURCE_COLLECTION_CONTEXT_V1,
    SOURCE_PANEL_SCHEMA_V1,
    SOURCE_STOPPING_FAILURE_TARGET,
    STOPPING_RULE_ID,
    PROTECTED_TASK_ACCESS_SHA256,
    SourceCollectionCaseReceiptV1,
    SourceCollectionPolicyIdentityV1,
    SourcePanelEntryV1,
    SourcePanelManifestV1,
    append_source_collection_receipt_v1,
    build_complete_source_panel_order_v1,
    build_selected_failure_panel_v1,
    read_source_collection_ledger_v1,
    source_panel_order_score_v1,
    stopping_decision_after_complete_prefix_v1,
)
from pchsi.memory.task_access import canonical_task_gamefile_group_id


TASK_TYPES = (
    "look_at_obj_in_light",
    "pick_and_place_simple",
    "pick_clean_then_place_in_recep",
    "pick_cool_then_place_in_recep",
    "pick_heat_then_place_in_recep",
    "pick_two_obj_and_place",
)


def _policy_identity():
    return SourceCollectionPolicyIdentityV1(
        logical_condition_id="P4-R1-Q2-BAD",
        checkpoint_instance_id="P4-R1-Q2-BAD-TRAIN17",
        training_seed=17,
        served_model_name="pi1-train17",
        adapter_bundle_sha256="a" * 64,
        policy_runtime_manifest_sha256="b" * 64,
        server_runtime_manifest_sha256="c" * 64,
        raw_protocol_sha256="d" * 64,
        policy_request_schema_sha256="e" * 64,
    )


def _entry(index: int, task_type: str | None = None):
    if task_type is None:
        task_type = TASK_TYPES[index % len(TASK_TYPES)]
    relative = (
        "train/"
        + task_type
        + f"-synthetic-{index:04d}/"
        + f"trial_T{index:04d}/game.tw-pddl"
    )
    game_sha = hashlib.sha256(
        f"game-{index}".encode("utf-8")
    ).hexdigest()
    group = canonical_task_gamefile_group_id(
        relative_gamefile=relative,
        gamefile_sha256=game_sha,
    )
    return SourcePanelEntryV1(
        panel_index=index,
        batch_index=index // SOURCE_BATCH_SIZE,
        task_access_record_line_index=index,
        task_access_record_sha256=hashlib.sha256(
            f"access-{index}".encode("utf-8")
        ).hexdigest(),
        trial_id=f"trial_T{index:04d}",
        task_type=task_type,
        dataset_relative_gamefile=relative,
        absolute_gamefile=(
            "/synthetic-root/" + relative
        ),
        gamefile_sha256=game_sha,
        task_gamefile_group_id=group,
        order_score=source_panel_order_score_v1(group),
    )


def _manifest():
    raw_entries = tuple(
        _entry(index)
        for index in range(2367)
    )
    ordered = build_complete_source_panel_order_v1(
        raw_entries
    )
    return SourcePanelManifestV1(
        schema_id=SOURCE_PANEL_SCHEMA_V1,
        schema_version=1,
        source_collection_context=SOURCE_COLLECTION_CONTEXT_V1,
        source_collection_code_commit="f" * 40,
        runtime_binding_sha256="1" * 64,
        task_access_protected_manifest_sha256=PROTECTED_TASK_ACCESS_SHA256,
        complete_panel_order_rule=COMPLETE_PANEL_ORDER_RULE,
        batch_size=SOURCE_BATCH_SIZE,
        stopping_failure_target=SOURCE_STOPPING_FAILURE_TARGET,
        stopping_rule_id=STOPPING_RULE_ID,
        outcome_use=OUTCOME_USE,
        performance_estimand=NO_PERFORMANCE_ESTIMAND,
        policy_identity=_policy_identity(),
        entries=ordered,
        panel_manifest_sha256=None,
    )


def _receipt(
    *,
    panel_sha: str,
    index: int,
    success: bool,
    previous: str | None,
):
    return SourceCollectionCaseReceiptV1(
        schema_id=SOURCE_CASE_RECEIPT_V1,
        schema_version=1,
        panel_manifest_sha256=panel_sha,
        panel_index=index,
        batch_index=index // SOURCE_BATCH_SIZE,
        task_access_record_line_index=index,
        task_access_record_sha256=hashlib.sha256(
            f"access-{index}".encode("utf-8")
        ).hexdigest(),
        task_gamefile_group_id=hashlib.sha256(
            f"group-{index}".encode("utf-8")
        ).hexdigest(),
        source_task_id=f"source-task-{index}",
        execution_attempt_id=f"e1-t{index:04d}-s0000000017-a000",
        attempt_bundle_sha256=hashlib.sha256(
            f"bundle-{index}".encode("utf-8")
        ).hexdigest(),
        scientific_outcome_status=(
            "SUCCESS" if success else "TASK_FAILURE"
        ),
        success=success,
        termination_reason=(
            "ENVIRONMENT_TERMINATED"
            if success
            else "ENVIRONMENT_STEP_BUDGET_EXHAUSTED"
        ),
        outcome_use=OUTCOME_USE,
        performance_estimand=NO_PERFORMANCE_ESTIMAND,
        previous_receipt_sha256=previous,
        receipt_sha256=None,
    )


def test_complete_source_panel_freezes_all_2367_before_outcomes():
    manifest = _manifest()
    assert len(manifest.entries) == 2367
    assert tuple(
        item.panel_index for item in manifest.entries
    ) == tuple(range(2367))
    assert manifest.performance_estimand == (
        "NO_PERFORMANCE_ESTIMAND"
    )
    assert manifest.outcome_use == (
        "STOPPING_ONLY_NO_PERFORMANCE_ESTIMAND"
    )
    assert manifest.batch_size == 12
    assert manifest.stopping_failure_target == 3

    rebuilt = SourcePanelManifestV1.from_json(
        manifest.canonical_bytes()
    )
    assert rebuilt == manifest


def test_complete_order_is_outcome_free_task_type_round_robin():
    entries = tuple(
        _entry(index)
        for index in range(60)
    )
    ordered = build_complete_source_panel_order_v1(
        entries
    )
    first_types = tuple(
        item.task_type
        for item in ordered[: len(TASK_TYPES)]
    )
    assert first_types == tuple(sorted(TASK_TYPES))

    # Ordering is a function of task identity only; no receipt/outcome object
    # participates in the API.
    assert all(
        item.order_score
        == source_panel_order_score_v1(
            item.task_gamefile_group_id
        )
        for item in ordered
    )


def test_manifest_rejects_partial_panel_and_performance_estimand():
    manifest = _manifest()
    with pytest.raises(ValueError):
        replace(
            manifest,
            entries=manifest.entries[:-1],
            panel_manifest_sha256=None,
        )

    with pytest.raises(ValueError):
        replace(
            manifest,
            performance_estimand="TASK_SUCCESS_RATE",
            panel_manifest_sha256=None,
        )


def test_stopping_rule_never_stops_mid_batch():
    panel_sha = "a" * 64
    receipts = []
    previous = None

    for index in range(11):
        receipt = _receipt(
            panel_sha=panel_sha,
            index=index,
            success=(index >= 3),
            previous=previous,
        )
        receipts.append(receipt)
        previous = receipt.receipt_sha256

    assert (
        stopping_decision_after_complete_prefix_v1(
            tuple(receipts),
            panel_size=2367,
        )
        == "CONTINUE"
    )

    receipt = _receipt(
        panel_sha=panel_sha,
        index=11,
        success=True,
        previous=previous,
    )
    receipts.append(receipt)

    assert (
        stopping_decision_after_complete_prefix_v1(
            tuple(receipts),
            panel_size=2367,
        )
        == "STOP_FAILURE_TARGET_REACHED"
    )


def test_collection_ledger_preserves_every_case_and_drains_partial_writes(
    tmp_path,
    monkeypatch,
):
    path = tmp_path / "source_collection_ledger.jsonl"
    original_write = __import__(
        "pchsi.memory.source_collection",
        fromlist=["os"],
    ).os.write
    module = __import__(
        "pchsi.memory.source_collection",
        fromlist=["os"],
    )
    calls = 0

    def partial(fd, data):
        nonlocal calls
        calls += 1
        return original_write(fd, bytes(data[:7]))

    monkeypatch.setattr(module.os, "write", partial)

    previous = None
    expected = []
    for index in range(12):
        receipt = _receipt(
            panel_sha="a" * 64,
            index=index,
            success=(index % 5 != 0),
            previous=previous,
        )
        append_source_collection_receipt_v1(
            path=path,
            receipt=receipt,
        )
        expected.append(receipt)
        previous = receipt.receipt_sha256

    assert calls > 12
    assert read_source_collection_ledger_v1(
        path
    ) == tuple(expected)


def test_selected_failure_panel_is_reference_only_to_full_ledger(
    tmp_path,
):
    ledger = tmp_path / "source_collection_ledger.jsonl"
    previous = None
    failures = []

    for index in range(12):
        success = index not in {1, 4, 9, 11}
        receipt = _receipt(
            panel_sha="a" * 64,
            index=index,
            success=success,
            previous=previous,
        )
        append_source_collection_receipt_v1(
            path=ledger,
            receipt=receipt,
        )
        if not success:
            failures.append(receipt)
        previous = receipt.receipt_sha256

    selected = build_selected_failure_panel_v1(
        panel_manifest_sha256="a" * 64,
        collection_ledger_path=ledger,
    )

    assert tuple(
        item.panel_index
        for item in selected.selected_failures
    ) == (1, 4, 9)
    assert selected.collection_ledger_sha256 == sha256_file(
        ledger
    )
    assert selected.performance_estimand == (
        "NO_PERFORMANCE_ESTIMAND"
    )
    assert tuple(
        item.case_receipt_sha256
        for item in selected.selected_failures
    ) == tuple(
        item.receipt_sha256
        for item in failures[:3]
    )


def test_source_collection_runtime_does_not_relabel_select_or_emit_rate_code():
    runner = Path(
        "scripts/memory/run_source_collection_v1.py"
    ).read_text(encoding="utf-8")
    runtime_discovery = Path(
        "scripts/memory/discover_source_collection_runtime_v1.py"
    ).read_text(encoding="utf-8")

    assert "ScheduledCell" in runner
    assert "SelectExecutionIdentityV1" not in runner
    assert "SELECT_SUMMARY_ONLY" not in runner
    assert "requires_diagnostic_policy_call_evidence=True" in runner
    assert "NO_PERFORMANCE_ESTIMAND" in runner
    assert "success_rate" not in runner
    assert "accuracy" not in runner.casefold()

    # SELECT attempts are used only to recover frozen pi1 identity. The
    # discovery program must not branch on observed success/failure.
    assert ".success" not in runtime_discovery
    assert "formal_attempt_count_checked" in runtime_discovery


def test_finalizer_is_pre_a9_and_requires_human_authority_artifact():
    finalizer = Path(
        "scripts/memory/finalize_approved_source_failures_v1.py"
    ).read_text(encoding="utf-8")

    assert "HUMAN_FAILURE_MEMORY_REGISTRATION_APPROVED_V1" in finalizer
    assert "RegisteredFailureSequenceWindowV1" in finalizer
    assert "RegisteredReplaySourceV1" in finalizer
    assert "MATERIALIZATION_MANIFEST.json" in finalizer
    assert "REPLAY_QUALIFICATION_MANIFEST.json" in finalizer

    # The finalizer prepares exact inputs only. Real A9 environment replay is
    # performed later by the separately approval-gated stage runner.
    assert "SpawnedAlfworldAdapter" not in finalizer
    assert "PolicyClient" not in finalizer
    assert "run_single_episode" not in finalizer


def test_source_runner_resumes_partial_batch_by_finishing_same_batch():
    runner = Path(
        "scripts/memory/run_source_collection_v1.py"
    ).read_text(encoding="utf-8")

    assert "SOURCE_COLLECTION_PREFIX_NOT_AT_COMPLETE_BATCH_BOUNDARY" not in runner
    assert "prefix_inside_batch" in runner
    assert "(current_batch + 1) * SOURCE_BATCH_SIZE" in runner
def test_dataset_discovery_includes_explicit_alfworld_cache(tmp_path):
    import importlib.util
    import sys

    path = Path(
        "scripts/memory/discover_source_dataset_root_v1.py"
    )

    spec = importlib.util.spec_from_file_location(
        "_dataset_discovery_hotfix_test",
        path,
    )

    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(
        spec
    )

    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    search_root = (
        tmp_path
        / "storage"
    )

    expected = (
        search_root
        / ".cache"
        / "alfworld"
        / "json_2.1.1"
    )

    expected.mkdir(
        parents=True
    )

    observed = (
        module
        ._direct_dataset_root_candidates(
            (search_root,)
        )
    )

    assert (
        expected.resolve()
        in observed
    )
