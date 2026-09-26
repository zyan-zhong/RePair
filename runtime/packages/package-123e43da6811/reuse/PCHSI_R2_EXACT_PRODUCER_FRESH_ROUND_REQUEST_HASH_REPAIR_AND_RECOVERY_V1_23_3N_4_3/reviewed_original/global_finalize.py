from __future__ import annotations

from pathlib import Path
import os
import shutil
import sys

from safe_io import load_json, sha_file, write_new_json
from shard_math import shard_positions


def try_finalize(
    *,
    state_root: Path,
    worktree: Path,
    extracted_capsule: Path,
    shard_plan: dict[str,object],
) -> bool:
    state_root=Path(state_root)
    evidence=state_root/"round_evidence"
    evidence.mkdir(parents=True,exist_ok=True)
    final_terminal=evidence/"PCHSI_V1232K_GLOBAL_TERMINAL_V1.json"
    if final_terminal.is_file():
        return True

    shard_count=int(shard_plan["shard_count"])
    shard_markers=[]
    for shard_id in range(shard_count):
        shard_root=state_root/"shards"/f"{shard_id:04d}"
        terminal=shard_root/"PCHSI_V1232S_SHARD_TERMINALS_V1.json"
        fatal=shard_root/"PCHSI_V1232S_SHARD_FATAL_V1.json"
        if terminal.is_file():
            shard_markers.append(("terminal",terminal))
        elif fatal.is_file():
            shard_markers.append(("fatal",fatal))
        else:
            return False

    lock=evidence/"GLOBAL_FINALIZE_LOCK"
    try:
        os.mkdir(lock)
    except FileExistsError:
        return False

    try:
        if final_terminal.is_file():
            return True

        binding=load_json(
            extracted_capsule/"ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json"
        )
        train=binding["train_update_authority"]
        memory=binding["memory_authority"]
        runtime=binding["runtime_authority"]

        sys.path.insert(0,str(worktree/"src"))
        from pchsi.round_control.clean_execution_binding import (
            load_clean_train_pool_records,
            build_clean_train_schedule,
        )
        from pchsi.round_control.rollout_collection import (
            RoundEpisodeTerminalV1,
            RoundRolloutCollectionRequestV1,
            RoundRolloutExecutionBindingV1,
            seal_rollout_universe,
            build_failure_cohort,
        )

        manifest_candidates=[
            p for p in extracted_capsule.rglob("*.jsonl")
            if p.is_file() and not p.is_symlink() and sha_file(p)==train["manifest_sha256"]
        ]
        if not manifest_candidates:
            raise RuntimeError("GLOBAL_MANIFEST_NOT_FOUND")
        manifest=sorted(manifest_candidates,key=str)[0]

        runtime_candidates=[
            p for p in extracted_capsule.rglob("*.json")
            if p.is_file() and not p.is_symlink()
            and sha_file(p)==runtime["runtime_binding_file_sha256"]
        ]
        memory_candidates=[
            p for p in extracted_capsule.rglob("*.json")
            if p.is_file() and not p.is_symlink()
            and sha_file(p)==memory["runtime_identity_file_sha256"]
        ]
        if not runtime_candidates or not memory_candidates:
            raise RuntimeError("GLOBAL_RUNTIME_OR_MEMORY_NOT_FOUND")
        runtime_path=sorted(runtime_candidates,key=str)[0]
        memory_path=sorted(memory_candidates,key=str)[0]
        runtime_obj=load_json(runtime_path)

        records=load_clean_train_pool_records(
            manifest_path=manifest,
            expected_manifest_sha256=train["manifest_sha256"],
            train_root=Path(train["train_root"]),
            expected_pool="TRAIN_UPDATE",
            expected_count=train["row_count"],
        )
        schedule=build_clean_train_schedule(
            records=records,
            train_pool="TRAIN_UPDATE",
            seed=train["rollout_seed"],
        )
        total=len(schedule)
        if total!=int(shard_plan["total_schedule_count"]):
            raise RuntimeError("GLOBAL_SCHEDULE_COUNT_CHANGED")

        profile_path=evidence/"ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json"
        if not profile_path.is_file():
            raise RuntimeError("GLOBAL_PROFILE_AUTHORITY_MISSING")
        profile_sha=sha_file(profile_path)

        request=RoundRolloutCollectionRequestV1(
            round_id=binding["round_id"],
            execution_attempt_id=str(shard_plan["activation_id"]),
            parent_policy_id=binding["parent_policy_id"],
            parent_policy_artifact_sha256=runtime_obj["policy_runtime_manifest_sha256"],
            policy_runtime_binding_sha256=sha_file(runtime_path),
            execution_profile_sha256=profile_sha,
            train_update_manifest_sha256=train["manifest_sha256"],
            round_memory_runtime_authority_sha256=sha_file(memory_path),
            round_start_memory_snapshot_sha256=memory["active_snapshot_sha256"],
            token_budget_contract_sha256=memory["token_budget_contract_sha256"],
            execution_namespace=str(shard_plan["activation_id"]),
            rollout_seed=train["rollout_seed"],
        )
        request_path=evidence/"ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json"
        if not request_path.exists():
            write_new_json(request_path,request.to_dict())
        elif load_json(request_path)!=request.to_dict():
            raise RuntimeError("GLOBAL_REQUEST_BYTES_CHANGED")

        rows_by_ordinal={}
        attempt_index=[]
        fatal_shards=[]
        for shard_id,(kind,path) in enumerate(shard_markers):
            assigned=shard_positions(total,shard_count,shard_id)
            if kind=="fatal":
                fatal=load_json(path)
                fatal_shards.append({
                    "shard_id":shard_id,
                    "fatal_path":str(path),
                    "fatal_sha256":sha_file(path),
                    "fatal_error_type":fatal.get("error_type"),
                    "fatal_error_message":fatal.get("error_message"),
                })
                for ordinal in assigned:
                    cell=schedule[ordinal]
                    sidecar=state_root/"shards"/f"{shard_id:04d}"/f"synthetic-global-{ordinal:05d}.json"
                    if not sidecar.exists():
                        write_new_json(sidecar,{
                          "schema_id":"ROUND_ROLLOUT_CELL_TERMINAL_V1","schema_version":1,
                          "global_ordinal":ordinal,
                          "scientific_cell_id":cell.scientific_cell_id,
                          "execution_attempt_id":cell.execution_attempt_id,
                          "task_index":cell.cell.task_index,
                          "task_id":cell.cell.task_id,
                          "status":"INFRASTRUCTURE_INVALID",
                          "success":None,
                          "termination_reason":"SHARD_FATAL_BEFORE_COMPLETE_TERMINALS",
                          "shard_id":shard_id,
                        })
                    rows_by_ordinal[ordinal]={
                      "scientific_cell_id":cell.scientific_cell_id,
                      "execution_attempt_id":cell.execution_attempt_id,
                      "task_id":cell.cell.task_id,
                      "task_index":cell.cell.task_index,
                      "status":"INFRASTRUCTURE_INVALID",
                      "success":None,
                      "terminal_receipt_sha256":sha_file(sidecar),
                    }
                continue

            value=load_json(path)
            entries=value.get("rows")
            if not isinstance(entries,list):
                raise RuntimeError("SHARD_TERMINAL_ROWS_INVALID")
            observed_ordinals=[]
            for entry in entries:
                ordinal=entry.get("global_ordinal")
                if type(ordinal) is not int or ordinal in rows_by_ordinal:
                    raise RuntimeError("GLOBAL_ORDINAL_INVALID_OR_DUPLICATE")
                observed_ordinals.append(ordinal)
                rows_by_ordinal[ordinal]={
                  "scientific_cell_id":entry["scientific_cell_id"],
                  "execution_attempt_id":entry["execution_attempt_id"],
                  "task_id":entry["task_id"],
                  "task_index":entry["task_index"],
                  "status":entry["status"],
                  "success":entry["success"],
                  "terminal_receipt_sha256":entry["terminal_receipt_sha256"],
                }
                attempt_index.append({
                  "global_ordinal":ordinal,
                  "scientific_cell_id":entry["scientific_cell_id"],
                  "shard_id":shard_id,
                  "attempt_bundle_path":entry.get("attempt_bundle_path"),
                  "attempt_terminal_path":entry.get("attempt_terminal_path"),
                })
            if tuple(sorted(observed_ordinals))!=assigned:
                raise RuntimeError("SHARD_ORDINAL_COVERAGE_MISMATCH_"+str(shard_id))

        if set(rows_by_ordinal)!={*range(total)}:
            raise RuntimeError("GLOBAL_TERMINAL_COVERAGE_INCOMPLETE")

        terminals=[]
        for ordinal,cell in enumerate(schedule):
            row=rows_by_ordinal[ordinal]
            if (
                row["scientific_cell_id"]!=cell.scientific_cell_id
                or row["execution_attempt_id"]!=cell.execution_attempt_id
                or row["task_id"]!=cell.cell.task_id
                or row["task_index"]!=cell.cell.task_index
            ):
                raise RuntimeError("GLOBAL_SCHEDULE_IDENTITY_MISMATCH_"+str(ordinal))
            terminals.append(RoundEpisodeTerminalV1(**row))

        exec_binding=RoundRolloutExecutionBindingV1(
            request_sha256=request.request_sha256,
            rollout_control_source_sha256=sha_file(
                worktree/"src/pchsi/round_control/rollout_collection.py"
            ),
            clean_execution_binding_source_sha256=sha_file(
                worktree/"src/pchsi/round_control/clean_execution_binding.py"
            ),
            episode_evaluator_source_sha256=sha_file(
                worktree/"src/pchsi/evaluation/episode_evaluator.py"
            ),
            attempt_receipts_source_sha256=sha_file(
                worktree/"src/pchsi/round_control/attempt_receipts.py"
            ),
            policy_runtime_adapter_sha256=sha_file(
                worktree/"src/pchsi/evaluation/policy_attempt_adapter.py"
            ),
            scientific_execution_authorized=True,
        )
        exec_path=evidence/"ROUND_ROLLOUT_EXECUTION_BINDING_V1.json"
        if not exec_path.exists():
            write_new_json(exec_path,exec_binding.to_dict())

        universe=seal_rollout_universe(
            request_sha256=request.request_sha256,
            terminals=tuple(terminals),
        )
        universe_path=evidence/"ROUND_ROLLOUT_UNIVERSE_SEAL_V1.json"
        write_new_json(universe_path,universe.to_dict())

        failure_path=None
        if universe.scientific_rollout_valid:
            cohort=build_failure_cohort(universe)
            failure_path=evidence/"ROUND_FAILURE_COHORT_SELECTION_MANIFEST_V1.json"
            write_new_json(failure_path,cohort.to_dict())

        attempt_index_path=evidence/"ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1.json"
        write_new_json(attempt_index_path,{
          "schema_id":"ROUND_SHARDED_ATTEMPT_BUNDLE_INDEX_V1","schema_version":1,
          "request_sha256":request.request_sha256,
          "row_count":len(attempt_index),
          "rows":sorted(attempt_index,key=lambda x:x["global_ordinal"]),
          "fatal_shards":fatal_shards,
          "human_selection_performed":False,
        })

        handoff_path=evidence/"ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json"
        write_new_json(handoff_path,{
          "schema_id":"ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1","schema_version":1,
          "round_id":binding["round_id"],
          "parent_policy_id":binding["parent_policy_id"],
          "rollout_request_path":str(request_path),
          "rollout_request_sha256":sha_file(request_path),
          "rollout_execution_binding_path":str(exec_path),
          "rollout_execution_binding_sha256":sha_file(exec_path),
          "rollout_universe_path":str(universe_path),
          "rollout_universe_sha256":sha_file(universe_path),
          "failure_cohort_path":None if failure_path is None else str(failure_path),
          "failure_cohort_sha256":None if failure_path is None else sha_file(failure_path),
          "attempt_bundle_index_path":str(attempt_index_path),
          "attempt_bundle_index_sha256":sha_file(attempt_index_path),
          "scheduled_count":universe.scheduled_count,
          "success_count":universe.success_count,
          "failure_count":universe.failure_count,
          "infrastructure_invalid_count":universe.infrastructure_invalid_count,
          "protocol_invalid_count":universe.protocol_invalid_count,
          "scientific_rollout_valid":universe.scientific_rollout_valid,
          "shard_count":shard_count,
          "human_selection_performed":False,
          "benchmark_feedback_used":False,
          "memory_writeback_performed":False,
          "training_execution_performed":False,
          "next":(
            "AUTOMATIC_EVIDENCE_AND_ANALYZER_HANDOFF_FROM_V1232K_ROLLOUT"
            if universe.scientific_rollout_valid
            else "CAMPAIGN_INFRA_INVALID_FRESH_ATTEMPT_GOVERNANCE"
          ),
        })

        write_new_json(final_terminal,{
          "schema_id":"PCHSI_V1232K_GLOBAL_TERMINAL_V1","schema_version":1,
          "status":(
            "V1232K_REPAIRED_GATED_SHARDED_FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_COMPLETE_VALID"
            if universe.scientific_rollout_valid
            else "V1232K_REPAIRED_GATED_SHARDED_FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_PROTOCOL_INFRA_INVALID"
          ),
          "scheduled_count":universe.scheduled_count,
          "success_count":universe.success_count,
          "failure_count":universe.failure_count,
          "infrastructure_invalid_count":universe.infrastructure_invalid_count,
          "protocol_invalid_count":universe.protocol_invalid_count,
          "scientific_rollout_valid":universe.scientific_rollout_valid,
          "handoff_path":str(handoff_path),
          "handoff_sha256":sha_file(handoff_path),
          "shard_count":shard_count,
          "fatal_shard_count":len(fatal_shards),
          "human_scientific_decision_count":0,
          "training_execution_count":0,
          "memory_writeback_count":0,
        })
        return True
    finally:
        # Keep lock as durable proof that finalization was attempted.
        pass
