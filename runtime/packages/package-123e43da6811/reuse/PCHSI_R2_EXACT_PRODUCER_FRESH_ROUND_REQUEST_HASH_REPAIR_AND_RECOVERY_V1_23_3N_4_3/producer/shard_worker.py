from __future__ import annotations

import argparse
from dataclasses import asdict, replace as dataclass_replace
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import traceback

from safe_io import canonical_bytes, load_json, safe_extract_zip, sha_file, write_new_bytes, write_new_json
from shard_math import shard_positions
from formal_rollout_support import (
    CachedTokenizerFactory,
    _registration_id,
    build_environment_runtime_manifest,
    classify_episode_result,
    find_capsule_file_by_sha,
    load_module,
)
from global_finalize import try_finalize
from fresh_round_contract import (request_from_plan, validate_attempt_ordinal, schedule_for_attempt, validate_request_against_capsule, profile_from_binding)
from runtime_surface_preflight import validate_runtime_surface


def git(repo:Path,*args:str)->str:
    cp=subprocess.run(
      ["git","-C",str(repo),*args],
      stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,shell=False
    )
    if cp.returncode: raise RuntimeError("GIT_FAILED:"+":".join(args)+":"+cp.stderr.strip())
    return cp.stdout.strip()



def run_command(argv:list[str])->subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        shell=False,
        check=False,
    )


def _gate_config(shard_plan:dict[str,object])->tuple[int,set[str]]:
    raw=shard_plan.get("staged_release_gate")
    if not isinstance(raw,dict):
        raise RuntimeError("STAGED_RELEASE_GATE_MISSING")
    gate_id=raw.get("initially_release_only_shard_id")
    statuses=raw.get("scientific_terminal_statuses")
    if type(gate_id) is not int:
        raise RuntimeError("STAGED_RELEASE_GATE_ID_INVALID")
    if not isinstance(statuses,list) or not statuses:
        raise RuntimeError("STAGED_RELEASE_GATE_STATUSES_INVALID")
    if not all(isinstance(x,str) and x for x in statuses):
        raise RuntimeError("STAGED_RELEASE_GATE_STATUSES_INVALID")
    return gate_id,set(statuses)


def _write_gate_failure(
    *,
    state_root:Path,
    shard_id:int,
    shard_count:int,
    reason:str,
)->None:
    gate_failure=state_root/"PCHSI_V1232K_GATE_FAILURE_V1.json"
    if gate_failure.exists():
        return
    array_job_id=os.environ.get("SLURM_ARRAY_JOB_ID")
    cancellations=[]
    if array_job_id:
        for sibling in range(shard_count):
            if sibling==shard_id:
                continue
            target=array_job_id+"_"+str(sibling)
            cp=run_command(["scancel",target])
            cancellations.append({
                "target":target,
                "returncode":cp.returncode,
                "stderr":cp.stderr.strip(),
            })
    write_new_json(gate_failure,{
      "schema_id":"PCHSI_V1232K_GATE_FAILURE_V1",
      "schema_version":1,
      "gate_shard_id":shard_id,
      "array_job_id":array_job_id,
      "reason":reason,
      "held_sibling_cancellation_results":cancellations,
      "remaining_shards_release_authorized":False,
      "scientific_rollout_valid":False,
      "human_retry_decision_required":False,
    })


def _open_gate(
    *,
    state_root:Path,
    shard_id:int,
    classification:str,
)->None:
    receipt=state_root/"PCHSI_V1232K_FULL_ARRAY_RELEASE_RECEIPT_V1.json"
    if receipt.exists():
        return
    array_job_id=os.environ.get("SLURM_ARRAY_JOB_ID")
    if not array_job_id:
        raise RuntimeError("SLURM_ARRAY_JOB_ID_MISSING_FOR_GATE_RELEASE")
    cp=run_command(["scontrol","release",array_job_id])
    if cp.returncode!=0:
        raise RuntimeError(
            "FULL_ARRAY_RELEASE_FAILED:"+cp.stderr.strip()
        )
    write_new_json(receipt,{
      "schema_id":"PCHSI_V1232K_FULL_ARRAY_RELEASE_RECEIPT_V1",
      "schema_version":1,
      "array_job_id":array_job_id,
      "gate_shard_id":shard_id,
      "gate_scientific_terminal_classification":classification,
      "remaining_array_elements_released":True,
      "human_release_decision_required":False,
    })


