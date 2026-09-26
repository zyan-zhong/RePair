from __future__ import annotations

import gc
import importlib.util
from pathlib import Path
import sys
from typing import Any

from smoke.common import SmokeError


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SmokeError(f"MODULE_IMPORT_SPEC_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def execute_model_initialization_smoke(
    *,
    reviewed_root: Path,
    training_stage_binding_path: Path,
) -> dict[str, Any]:
    root_text = str(reviewed_root)
    if root_text not in sys.path:
        sys.path.insert(0, root_text)

    from round_training.contracts import load_stage_context

    context = load_stage_context(training_stage_binding_path)
    adapter = _load_module(
        context.runtime_adapter_path,
        "reviewed_training_runtime_adapter",
    )
    adapter.validate_profile_without_model_load(context)

    try:
        import torch
    except Exception as exc:
        raise SmokeError(f"TORCH_IMPORT_FAILED:{exc}") from exc

    if not torch.cuda.is_available():
        raise SmokeError("CUDA_UNAVAILABLE")
    if torch.cuda.device_count() != 1:
        raise SmokeError(
            f"VISIBLE_CUDA_DEVICE_COUNT_NOT_ONE:"
            f"{torch.cuda.device_count()}"
        )

    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()

    parent = adapter._load_parent_module(
        context.training_contract
    )
    adapter._install_parent_adapter(
        parent,
        context=context,
    )

    model = None
    result = None
    try:
        seed = context.training_contract["budget"]["training_seed"]
        model = parent.build_seeded_formal_lora_model(
            seed=seed,
            device="cuda",
        )

        trainable_names = tuple(
            parent.verify_lora_only_trainable_parameters(model)
        )
        if not trainable_names:
            raise SmokeError("NO_TRAINABLE_PARAMETERS")
        if any(
            "lora_" not in name.lower()
            for name in trainable_names
        ):
            raise SmokeError("NON_LORA_TRAINABLE_PARAMETER")

        target_modules = tuple(sorted(
            parent.actual_lora_target_module_suffixes(model)
        ))
        expected_modules = tuple(sorted(
            context.training_contract["peft"]["target_modules"]
        ))
        if target_modules != expected_modules:
            raise SmokeError(
                "TARGET_MODULE_BOUNDARY_MISMATCH:"
                + repr(target_modules)
                + ":"
                + repr(expected_modules)
            )

        initial_sha = parent.hash_trainable_parameters(model)
        expected_initial = context.training_contract["parent"][
            "final_trainable_parameter_sha256"
        ]
        if initial_sha != expected_initial:
            raise SmokeError(
                f"INITIAL_TRAINABLE_PARAMETER_SHA_MISMATCH:"
                f"{initial_sha}:{expected_initial}"
            )

        trainable_parameter_count = 0
        total_parameter_count = 0
        trainable_dtypes = set()
        for name, parameter in model.named_parameters():
            total_parameter_count += parameter.numel()
            if parameter.requires_grad:
                trainable_parameter_count += parameter.numel()
                trainable_dtypes.add(str(parameter.dtype))
                if parameter.grad is not None:
                    raise SmokeError(
                        f"GRADIENT_UNEXPECTEDLY_PRESENT:{name}"
                    )

        post_check_sha = parent.hash_trainable_parameters(model)
        if post_check_sha != initial_sha:
            raise SmokeError(
                "MODEL_PARAMETERS_CHANGED_DURING_SMOKE"
            )

        torch.cuda.synchronize()
        result = {
            "schema_id": (
                "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_RESULT_V1"
            ),
            "schema_version": 1,
            "round_id": context.binding["round_id"],
            "profile_id": context.binding["profile_id"],
            "stage_binding_sha256": context.binding[
                "stage_binding_sha256"
            ],
            "status": "PASS",
            "device_type": "cuda",
            "visible_cuda_device_count": 1,
            "torch_version": str(torch.__version__),
            "torch_cuda_version": str(torch.version.cuda),
            "cuda_device_name": torch.cuda.get_device_name(0),
            "base_model_revision": context.training_contract[
                "parent"
            ]["base_model_revision"],
            "parent_adapter_bundle_sha256": (
                context.training_contract["parent"][
                    "adapter_bundle_sha256"
                ]
            ),
            "expected_initial_trainable_parameter_sha256": (
                expected_initial
            ),
            "observed_initial_trainable_parameter_sha256": (
                initial_sha
            ),
            "post_check_trainable_parameter_sha256": (
                post_check_sha
            ),
            "trainable_parameter_name_count": len(
                trainable_names
            ),
            "trainable_parameter_name_sha256": (
                __import__("hashlib").sha256(
                    "\n".join(trainable_names).encode("utf-8")
                ).hexdigest()
            ),
            "trainable_parameter_count": trainable_parameter_count,
            "total_parameter_count": total_parameter_count,
            "trainable_dtypes": sorted(trainable_dtypes),
            "target_modules": list(target_modules),
            "model_train_mode": bool(model.training),
            "forward_count": 0,
            "backward_count": 0,
            "optimizer_constructed": False,
            "optimizer_step_count": 0,
            "training_execution_count": 0,
            "peak_cuda_memory_allocated_bytes": (
                torch.cuda.max_memory_allocated()
            ),
            "cuda_memory_allocated_before_unload_bytes": (
                torch.cuda.memory_allocated()
            ),
            "model_unloaded": False,
            "result_sha256": "",
        }
    finally:
        if model is not None:
            del model
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()

    if result is None:
        raise SmokeError("SMOKE_RESULT_NOT_CREATED")
    result["model_unloaded"] = True
    result["cuda_memory_allocated_after_unload_bytes"] = (
        torch.cuda.memory_allocated()
    )
    return result
