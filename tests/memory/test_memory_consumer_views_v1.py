from __future__ import annotations

from pathlib import Path
import importlib.util
import sys

import pytest

from pchsi.evaluation.raw_policy_prompt import ExecutedTransition
from pchsi.memory.consumer_views import (
    MemoryConsumerQueryV1,
    MemoryPartitionAuthorityScopeV1,
    MemorySourcePartitionBindingV1,
    MemorySourcePartitionV1,
    ResearcherPurposeV1,
    build_analyzer_memory_view_v1,
    build_policy_memory_view_v1,
    build_researcher_memory_view_v1,
)
from pchsi.memory.dev_snapshot_loader import (
    load_calibrated_dev_snapshot_v2,
)
from pchsi.memory.formal_b_retrieval import (
    FormalBRetrieverConfigV1,
)


def _published_snapshot_helper():
    path = Path(__file__).with_name(
        "package_b_direct_test_helpers.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_memory_v1_completion_package_b_test_helpers",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load package-B test helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module.published_snapshot


def _loaded(tmp_path: Path):
    published_snapshot = _published_snapshot_helper()
    final, snapshot, contract, contract_path, _ = (
        published_snapshot(tmp_path)
    )
    loaded = load_calibrated_dev_snapshot_v2(
        snapshot_directory=final,
        expected_snapshot_sha256=snapshot.snapshot_sha256,
        token_budget_contract_path=contract_path,
        expected_token_budget_contract_sha256=(
            contract.contract_sha256
        ),
    )
    return loaded


def _query(text: str) -> MemoryConsumerQueryV1:
    return MemoryConsumerQueryV1(
        observation=text,
        executed_transitions=(
            ExecutedTransition(
                "look",
                "activation visible failure mechanism",
            ),
        ),
        admissible_commands=("look", "inventory"),
        interface_feedback=None,
        public_task_goal="inspect the object",
    )


def _keys(value):
    found = set()
    if isinstance(value, dict):
        for key, child in value.items():
            found.add(key)
            found.update(_keys(child))
    elif isinstance(value, list):
        for child in value:
            found.update(_keys(child))
    return found


def test_policy_analyzer_researcher_receive_different_views(tmp_path):
    loaded = _loaded(tmp_path)
    policy = build_policy_memory_view_v1(
        query=_query("activation visible failure mechanism"),
        snapshot=loaded,
        config=FormalBRetrieverConfigV1(threshold_pct=0),
    )
    analyzer = build_analyzer_memory_view_v1(
        query=_query("activation visible failure mechanism"),
        snapshot=loaded,
        top_k=3,
    )
    partitions = {
        member.record.memory_lineage_id: (
            MemorySourcePartitionBindingV1(
                memory_lineage_id=(
                    member.record.memory_lineage_id
                ),
                source_partition=(
                    MemorySourcePartitionV1
                    .TRAIN_MEMORY_SOURCE
                ),
                partition_authority_sha256=(
                    loaded.snapshot.snapshot_sha256
                ),
            )
        )
        for member in loaded.members
    }
    researcher = build_researcher_memory_view_v1(
        snapshot=loaded,
        purpose=ResearcherPurposeV1.ROUND_RESEARCH_PLANNING,
        source_partition_by_lineage=partitions,
        round_evidence={"verified_result_count": 0},
        heldout_aggregate_metrics={
            "valid_seen": {
                "success_count": 0,
                "denominator": 10,
            }
        },
    )

    assert policy.policy_prompt_fragment() is not None
    assert len(analyzer.candidates) == 1
    assert len(researcher.train_side_records) == 1

    policy_keys = _keys(policy.policy_prompt_fragment())
    assert "memory_lineage_id" not in policy_keys
    assert "governance_state" not in policy_keys
    assert "provenance" not in policy_keys
    assert "effect_status" not in policy_keys

    analyzer_payload = analyzer.to_dict()
    assert analyzer_payload["direct_action_authority"] is False
    assert analyzer_payload["benefit_harm_authority"] is False
    assert "source_task_id" not in _keys(analyzer_payload)
    assert "task_gamefile_group_id" not in _keys(analyzer_payload)

    researcher_payload = researcher.to_dict()
    assert (
        researcher_payload["direct_environment_action_authority"]
        is False
    )
    assert researcher_payload["benefit_harm_authority"] is False


def test_policy_can_abstain_while_analyzer_still_gets_candidates(tmp_path):
    loaded = _loaded(tmp_path)
    query = _query("completely unrelated state")
    policy = build_policy_memory_view_v1(
        query=query,
        snapshot=loaded,
        config=FormalBRetrieverConfigV1(threshold_pct=50),
    )
    analyzer = build_analyzer_memory_view_v1(
        query=query,
        snapshot=loaded,
        top_k=3,
    )
    assert policy.policy_prompt_fragment() is None
    assert len(analyzer.candidates) == 1
    assert (
        analyzer.to_dict()["selection_semantics"]
        == "BOUNDED_CANDIDATE_SUPPORT_NO_POLICY_EXPOSURE_THRESHOLD"
    )


def test_researcher_record_access_requires_train_memory_source(tmp_path):
    loaded = _loaded(tmp_path)
    lineage = loaded.members[0].record.memory_lineage_id
    with pytest.raises(
        ValueError,
        match="TRAIN_MEMORY_SOURCE",
    ):
        build_researcher_memory_view_v1(
            snapshot=loaded,
            purpose=ResearcherPurposeV1.TRAINING_DATA_BUILD,
            source_partition_by_lineage={
                lineage: MemorySourcePartitionBindingV1(
                    memory_lineage_id=lineage,
                    source_partition=(
                        MemorySourcePartitionV1.VALID_SEEN
                    ),
                    partition_authority_sha256=(
                        loaded.snapshot.snapshot_sha256
                    ),
                )
            },
        )


def test_researcher_heldout_evidence_must_be_aggregate_only(tmp_path):
    loaded = _loaded(tmp_path)
    lineage = loaded.members[0].record.memory_lineage_id
    with pytest.raises(
        ValueError,
        match="aggregate-only",
    ):
        build_researcher_memory_view_v1(
            snapshot=loaded,
            purpose=(
                ResearcherPurposeV1.POLICY_EVALUATION_REVIEW
            ),
            source_partition_by_lineage={
                lineage: MemorySourcePartitionBindingV1(
                    memory_lineage_id=lineage,
                    source_partition=(
                        MemorySourcePartitionV1
                        .TRAIN_MEMORY_SOURCE
                    ),
                    partition_authority_sha256=(
                        loaded.snapshot.snapshot_sha256
                    ),
                )
            },
            heldout_aggregate_metrics={
                "valid_unseen": {
                    "task_gamefile_group_id": "leak"
                }
            },
        )



def test_training_data_build_rejects_snapshot_only_partition_claim(tmp_path):
    loaded = _loaded(tmp_path)
    lineage = loaded.members[0].record.memory_lineage_id
    with pytest.raises(ValueError, match="full source collection"):
        build_researcher_memory_view_v1(
            snapshot=loaded,
            purpose=ResearcherPurposeV1.TRAINING_DATA_BUILD,
            source_partition_by_lineage={
                lineage: MemorySourcePartitionBindingV1(
                    memory_lineage_id=lineage,
                    source_partition=MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE,
                    partition_authority_sha256=loaded.snapshot.snapshot_sha256,
                )
            },
        )


def test_training_data_build_accepts_full_three_way_source_authority(tmp_path):
    loaded = _loaded(tmp_path)
    lineage = loaded.members[0].record.memory_lineage_id
    binding = MemorySourcePartitionBindingV1.full_train_source_provenance(
        memory_lineage_id=lineage,
        source_collection_manifest_sha256="a" * 64,
        task_access_authority_sha256="b" * 64,
        record_provenance_authority_sha256="c" * 64,
    )
    assert binding.authority_scope is MemoryPartitionAuthorityScopeV1.FULL_TRAIN_SOURCE_PROVENANCE
    view = build_researcher_memory_view_v1(
        snapshot=loaded,
        purpose=ResearcherPurposeV1.TRAINING_DATA_BUILD,
        source_partition_by_lineage={lineage: binding},
    )
    row = view.train_side_records[0]
    assert row["source_partition_authority_scope"] == "FULL_TRAIN_SOURCE_PROVENANCE"
    assert row["task_access_authority_sha256"] == "b" * 64