def write_or_verify_json(path:Path,value:object)->None:
    payload=canonical_bytes(value)
    try:
        write_new_bytes(path,payload)
    except FileExistsError:
        if path.read_bytes()!=payload:
            raise RuntimeError("COMMON_ARTIFACT_IDENTITY_MISMATCH:"+str(path))


def synthetic_row(*,ordinal:int,cell,shard_id:int,reason:str,sidecar:Path)->dict[str,object]:
    value={
      "schema_id":"ROUND_ROLLOUT_CELL_TERMINAL_V1","schema_version":1,
      "global_ordinal":ordinal,"shard_id":shard_id,
      "scientific_cell_id":cell.scientific_cell_id,
      "execution_attempt_id":cell.execution_attempt_id,
      "task_index":cell.cell.task_index,"task_id":cell.cell.task_id,
      "status":"INFRASTRUCTURE_INVALID","success":None,
      "scientific_outcome_status":"NOT_PRODUCED",
      "operational_finalization_status":"NOT_STARTED",
      "termination_reason":reason,
      "attempt_terminal_path":None,
      "attempt_bundle_root":None,
    }
    write_new_json(sidecar,value)
    return {
      **value,
      "terminal_receipt_sha256":sha_file(sidecar),
    }


def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--state-root",required=True)
    ap.add_argument("--v1230-output-root",required=True)
    ap.add_argument("--capsule",required=True)
    ap.add_argument("--shard-plan",required=True)
    ap.add_argument("--shard-id",required=True,type=int)
    args=ap.parse_args()

    state_root=Path(args.state_root).resolve()
    v1230=Path(args.v1230_output_root).resolve()
    capsule=Path(args.capsule).resolve()
    shard_plan=load_json(Path(args.shard_plan))
    shard_id=int(args.shard_id)
    shard_count=int(shard_plan["shard_count"])
    if not 0<=shard_id<shard_count:
        raise SystemExit("STOP=SHARD_ID_OUT_OF_RANGE")
    gate_shard_id,gate_scientific_statuses=_gate_config(shard_plan)
    shard_root=state_root/"shards"/f"{shard_id:04d}"
    shard_root.mkdir(parents=True,exist_ok=True,mode=0o700)
    terminals_path=shard_root/"PCHSI_V1232S_SHARD_TERMINALS_V1.json"
    fatal_path=shard_root/"PCHSI_V1232S_SHARD_FATAL_V1.json"

    service=None;service_out=None;service_err=None
    extracted=shard_root/"capsule"
    schedule=None
    assigned=None
    rows=[]
    started=time.monotonic()

    try:
        if sha_file(capsule) != shard_plan["repaired_capsule_sha256"]:
            raise RuntimeError("SHARD_CAPSULE_SHA_CHANGED")
        if not extracted.exists():safe_extract_zip(capsule,extracted)
        binding=load_json(extracted/"ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_EXECUTION_BINDING_V1.json")
        allocation_contract=load_json(extracted/"ROUND_MEMORY_AWARE_GENERIC_ROLLOUT_ALLOCATION_PREFLIGHT_V1.json")
        worktree=v1230/"build/worktree"
        if git(worktree,"rev-parse","HEAD")!=binding["implementation_head"]:
            raise RuntimeError("SHARD_IMPLEMENTATION_HEAD_CHANGED")
        validate_runtime_surface(worktree,extracted)
        sys.path.insert(0,str(worktree/"src"))
        current_request=request_from_plan(shard_plan)
        validate_attempt_ordinal(shard_plan["fresh_execution_attempt_ordinal"])
        if current_request is None and shard_plan["fresh_execution_attempt_ordinal"] == 0:
            raise RuntimeError("ZERO_ORDINAL_REQUIRES_CURRENT_REQUEST_AUTHORITY")
        # Resolve only the input identities read by this original producer.
        runtime_path=find_capsule_file_by_sha(extracted,expected_sha256=binding["runtime_authority"]["runtime_binding_file_sha256"],suffixes=(".json",))
        memory_path=find_capsule_file_by_sha(extracted,expected_sha256=binding["memory_authority"]["runtime_identity_file_sha256"],suffixes=(".json",))
        if current_request is not None:
            _,bound_profile=profile_from_binding(binding)
            validate_request_against_capsule(current_request,binding,runtime_path,memory_path,bound_profile)

        alloc_mod=load_module("v1232s_alloc_"+str(shard_id),extracted/"allocation_preflight.py")
        import torch
        allocation=alloc_mod.validate_live_allocation(
          allocation_contract,os.environ,cuda_device_count=torch.cuda.device_count()
        )
        allocation["cuda_device_names"]=[
          torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())
        ]
        write_new_json(shard_root/"PCHSI_V1232S_ALLOCATION_PREFLIGHT_RESULT_V1.json",allocation)

        cache_root=shard_root/"runtime_cache"
        for key,sub in {
          "HOME":"home","XDG_CACHE_HOME":"xdg","HF_HOME":"hf",
          "HUGGINGFACE_HUB_CACHE":"hf_hub","TRANSFORMERS_CACHE":"transformers",
          "CUDA_CACHE_PATH":"cuda","TORCHINDUCTOR_CACHE_DIR":"torchinductor",
          "TRITON_CACHE_DIR":"triton","NUMBA_CACHE_DIR":"numba","MPLCONFIGDIR":"mpl",
        }.items():
            p=cache_root/sub;p.mkdir(parents=True,exist_ok=True);os.environ[key]=str(p)
        os.environ["PYTHONDONTWRITEBYTECODE"]="1"
        os.environ["TOKENIZERS_PARALLELISM"]="false"

        runtime_auth=binding["runtime_authority"]
        memory_auth=binding["memory_authority"]
        train_auth=binding["train_update_authority"]
        runtime_path=find_capsule_file_by_sha(
          extracted,expected_sha256=runtime_auth["runtime_binding_file_sha256"],suffixes=(".json",)
        )
        memory_path=find_capsule_file_by_sha(
          extracted,expected_sha256=memory_auth["runtime_identity_file_sha256"],suffixes=(".json",)
        )
        manifest_path=find_capsule_file_by_sha(
          extracted,expected_sha256=train_auth["manifest_sha256"],suffixes=(".jsonl",)
        )
        runtime=load_json(runtime_path)
        memory_identity=load_json(memory_path)

        service_mod=load_module(
          "v1232s_service_"+str(shard_id),
          extracted/"policy_runtime_lifecycle_source/policy_runtime_service.py"
        )
        pre=service_mod.probe_policy_runtime_service(runtime,timeout_seconds=1.0)
        write_new_json(shard_root/"PCHSI_V1232S_PRELAUNCH_ENDPOINT_PROBE_V1.json",pre)
        if pre.get("tcp_connect_ok") is True:
            raise RuntimeError("SHARD_PREEXISTING_ENDPOINT_OCCUPIED")

        launch=binding["service_launch_contract"]["launch_command"]
        service_out=(shard_root/"vllm.stdout.log").open("wb")
        service_err=(shard_root/"vllm.stderr.log").open("wb")
        service=subprocess.Popen(
          launch,cwd=worktree,env=dict(os.environ),
          stdout=service_out,stderr=service_err,start_new_session=True
        )
        deadline=time.monotonic()+1800
        readiness=None
        while time.monotonic()<deadline:
            if service.poll() is not None:
                raise RuntimeError("SHARD_VLLM_EXIT_BEFORE_READY:"+str(service.returncode))
            readiness=service_mod.probe_policy_runtime_service(runtime,timeout_seconds=1.0)
            if readiness.get("ready") is True:break
            time.sleep(2)
        if not isinstance(readiness,dict) or readiness.get("ready") is not True:
            raise RuntimeError("SHARD_VLLM_READINESS_TIMEOUT")
        write_new_json(shard_root/"PCHSI_V1232S_SERVICE_READINESS_V1.json",readiness)

        from pchsi.evaluation.alfworld_adapter import SpawnedAlfworldAdapter
        from pchsi.evaluation.artifact_publisher import ArtifactPublisher
        from pchsi.evaluation.budget import BudgetLimits
        from pchsi.evaluation.episode_evaluator import EpisodeDependencies,EpisodeExecutionConfig,run_single_episode
        from pchsi.evaluation.policy_attempt_adapter import BoundI1PolicyExecutionProfileV1,RoundMemoryPolicyAttemptAdapterV1
        from pchsi.evaluation.policy_client import HttpPolicyTransport,PolicyClient
        from pchsi.evaluation.rendered_prompt import LocalTokenizerPromptRenderer
        from pchsi.round_control.clean_execution_binding import load_clean_train_pool_records,build_clean_train_schedule
        from pchsi.evaluation.run_schedule import execution_attempt_id

        records=load_clean_train_pool_records(
          manifest_path=manifest_path,expected_manifest_sha256=train_auth["manifest_sha256"],
          train_root=Path(train_auth["train_root"]),expected_pool="TRAIN_UPDATE",
          expected_count=train_auth["row_count"]
        )
        schedule=build_clean_train_schedule(
          records=records,train_pool="TRAIN_UPDATE",seed=train_auth["rollout_seed"]
        )
        fresh_attempt_ordinal=validate_attempt_ordinal(shard_plan["fresh_execution_attempt_ordinal"])
        schedule=schedule_for_attempt(schedule,fresh_attempt_ordinal,execution_attempt_id)
        assigned=shard_positions(len(schedule),shard_count,shard_id)
        by_index={r.index:r for r in records}
        write_new_json(shard_root/"PCHSI_V1232S_SHARD_SCHEDULE_V1.json",{
          "schema_id":"PCHSI_V1232S_SHARD_SCHEDULE_V1","schema_version":1,
          "shard_id":shard_id,"shard_count":shard_count,
          "global_schedule_count":len(schedule),
          "global_ordinals":list(assigned),
          "scientific_cell_ids":[schedule[i].scientific_cell_id for i in assigned],
          "sharding_mode":shard_plan["sharding_mode"],
          "outcome_adaptive_assignment":False,
        })

        evidence=state_root/"round_evidence";evidence.mkdir(parents=True,exist_ok=True)
        profile_data=binding["policy_execution_profile"]
        profile=BoundI1PolicyExecutionProfileV1(
          served_model_name=profile_data["served_model_name"],
          continuation_request_contract=profile_data["continuation_request_contract"],
          policy_version=profile_data["policy_version"],
        )
        profile_artifact={
          "schema_id":"ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1","schema_version":1,
          "profile_kind":profile.profile_id,"arm_id":profile.arm_id,
          "policy_version":profile.policy_version,
          "served_model_name":profile.served_model_name,
          "continuation_request_contract":profile.continuation_request_contract,
        }
        profile_path=evidence/"ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1.json"
        write_or_verify_json(profile_path,profile_artifact)
        profile_sha=sha_file(profile_path)
        if current_request is not None and profile_sha!=current_request.execution_profile_sha256:
            raise RuntimeError("WORKER_CURRENT_PROFILE_SHA_MISMATCH")

        access_path=shard_root/"ROUND_TRAIN_UPDATE_ACCESS_AUTHORITY_V1.json"
        write_new_json(access_path,{
          "schema_id":"ROUND_TRAIN_UPDATE_ACCESS_AUTHORITY_V1","schema_version":1,
          "pool":"TRAIN_UPDATE","manifest_sha256":train_auth["manifest_sha256"],
          "row_count":len(records),"benchmark_feedback_authorized":False,
          "valid_seen_authorized":False,"valid_unseen_authorized":False,
          "train_select_authorized":False,"train_audit_authorized":False,
        })
        access_sha=sha_file(access_path)

        protocol_path=shard_root/"ROUND_MEMORY_AWARE_SHARDED_ROLLOUT_PROTOCOL_V1.json"
        write_new_json(protocol_path,{
          "schema_id":"ROUND_MEMORY_AWARE_SHARDED_ROLLOUT_PROTOCOL_V1","schema_version":1,
          "implementation_head":binding["implementation_head"],
          "shard_id":shard_id,"shard_count":shard_count,
          "global_schedule_count":len(schedule),"assigned_count":len(assigned),
          "memory_snapshot_sha256":memory_identity["active_snapshot_sha256"],
          "task_retry_count":0,"job_requeue_authorized":False,
          "fresh_execution_attempt_ordinal":fresh_attempt_ordinal,
          "same_round_memory_writeback_authorized":False,
          "training_execution_authorized":False,
        })
        protocol_sha=sha_file(protocol_path)

        game_path=shard_root/"ROUND_SHARD_GAMEFILE_IDENTITY_V1.json"
        write_new_json(game_path,{
          "schema_id":"ROUND_SHARD_GAMEFILE_IDENTITY_V1","schema_version":1,
          "shard_id":shard_id,
          "records":[
            {"global_ordinal":ordinal,"task_index":schedule[ordinal].cell.task_index,
             "gamefile":by_index[schedule[ordinal].cell.task_index].gamefile,
             "sha256":sha_file(Path(by_index[schedule[ordinal].cell.task_index].gamefile))}
            for ordinal in assigned
          ],
        })
        game_sha=sha_file(game_path)

        env_path=shard_root/"ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1.json"
        env_sha=build_environment_runtime_manifest(output_path=env_path,implementation_src=worktree/"src")
        schedule_sha=sha_file(shard_root/"PCHSI_V1232S_SHARD_SCHEDULE_V1.json")

        renderer=LocalTokenizerPromptRenderer(
          model_path=runtime["base_model_local_path"],
          revision=runtime["tokenizer_revision"],
          chat_template_sha256=runtime["chat_template_sha256"],
          tokenizer_factory=CachedTokenizerFactory(),
        )
        policy_client=PolicyClient(
          transport=HttpPolicyTransport(base_url=runtime["policy_base_url"],timeout_seconds=60.0)
        )
        memory_adapter=RoundMemoryPolicyAttemptAdapterV1(
          runtime_identity_path=memory_path,
          expected_runtime_identity_file_sha256=sha_file(memory_path),
        )
        publisher=ArtifactPublisher(run_root=shard_root/"rollout_run")
        cell_dir=shard_root/"cell_terminals";cell_dir.mkdir(parents=True,exist_ok=True)

        abort=False
        for local_index,ordinal in enumerate(assigned):
            cell=schedule[ordinal]
            sidecar=cell_dir/f"{ordinal:05d}.json"
            if abort:
                row=synthetic_row(
                  ordinal=ordinal,cell=cell,shard_id=shard_id,
                  reason="ABORTED_AFTER_PRIOR_INFRASTRUCTURE_OR_PROTOCOL_INVALID",
                  sidecar=sidecar,
                )
                rows.append(row);continue
            if service.poll() is not None:
                row=synthetic_row(
                  ordinal=ordinal,cell=cell,shard_id=shard_id,
                  reason="POLICY_SERVICE_EXITED_BEFORE_CELL",sidecar=sidecar
                )
                rows.append(row);abort=True;continue

            task=by_index[cell.cell.task_index]
            env=None
            try:
                env=SpawnedAlfworldAdapter.start(
                  exact_gamefile=Path(task.gamefile),
                  registration_id=_registration_id(state_root.name+"-"+str(shard_id),task.index),
                  runtime_manifest_sha256=env_sha,
                )
                config=EpisodeExecutionConfig(
                  run_id=state_root.name,cell=cell.cell,
                  execution_attempt_id=cell.execution_attempt_id,
                  attempt_ordinal=cell.attempt_ordinal,task=task,seed=cell.cell.seed,
                  evaluator_commit=binding["implementation_head"],
                  design_merge_commit=binding["implementation_head"],
                  runtime_core_commit=binding["implementation_head"],
                  raw_protocol_sha256=protocol_sha,split_access_sha256=access_sha,
                  gamefile_identity_manifest_sha256=game_sha,
                  environment_runtime_manifest_sha256=env_sha,
                  policy_runtime_manifest_sha256=runtime["policy_runtime_manifest_sha256"],
                  policy_request_schema_sha256=binding["policy_request_schema_sha256"],
                  run_schedule_sha256=schedule_sha,
                  gamefile_sha256=sha_file(Path(task.gamefile)),
                  budget_limits=BudgetLimits(),
                )
                result=run_single_episode(
                  config=config,
                  dependencies=EpisodeDependencies(
                    environment=env,policy_client=policy_client,prompt_renderer=renderer,
                    artifact_publisher=publisher,policy_execution_profile=profile,
                    policy_attempt_adapter=memory_adapter,
                  ),
                )
                attempt_terminal=(
                  shard_root/"rollout_run"/"attempt_ledger"/f"{cell.execution_attempt_id}.terminal.json"
                )
                receipt=load_json(attempt_terminal) if attempt_terminal.is_file() else None
                classification=classify_episode_result(result=result,terminal_receipt=receipt)
                value={
                  "schema_id":"ROUND_ROLLOUT_CELL_TERMINAL_V1","schema_version":1,
                  "global_ordinal":ordinal,"shard_id":shard_id,
                  "scientific_cell_id":cell.scientific_cell_id,
                  "execution_attempt_id":cell.execution_attempt_id,
                  "task_index":task.index,"task_id":task.task_id,
                  "status":classification,
                  "success":result.success if classification in {"SCIENTIFIC_SUCCESS","SCIENTIFIC_FAILURE"} else None,
                  "scientific_outcome_status":result.scientific_outcome_status.value,
                  "operational_finalization_status":result.operational_finalization_status.value,
                  "termination_reason":result.termination_reason,
                  "attempt_terminal_path":str(attempt_terminal) if attempt_terminal.is_file() else None,
                  "attempt_bundle_root":str(shard_root/"rollout_run"/"attempts"),
                }
                write_new_json(sidecar,value)
                rows.append({**value,"terminal_receipt_sha256":sha_file(sidecar)})
                if shard_id==gate_shard_id and not (
                    state_root/"PCHSI_V1232K_FULL_ARRAY_RELEASE_RECEIPT_V1.json"
                ).exists():
                    if classification in gate_scientific_statuses:
                        _open_gate(
                            state_root=state_root,
                            shard_id=shard_id,
                            classification=classification,
                        )
                    else:
                        _write_gate_failure(
                            state_root=state_root,
                            shard_id=shard_id,
                            shard_count=shard_count,
                            reason=(
                                "GATE_FIRST_TERMINAL_NOT_SCIENTIFIC:"
                                +classification
                            ),
                        )
                if classification in {"INFRASTRUCTURE_INVALID","PROTOCOL_INVALID"}:
                    abort=True
            except BaseException as cell_error:
                if env is not None:
                    try:env.close()
                    except BaseException:pass
                value=synthetic_row(
                  ordinal=ordinal,cell=cell,shard_id=shard_id,
                  reason="CELL_EXECUTION_EXCEPTION:"+type(cell_error).__name__,
                  sidecar=sidecar,
                )
                value["exception_message"]=str(cell_error)[:1000]
                rows.append(value)
                if shard_id==gate_shard_id and not (
                    state_root/"PCHSI_V1232K_FULL_ARRAY_RELEASE_RECEIPT_V1.json"
                ).exists():
                    _write_gate_failure(
                        state_root=state_root,
                        shard_id=shard_id,
                        shard_count=shard_count,
                        reason=(
                            "GATE_FIRST_CELL_EXCEPTION:"
                            +type(cell_error).__name__
                        ),
                    )
                abort=True

        write_new_json(terminals_path,{
          "schema_id":"PCHSI_V1232S_SHARD_TERMINALS_V1","schema_version":1,
          "shard_id":shard_id,"shard_count":shard_count,
          "assigned_global_ordinals":list(assigned),
          "rows":rows,
          "completed_row_count":len(rows),
          "scientific_environment_execution_finished":True,
          "human_scientific_decision_count":0,
          "training_execution_count":0,
          "memory_writeback_count":0,
          "elapsed_seconds":time.monotonic()-started,
        })
        return 0

    except BaseException as exc:
        if shard_id==gate_shard_id and not (
            state_root/"PCHSI_V1232K_FULL_ARRAY_RELEASE_RECEIPT_V1.json"
        ).exists():
            try:
                _write_gate_failure(
                    state_root=state_root,
                    shard_id=shard_id,
                    shard_count=shard_count,
                    reason="GATE_SHARD_FATAL:"+type(exc).__name__,
                )
            except BaseException:
                pass
        if not fatal_path.exists():
            write_new_json(fatal_path,{
              "schema_id":"PCHSI_V1232S_SHARD_FATAL_V1","schema_version":1,
              "shard_id":shard_id,"shard_count":shard_count,
              "error_type":type(exc).__name__,"error_message":str(exc),
              "traceback":traceback.format_exc(),
              "assigned_global_ordinals":None if assigned is None else list(assigned),
              "scientific_environment_execution_finished":False,
              "human_scientific_decision_count":0,
            })
        return 0
    finally:
        if service is not None and service.poll() is None:
            try:os.killpg(service.pid,signal.SIGTERM);service.wait(timeout=60)
            except Exception:
                try:os.killpg(service.pid,signal.SIGKILL)
                except Exception:pass
        if service_out is not None:service_out.close()
        if service_err is not None:service_err.close()
        try:
            # Every shard may try; only the first after all markers exist finalizes.
            if extracted.exists():
                try_finalize(
                  state_root=state_root,worktree=v1230/"build/worktree",
                  extracted_capsule=extracted,shard_plan=shard_plan,
                )
        except BaseException as final_error:
            final_fail=state_root/"round_evidence"/"PCHSI_V1232K_GLOBAL_FINALIZE_FAILURE_V1.json"
            if not final_fail.exists():
                final_fail.parent.mkdir(parents=True,exist_ok=True)
                try:
                    write_new_json(final_fail,{
                      "schema_id":"PCHSI_V1232K_GLOBAL_FINALIZE_FAILURE_V1","schema_version":1,
                      "error_type":type(final_error).__name__,
                      "error_message":str(final_error),
                      "traceback":traceback.format_exc(),
                    })
                except BaseException:
                    pass

if __name__=="__main__":
    raise SystemExit(main())
