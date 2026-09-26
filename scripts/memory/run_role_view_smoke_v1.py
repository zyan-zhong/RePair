#!/usr/bin/env python3
"""Materialize all three role-specific Memory views from one frozen query.

This is an infrastructure/access audit, not a scientific outcome.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.evaluation.raw_policy_prompt import (
    ExecutedTransition,
    InterfaceFeedbackCode,
)
from pchsi.memory.consumer_views import (
    MemoryConsumerQueryV1,
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


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"object required: {path}")
    return value


def write_new(path: Path, value: object) -> None:
    data = canonical_json_bytes(value)
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        os.write(fd, data)
        os.fsync(fd)
    finally:
        os.close(fd)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument(
        "--corrected-query-panel",
        required=True,
    )
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    repo = Path(args.repo_root)
    panel_path = Path(args.corrected_query_panel)
    output = Path(args.output_root)
    if output.exists() or output.is_symlink():
        raise SystemExit("STOP=ROLE_VIEW_SMOKE_OUTPUT_EXISTS")
    if panel_path.is_symlink() or not panel_path.is_file():
        raise SystemExit("STOP=ROLE_VIEW_QUERY_PANEL_INVALID")

    dependency = load_json(
        repo
        / "configs/memory/"
        "package_b_failure_memory_dependency_v1.json"
    )
    b_result = load_json(
        repo
        / "configs/memory/"
        "formal_b_minimal_q3_result_authority_v1.json"
    )
    panel = load_json(panel_path)
    queries = panel.get("queries")
    if not isinstance(queries, list) or not queries:
        raise SystemExit("STOP=ROLE_VIEW_QUERY_POPULATION_EMPTY")

    raw = queries[0]
    visible = raw["policy_visible_query"]
    sidecar = raw.get("factual_sidecar", {})
    query = MemoryConsumerQueryV1(
        observation=visible["observation"],
        executed_transitions=tuple(
            ExecutedTransition(
                action=row["action"],
                resulting_observation=row[
                    "resulting_observation"
                ],
            )
            for row in visible["executed_transitions"]
        ),
        admissible_commands=tuple(
            visible["admissible_commands"]
        ),
        interface_feedback=(
            None
            if visible["interface_feedback"] is None
            else InterfaceFeedbackCode(
                visible["interface_feedback"]
            )
        ),
        public_task_goal=str(
            sidecar.get("public_task_goal", "")
        ),
    )

    contract_path = (
        repo
        / "configs/memory/"
        "failure_memory_token_budget_contract_v1.json"
    )
    snapshot = load_calibrated_dev_snapshot_v2(
        snapshot_directory=Path(
            dependency["active_snapshot_external_directory"]
        ),
        expected_snapshot_sha256=(
            dependency["active_snapshot_sha256"]
        ),
        token_budget_contract_path=contract_path,
        expected_token_budget_contract_sha256=(
            dependency["token_budget_contract_sha256"]
        ),
    )

    config = FormalBRetrieverConfigV1(
        threshold_pct=b_result["selected_threshold_pct"]
    )
    if config.config_sha256 != (
        b_result["selected_config_sha256"]
    ):
        raise SystemExit(
            "STOP=ROLE_VIEW_B_CONFIG_BINDING_MISMATCH"
        )

    policy = build_policy_memory_view_v1(
        query=query,
        snapshot=snapshot,
        config=config,
    )
    analyzer = build_analyzer_memory_view_v1(
        query=query,
        snapshot=snapshot,
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
                    snapshot.snapshot.snapshot_sha256
                ),
            )
        )
        for member in snapshot.members
    }
    researcher = build_researcher_memory_view_v1(
        snapshot=snapshot,
        purpose=ResearcherPurposeV1.ROUND_RESEARCH_PLANNING,
        source_partition_by_lineage=partitions,
        round_evidence={
            "role_view_smoke_only": True,
            "scientific_outcome": False,
        },
        heldout_aggregate_metrics={
            "policy_direct_b": {
                "registered_safety_stress_metrics": (
                    b_result[
                        "registered_safety_stress_metrics"
                    ]
                )
            }
        },
    )

    if not analyzer.candidates:
        raise SystemExit(
            "STOP=ANALYZER_VIEW_HAS_NO_HISTORICAL_CANDIDATES"
        )
    if len(researcher.train_side_records) != len(
        snapshot.members
    ):
        raise SystemExit(
            "STOP=RESEARCHER_VIEW_RECORD_COUNT_MISMATCH"
        )

    output.mkdir(parents=True, mode=0o700)
    write_new(output / "QUERY_V1.json", query.to_dict())
    write_new(
        output / "POLICY_MEMORY_VIEW_V1.json",
        policy.to_dict(),
    )
    write_new(
        output / "ANALYZER_MEMORY_VIEW_V1.json",
        analyzer.to_dict(),
    )
    write_new(
        output / "RESEARCHER_MEMORY_VIEW_V1.json",
        researcher.to_dict(),
    )
    summary = {
        "schema_id": "MEMORY_ROLE_VIEW_SMOKE_AUDIT_V1",
        "schema_version": 1,
        "snapshot_sha256": snapshot.snapshot.snapshot_sha256,
        "query_source": "FROZEN_CORRECTED_FORMAL_B_QUERY",
        "policy_decision_reason": (
            policy.decision_reason.value
        ),
        "policy_prompt_payload_present": (
            policy.policy_prompt_fragment() is not None
        ),
        "analyzer_candidate_count": (
            len(analyzer.candidates)
        ),
        "researcher_train_record_count": (
            len(researcher.train_side_records)
        ),
        "policy_and_analyzer_views_are_distinct": (
            policy.to_dict() != analyzer.to_dict()
        ),
        "policy_and_researcher_views_are_distinct": (
            policy.to_dict() != researcher.to_dict()
        ),
        "analyzer_direct_action_authority": False,
        "researcher_direct_action_authority": False,
        "benefit_harm_authority": (
            "SAME_STATE_ENVIRONMENT_ONLY"
        ),
        "scientific_outcome": False,
        "pass": True,
    }
    write_new(
        output / "MEMORY_ROLE_VIEW_SMOKE_AUDIT_V1.json",
        summary,
    )

    print("MEMORY_ROLE_VIEW_SMOKE_AUDIT_PASS")
    print(
        "POLICY_DECISION_REASON="
        + policy.decision_reason.value
    )
    print(
        "POLICY_PROMPT_PAYLOAD_PRESENT="
        + str(policy.policy_prompt_fragment() is not None).lower()
    )
    print(
        "ANALYZER_CANDIDATE_COUNT="
        + str(len(analyzer.candidates))
    )
    print(
        "RESEARCHER_TRAIN_RECORD_COUNT="
        + str(len(researcher.train_side_records))
    )
    print("SCIENTIFIC_OUTCOME=false")


if __name__ == "__main__":
    main()
