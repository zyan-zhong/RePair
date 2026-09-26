from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
from typing import Any

from round_training.common import (
    ContractError,
    load_json_object,
    require_sha,
    sha256_file,
)
from round_training.contracts import StageContext
from round_training.receipts import artifact_ref_for_output


SUPPORTED_SCHEMA = "ROUND_LOCAL_TRAINING_CONTRACT_V2"
SUPPORTED_ORDER_SCHEMA = "ROUND_SAMPLE_ORDER_MANIFEST_V2"
SUPPORTED_IDENTITY_DOMAIN = "SOURCE_EXAMPLE_SHA256"


def _input_ref(
    *,
    logical_name: str,
    retention_class: str,
    path: Path,
    expected_sha256: str,
    schema_id: str | None,
) -> dict[str, Any]:
    require_sha(path, expected_sha256, logical_name)
    return {
        "logical_name": logical_name,
        "retention_class": retention_class,
        "path": str(path.resolve()),
        "sha256": expected_sha256,
        "size_bytes": path.stat().st_size,
        "schema_id": schema_id,
    }


def _load_local_analyzer_records(
    contract: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    from pchsi.round_control.local_analyzer_training_adapter import (
        load_native_records,
    )

    dataset = contract["dataset"]
    path = Path(dataset["path"])
    manifest_path = Path(dataset["manifest_path"])

    require_sha(path, dataset["sha256"], "LOCAL_ANALYZER_NATIVE_DATASET")
    require_sha(
        manifest_path,
        dataset["manifest_file_sha256"],
        "LOCAL_ANALYZER_NATIVE_DATASET_MANIFEST",
    )

    records = load_native_records(
        dataset_path=path,
        manifest_path=manifest_path,
    )
    if len(records) != dataset["row_count"]:
        raise ContractError("LOCAL_ANALYZER_NATIVE_ROW_COUNT_CHANGED")

    expected_lengths = dataset["sequence_lengths"]
    total_targets = 0
    for ordinal, record in enumerate(records):
        if record["ordinal"] != ordinal:
            raise ContractError(
                f"LOCAL_ANALYZER_ORDINAL_CHANGED:{ordinal}"
            )
        tokenization = record["tokenization"]
        if (
            tokenization["sequence_token_count"]
            != expected_lengths[ordinal]
        ):
            raise ContractError(
                f"LOCAL_ANALYZER_SEQUENCE_LENGTH_CHANGED:{ordinal}"
            )
        total_targets += int(
            tokenization["response_loss_token_count"]
        )
    if total_targets != dataset["one_pass_target_loss_token_count"]:
        raise ContractError(
            "LOCAL_ANALYZER_ONE_PASS_TARGET_TOKEN_COUNT_CHANGED"
        )
    return records


def _verify_sample_order(
    *,
    records: tuple[dict[str, Any], ...],
    context: StageContext,
) -> None:
    order = context.sample_order
    contract = context.training_contract
    dataset = contract["dataset"]
    budget = contract["budget"]

    if order.get("schema_id") != SUPPORTED_ORDER_SCHEMA:
        raise ContractError("LOCAL_ANALYZER_SAMPLE_ORDER_SCHEMA_CHANGED")
    if order.get("identity_domain") != SUPPORTED_IDENTITY_DOMAIN:
        raise ContractError("LOCAL_ANALYZER_IDENTITY_DOMAIN_CHANGED")

    pass_orders = order["pass_orders"]
    groups = order["optimizer_groups"]
    flat_rows = []
    flat_identities = []

    for pass_index, pass_order in enumerate(pass_orders):
        for step_in_pass, start in enumerate(
            range(0, dataset["row_count"], budget["effective_batch_size"]),
            start=1,
        ):
            group_index = (
                pass_index
                * (dataset["row_count"] // budget["effective_batch_size"])
                + step_in_pass
                - 1
            )
            group = groups[group_index]
            ordinals = pass_order[
                start : start + budget["effective_batch_size"]
            ]
            expected_rows = [
                records[index]["source_example_sha256"]
                for index in ordinals
            ]
            expected_targets = sum(
                int(
                    records[index]["tokenization"][
                        "response_loss_token_count"
                    ]
                )
                for index in ordinals
            )
            if group["ordinals"] != ordinals:
                raise ContractError(
                    "LOCAL_ANALYZER_SAMPLE_ORDER_ORDINAL_MISMATCH"
                )
            if group["row_sha256s"] != expected_rows:
                raise ContractError(
                    "LOCAL_ANALYZER_SAMPLE_ORDER_ROW_ID_MISMATCH"
                )
            if group["source_identity_sha256s"] != expected_rows:
                raise ContractError(
                    "LOCAL_ANALYZER_SAMPLE_ORDER_SOURCE_ID_MISMATCH"
                )
            if group["target_loss_tokens"] != expected_targets:
                raise ContractError(
                    "LOCAL_ANALYZER_SAMPLE_ORDER_TOKEN_MISMATCH"
                )
            flat_rows.extend(expected_rows)
            flat_identities.extend(expected_rows)

    if flat_rows != order["ordered_row_sha256s"]:
        raise ContractError("LOCAL_ANALYZER_FLAT_ROW_ORDER_MISMATCH")
    if flat_identities != order["ordered_source_identity_sha256s"]:
        raise ContractError("LOCAL_ANALYZER_FLAT_IDENTITY_ORDER_MISMATCH")


def _validate_runtime_contract(context: StageContext) -> tuple[dict[str, Any], ...]:
    contract = context.training_contract
    if contract.get("schema_id") != SUPPORTED_SCHEMA:
        raise ContractError("LOCAL_ANALYZER_RUNTIME_REQUIRES_CONTRACT_V2")

    dataset = contract["dataset"]
    budget = contract["budget"]
    execution = contract["execution"]
    optimization = contract["optimization"]
    peft = contract["peft"]

    exact = {
        ("dataset", "trained_region"): "ASSISTANT_COMPLETION_SUFFIX_ONLY",
        ("dataset", "prompt_label_value"): -100,
        ("dataset", "packing"): False,
        ("dataset", "truncation"): False,
        ("dataset", "retokenization"): False,
        ("dataset", "reapply_chat_template"): False,
        ("execution", "world_size"): 2,
        ("execution", "per_rank_micro_batch_size"): 1,
        ("execution", "distributed_backend"): "nccl",
        ("execution", "bf16"): True,
        ("execution", "fp16"): False,
        ("execution", "gradient_checkpointing"): True,
        ("execution", "gradient_checkpointing_use_reentrant"): False,
        ("execution", "torch_compile"): False,
        ("optimization", "optimizer"): "adamw_torch",
        ("optimization", "lr_scheduler"): "linear",
        ("optimization", "fresh_optimizer"): True,
        ("optimization", "fresh_scheduler"): True,
        ("optimization", "resume_from_checkpoint"): False,
        ("peft", "method"): "LORA",
        ("peft", "base_weights_trainable"): False,
        ("peft", "bias"): "none",
        ("peft", "autocast_adapter_dtype"): True,
    }
    sections = {
        "dataset": dataset,
        "budget": budget,
        "execution": execution,
        "optimization": optimization,
        "peft": peft,
    }
    mismatches = []
    for (section, key), expected in exact.items():
        observed = sections[section].get(key)
        if observed != expected:
            mismatches.append((section, key, observed, expected))
    if mismatches:
        raise ContractError(
            "LOCAL_ANALYZER_DDP_RUNTIME_CAPABILITY_MISMATCH:"
            + repr(mismatches)
        )

    if budget["micro_batch_size"] != 1:
        raise ContractError("LOCAL_ANALYZER_PER_RANK_MICRO_BATCH_CHANGED")
    if budget["gradient_accumulation_steps"] != 1:
        raise ContractError("LOCAL_ANALYZER_GRAD_ACCUM_CHANGED")
    if budget["effective_batch_size"] != 2:
        raise ContractError("LOCAL_ANALYZER_GLOBAL_BATCH_CHANGED")

    if dataset["row_adapter"].get("identity_domain") != SUPPORTED_IDENTITY_DOMAIN:
        raise ContractError("LOCAL_ANALYZER_IDENTITY_DOMAIN_CHANGED")
    if (
        dataset["row_adapter"].get("source_identity_sha_field")
        != "source_example_sha256"
    ):
        raise ContractError("LOCAL_ANALYZER_SOURCE_IDENTITY_FIELD_CHANGED")

    parent = contract.get("parent")
    if not isinstance(parent, dict):
        raise ContractError("LOCAL_ANALYZER_PARENT_SECTION_MISSING")
    for key in (
        "base_model_path",
        "base_model_revision",
        "zero_step_adapter_path",
        "zero_step_adapter_bundle_sha256",
    ):
        value = parent.get(key)
        if not isinstance(value, str) or not value:
            raise ContractError(
                "LOCAL_ANALYZER_PARENT_FIELD_INVALID:" + key
            )

    records = _load_local_analyzer_records(contract)
    _verify_sample_order(
        records=records,
        context=context,
    )
    return records


def validate_profile_without_model_load(
    context: StageContext,
) -> dict[str, Any]:
    records = _validate_runtime_contract(context)
    contract = context.training_contract
    return {
        "record_count": len(records),
        "optimizer_step_count": contract["budget"]["optimizer_steps"],
        "world_size": contract["execution"]["world_size"],
        "effective_batch_size": contract["budget"]["effective_batch_size"],
        "one_pass_target_loss_token_count": contract["dataset"][
            "one_pass_target_loss_token_count"
        ],
        "identity_domain": SUPPORTED_IDENTITY_DOMAIN,
    }


def input_artifact_refs(
    context: StageContext,
) -> list[dict[str, Any]]:
    contract = context.training_contract
    _validate_runtime_contract(context)
    dataset = contract["dataset"]
    parent = contract["parent"]
    provenance = contract["provenance"]

    refs = [
        _input_ref(
            logical_name="LOCAL_ANALYZER_NATIVE_DATASET",
            retention_class="TRAINING_DATASET",
            path=Path(dataset["path"]),
            expected_sha256=dataset["sha256"],
            schema_id=dataset["row_adapter"]["schema_id"],
        ),
        _input_ref(
            logical_name="LOCAL_ANALYZER_NATIVE_DATASET_MANIFEST",
            retention_class="TRAINING_DATASET_MANIFEST",
            path=Path(dataset["manifest_path"]),
            expected_sha256=dataset["manifest_file_sha256"],
            schema_id="LOCAL_ANALYZER_BOOTSTRAP_TRAINER_NATIVE_MANIFEST_V1",
        ),
        _input_ref(
            logical_name="LOCAL_ANALYZER_FINAL_PROFILE",
            retention_class="SCIENTIFIC_CONFIG",
            path=Path(provenance["final_profile_path"]),
            expected_sha256=provenance["final_profile_sha256"],
            schema_id="LOCAL_ANALYZER_BOOTSTRAP_FINAL_TRAINING_PROFILE_V1",
        ),
        _input_ref(
            logical_name="LOCAL_ANALYZER_DDP_SAMPLE_ORDER_AUTHORITY",
            retention_class="SCIENTIFIC_CONFIG",
            path=Path(provenance["stage6ag_sample_order_path"]),
            expected_sha256=provenance["stage6ag_sample_order_sha256"],
            schema_id="LOCAL_ANALYZER_BOOTSTRAP_DDP_SAMPLE_ORDER_V1",
        ),
    ]

    adapter_root = Path(parent["zero_step_adapter_path"])
    adapter_manifest = Path(parent["zero_step_adapter_manifest_path"])
    refs.append(
        _input_ref(
            logical_name="ZERO_STEP_ADAPTER_MANIFEST",
            retention_class="MODEL_ARTIFACT_MANIFEST",
            path=adapter_manifest,
            expected_sha256=parent["zero_step_adapter_manifest_sha256"],
            schema_id=None,
        )
    )
    for relative, expected_sha in parent["zero_step_adapter_files"].items():
        refs.append(
            _input_ref(
                logical_name=(
                    "ZERO_STEP_ADAPTER_FILE_"
                    + relative.upper().replace(".", "_").replace("/", "_")
                ),
                retention_class="MODEL_ARTIFACT",
                path=adapter_root / relative,
                expected_sha256=expected_sha,
                schema_id=None,
            )
        )
    return refs


def _hash_trainable_parameters(model) -> str:
    digest = hashlib.sha256()
    for name, parameter in sorted(
        (
            (name, parameter)
            for name, parameter in model.named_parameters()
            if parameter.requires_grad
        ),
        key=lambda item: item[0],
    ):
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(
            parameter.detach()
            .float()
            .cpu()
            .contiguous()
            .numpy()
            .tobytes()
        )
    return digest.hexdigest()


def _adapter_file_manifest(adapter_dir: Path) -> dict[str, Any]:
    files = {}
    for path in sorted(
        child
        for child in adapter_dir.rglob("*")
        if child.is_file() and not child.is_symlink()
    ):
        relative = path.relative_to(adapter_dir).as_posix()
        files[relative] = {
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        }
    if not files:
        raise RuntimeError("saved adapter contains no files")
    bundle = hashlib.sha256(
        json.dumps(
            files,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    return {
        "schema_id": "ROUND_TRAINING_ADAPTER_ARTIFACT_MANIFEST_V1",
        "schema_version": 1,
        "files": files,
        "adapter_bundle_sha256": bundle,
    }


def _seed_for_sample(training_seed: int, ordinal: int) -> int:
    return training_seed + 1009 * (ordinal + 1)


def _worker_main(request_path: Path) -> int:
    import torch
    import torch.distributed as dist
    from torch.nn.parallel import DistributedDataParallel as DDP
    from peft import PeftModel
    from transformers import (
        AutoModelForCausalLM,
        get_linear_schedule_with_warmup,
    )

    request = load_json_object(request_path)
    contract = request["training_contract"]
    sample_order = request["sample_order"]
    output_dir = Path(request["output_dir"]).resolve()
    dataset_path = Path(contract["dataset"]["path"])

    local_rank = int(os.environ["LOCAL_RANK"])
    rank = int(os.environ["RANK"])
    world_size = int(os.environ["WORLD_SIZE"])
    if world_size != contract["execution"]["world_size"]:
        raise RuntimeError("DDP_WORLD_SIZE_RUNTIME_MISMATCH")
    if torch.cuda.device_count() != world_size:
        raise RuntimeError("VISIBLE_GPU_COUNT_WORLD_SIZE_MISMATCH")

    torch.cuda.set_device(local_rank)
    device = torch.device(f"cuda:{local_rank}")

    # Load model + exact PEFT adapter BEFORE process-group init. This preserves
    # the Stage6AF fix and avoids PEFT entering its TP state-dict helper.
    if dist.is_initialized():
        raise RuntimeError("PROCESS_GROUP_INITIALIZED_BEFORE_PEFT_LOAD")

    training_seed = int(contract["budget"]["training_seed"])
    torch.manual_seed(training_seed)
    torch.cuda.manual_seed_all(training_seed)

    base = AutoModelForCausalLM.from_pretrained(
        contract["parent"]["base_model_path"],
        revision=contract["parent"]["base_model_revision"],
        local_files_only=True,
        trust_remote_code=False,
        torch_dtype=torch.bfloat16,
        low_cpu_mem_usage=True,
    )
    base.config.use_cache = False
    base.to(device)

    model = PeftModel.from_pretrained(
        base,
        contract["parent"]["zero_step_adapter_path"],
        is_trainable=True,
        autocast_adapter_dtype=contract["peft"][
            "autocast_adapter_dtype"
        ],
    )
    model.train()
    model.config.use_cache = False

    gc_target = model.get_base_model()
    gc_target.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )
    if not bool(getattr(gc_target, "is_gradient_checkpointing", False)):
        raise RuntimeError("GRADIENT_CHECKPOINTING_NOT_ACTIVE")

    trainable = [
        parameter
        for _, parameter in model.named_parameters()
        if parameter.requires_grad
    ]
    if not trainable:
        raise RuntimeError("NO_TRAINABLE_PARAMETERS")
    if any(
        "lora_" not in name.lower()
        for name, parameter in model.named_parameters()
        if parameter.requires_grad
    ):
        raise RuntimeError("NON_LORA_TRAINABLE_PARAMETER")

    initial_hash = _hash_trainable_parameters(model)

    dist.init_process_group(
        backend=contract["execution"]["distributed_backend"]
    )
    ddp = DDP(
        model,
        device_ids=[local_rank],
        output_device=local_rank,
        broadcast_buffers=False,
        find_unused_parameters=False,
    )

    optimizer = torch.optim.AdamW(
        trainable,
        lr=float(contract["optimization"]["learning_rate"]),
        betas=(
            float(contract["optimization"]["adam_beta1"]),
            float(contract["optimization"]["adam_beta2"]),
        ),
        eps=float(contract["optimization"]["adam_epsilon"]),
        weight_decay=float(contract["optimization"]["weight_decay"]),
    )
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=int(contract["optimization"]["warmup_steps"]),
        num_training_steps=int(contract["budget"]["optimizer_steps"]),
    )

    rows = [
        json.loads(line)
        for line in dataset_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    if len(rows) != contract["dataset"]["row_count"]:
        raise RuntimeError("WORKER_DATASET_ROW_COUNT_MISMATCH")

    ledger_path = output_dir / "training_step_ledger.jsonl"
    if rank == 0 and ledger_path.exists():
        raise RuntimeError("TRAINING_STEP_LEDGER_ALREADY_EXISTS")

    optimizer_step_count = 0
    total_target_tokens = 0
    all_losses_finite = True
    all_grad_norms_finite = True
    rank_peak_reserved_gib = 0.0

    groups = sample_order["optimizer_groups"]
    for group in groups:
        if len(group["ordinals"]) != world_size:
            raise RuntimeError("DDP_GROUP_SIZE_WORLD_SIZE_MISMATCH")

        ordinal = int(group["ordinals"][rank])
        row = rows[ordinal]
        tokenization = row["tokenization"]
        input_ids = torch.tensor(
            [tokenization["input_ids"]],
            dtype=torch.long,
            device=device,
        )
        labels = torch.tensor(
            [tokenization["labels"]],
            dtype=torch.long,
            device=device,
        )
        attention_mask = torch.ones_like(input_ids, dtype=torch.long)

        seed = _seed_for_sample(training_seed, ordinal)
        torch.manual_seed(seed)
        torch.cuda.manual_seed_all(seed)

        optimizer.zero_grad(set_to_none=True)
        output = ddp(
            input_ids=input_ids,
            attention_mask=attention_mask,
            labels=labels,
            use_cache=False,
        )
        loss = output.loss
        if loss is None or not torch.isfinite(loss).item():
            all_losses_finite = False
            raise RuntimeError("NONFINITE_LOSS")

        loss.backward()
        grad_norm = torch.nn.utils.clip_grad_norm_(
            trainable,
            max_norm=float(contract["optimization"]["max_grad_norm"]),
        )
        if not torch.isfinite(torch.as_tensor(grad_norm)).item():
            all_grad_norms_finite = False
            raise RuntimeError("NONFINITE_GRAD_NORM")

        optimizer.step()
        scheduler.step()
        optimizer_step_count += 1

        local_metrics = {
            "rank": rank,
            "ordinal": ordinal,
            "source_example_sha256": row["source_identity"][
                "source_example_sha256"
            ],
            "stage_id": row["source_identity"]["stage_id"],
            "sequence_token_count": int(
                tokenization["sequence_token_count"]
            ),
            "response_loss_token_count": int(
                tokenization["response_loss_token_count"]
            ),
            "sample_seed": seed,
            "loss": float(loss.detach().float().cpu().item()),
            "grad_norm": float(torch.as_tensor(grad_norm).detach().cpu().item()),
        }
        gathered = [None for _ in range(world_size)]
        dist.all_gather_object(gathered, local_metrics)

        group_target_tokens = sum(
            int(item["response_loss_token_count"])
            for item in gathered
        )
        if group_target_tokens != int(group["target_loss_tokens"]):
            raise RuntimeError("RUNTIME_GROUP_TARGET_TOKEN_MISMATCH")
        total_target_tokens += group_target_tokens

        if rank == 0:
            ledger_row = {
                "schema_id": "ROUND_TRAINING_STEP_LEDGER_V1",
                "schema_version": 1,
                "global_step": optimizer_step_count,
                "world_size": world_size,
                "global_effective_batch_size": int(
                    contract["budget"]["effective_batch_size"]
                ),
                "rank_metrics": gathered,
                "target_loss_tokens": group_target_tokens,
                "learning_rate_after_step": float(
                    scheduler.get_last_lr()[0]
                ),
                "all_losses_finite": True,
                "all_grad_norms_finite": True,
            }
            with ledger_path.open("a", encoding="utf-8") as handle:
                handle.write(
                    json.dumps(
                        ledger_row,
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                    + "\n"
                )
                handle.flush()
                os.fsync(handle.fileno())

        rank_peak_reserved_gib = max(
            rank_peak_reserved_gib,
            torch.cuda.max_memory_reserved(device) / (1024 ** 3),
        )
        dist.barrier()

    if optimizer_step_count != contract["budget"]["optimizer_steps"]:
        raise RuntimeError("RUNTIME_OPTIMIZER_STEP_COUNT_MISMATCH")
    if total_target_tokens != contract["budget"]["target_loss_token_budget"]:
        raise RuntimeError("RUNTIME_TARGET_TOKEN_BUDGET_MISMATCH")

    final_hash = _hash_trainable_parameters(model)
    if final_hash == initial_hash:
        raise RuntimeError("TRAINABLE_STATE_UNCHANGED_AFTER_OPTIMIZER")

    hashes = [None for _ in range(world_size)]
    dist.all_gather_object(hashes, final_hash)
    if len(set(hashes)) != 1:
        raise RuntimeError("DDP_FINAL_TRAINABLE_PARAMETER_HASH_DIVERGED")

    rank_memory = [None for _ in range(world_size)]
    dist.all_gather_object(rank_memory, rank_peak_reserved_gib)

    adapter_dir = output_dir / "adapter"
    if rank == 0:
        ddp.module.save_pretrained(
            adapter_dir,
            safe_serialization=True,
        )
    dist.barrier()

    # Important: destroy PG before PEFT reload to preserve the Stage6AF load
    # order compatibility boundary.
    dist.destroy_process_group()

    if rank == 0:
        manifest = _adapter_file_manifest(adapter_dir)
        manifest.update(
            {
                "round_id": contract["round_id"],
                "profile_id": contract["profile_id"],
                "initial_trainable_parameter_sha256": initial_hash,
                "final_trainable_parameter_sha256": final_hash,
                "world_size": world_size,
            }
        )
        manifest_path = output_dir / "adapter_artifact_manifest.json"
        manifest_path.write_text(
            json.dumps(
                manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

        # Save/reload proof occurs only after the process group is destroyed.
        del ddp
        del model
        del base
        torch.cuda.empty_cache()

        reload_base = AutoModelForCausalLM.from_pretrained(
            contract["parent"]["base_model_path"],
            revision=contract["parent"]["base_model_revision"],
            local_files_only=True,
            trust_remote_code=False,
            torch_dtype=torch.bfloat16,
            low_cpu_mem_usage=True,
        )
        reload_base.to(device)
        reloaded = PeftModel.from_pretrained(
            reload_base,
            str(adapter_dir),
            is_trainable=True,
            autocast_adapter_dtype=contract["peft"][
                "autocast_adapter_dtype"
            ],
        )
        reload_hash = _hash_trainable_parameters(reloaded)
        if reload_hash != final_hash:
            raise RuntimeError("SAVED_ADAPTER_RELOAD_HASH_MISMATCH")

        run_manifest = {
            "schema_id": "ROUND_TRAINING_FORMAL_RUN_MANIFEST_V1",
            "schema_version": 1,
            "round_id": contract["round_id"],
            "profile_id": contract["profile_id"],
            "condition_id": contract["condition_id"],
            "run_status": "FORMAL_TRAINING_COMPLETED",
            "role": "LOCAL_ANALYZER",
            "repo_head": contract["repo_head"],
            "world_size": world_size,
            "global_effective_batch_size": int(
                contract["budget"]["effective_batch_size"]
            ),
            "optimizer_step_count": optimizer_step_count,
            "dataset_pass_count": int(contract["budget"]["epochs"]),
            "target_loss_token_count": total_target_tokens,
            "all_losses_finite": all_losses_finite,
            "all_grad_norms_finite": all_grad_norms_finite,
            "initial_trainable_parameter_sha256": initial_hash,
            "final_trainable_parameter_sha256": final_hash,
            "reloaded_trainable_parameter_sha256": reload_hash,
            "adapter_bundle_sha256": manifest["adapter_bundle_sha256"],
            "rank_peak_cuda_memory_reserved_gib": rank_memory,
            "optimizer": contract["optimization"],
            "checkpoint_rule": contract["execution"]["checkpoint_rule"],
            "gradient_checkpointing": True,
            "gradient_checkpointing_use_reentrant": False,
            "peft_loaded_before_process_group_init": True,
            "process_group_destroyed_before_reload": True,
            "environment_upgrade_used": False,
            "tensor_parallel_used": False,
            "provider_call_count": 0,
            "environment_call_count": 0,
        }
        run_manifest_path = output_dir / "formal_run_manifest.json"
        run_manifest_path.write_text(
            json.dumps(
                run_manifest,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )

    return 0


def execute_training_stage(
    *,
    context: StageContext,
    output_dir: Path,
    runner_freeze_root_sha256: str,
) -> dict[str, Any]:
    _validate_runtime_contract(context)

    if output_dir.exists():
        raise ContractError("AUTHORIZED_OUTPUT_ALREADY_EXISTS")
    output_dir.mkdir(parents=True, exist_ok=False)

    request = {
        "schema_id": "LOCAL_ANALYZER_DDP_WORKER_REQUEST_V1",
        "schema_version": 1,
        "runner_freeze_root_sha256": runner_freeze_root_sha256,
        "training_contract": context.training_contract,
        "sample_order": context.sample_order,
        "output_dir": str(output_dir),
    }
    request_path = output_dir / "ddp_worker_request.json"
    request_path.write_text(
        json.dumps(
            request,
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    worker_stdout = output_dir / "ddp_worker.stdout.log"
    worker_stderr = output_dir / "ddp_worker.stderr.log"

    world_size = int(context.training_contract["execution"]["world_size"])
    command = [
        sys.executable,
        "-m",
        "torch.distributed.run",
        "--standalone",
        "--nnodes=1",
        f"--nproc-per-node={world_size}",
        str(Path(__file__).resolve()),
        "--worker-request",
        str(request_path),
    ]

    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"
    env["PYTORCH_ALLOC_CONF"] = "expandable_segments:True"

    with (
        worker_stdout.open("w", encoding="utf-8") as stdout_handle,
        worker_stderr.open("w", encoding="utf-8") as stderr_handle,
    ):
        process = subprocess.run(
            command,
            cwd=str(context.package_root),
            env=env,
            text=True,
            stdout=stdout_handle,
            stderr=stderr_handle,
        )

    if process.returncode != 0:
        raise ContractError(
            "LOCAL_ANALYZER_DDP_WORKER_FAILED:"
            + str(process.returncode)
            + ":"
            + str(worker_stderr)
        )

    ledger = output_dir / "training_step_ledger.jsonl"
    run_manifest = output_dir / "formal_run_manifest.json"
    adapter_manifest = output_dir / "adapter_artifact_manifest.json"

    for path in (ledger, run_manifest, adapter_manifest):
        if not path.is_file():
            raise ContractError(
                "LOCAL_ANALYZER_DDP_OUTPUT_MISSING:" + str(path)
            )

    manifest = load_json_object(run_manifest)
    expected_steps = context.training_contract["budget"]["optimizer_steps"]
    if manifest.get("optimizer_step_count") != expected_steps:
        raise ContractError("LOCAL_ANALYZER_DDP_STEP_RECEIPT_MISMATCH")
    if manifest.get("target_loss_token_count") != context.training_contract[
        "budget"
    ]["target_loss_token_budget"]:
        raise ContractError("LOCAL_ANALYZER_DDP_TOKEN_RECEIPT_MISMATCH")

    artifacts = [
        artifact_ref_for_output(
            logical_name="TRAINING_STEP_LEDGER",
            retention_class="RAW_EVIDENCE",
            path=ledger,
            schema_id="ROUND_TRAINING_STEP_LEDGER_V1",
        ),
        artifact_ref_for_output(
            logical_name="FORMAL_RUN_MANIFEST",
            retention_class="VALIDATED_SCIENTIFIC_ARTIFACT",
            path=run_manifest,
            schema_id="ROUND_TRAINING_FORMAL_RUN_MANIFEST_V1",
        ),
        artifact_ref_for_output(
            logical_name="ADAPTER_ARTIFACT_MANIFEST",
            retention_class="VALIDATED_SCIENTIFIC_ARTIFACT",
            path=adapter_manifest,
            schema_id="ROUND_TRAINING_ADAPTER_ARTIFACT_MANIFEST_V1",
        ),
        artifact_ref_for_output(
            logical_name="DDP_WORKER_STDOUT",
            retention_class="RAW_EVIDENCE",
            path=worker_stdout,
            schema_id=None,
        ),
        artifact_ref_for_output(
            logical_name="DDP_WORKER_STDERR",
            retention_class="RAW_EVIDENCE",
            path=worker_stderr,
            schema_id=None,
        ),
        artifact_ref_for_output(
            logical_name="DDP_WORKER_REQUEST",
            retention_class="SCIENTIFIC_CONFIG",
            path=request_path,
            schema_id="LOCAL_ANALYZER_DDP_WORKER_REQUEST_V1",
        ),
    ]
    return {
        "artifacts": artifacts,
        "run_manifest": manifest,
    }


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--worker-request", type=Path)
    return parser


def main(argv=None) -> int:
    args = _build_argument_parser().parse_args(argv)
    if args.worker_request is None:
        raise SystemExit("--worker-request is required for worker execution")
    return _worker_main(args.worker_request.resolve())


if __name__ == "__main__":
    raise SystemExit(main())
