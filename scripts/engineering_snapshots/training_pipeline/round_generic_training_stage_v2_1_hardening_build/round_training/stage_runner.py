from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import traceback
from typing import Any

from .common import (
    ContractError,
    require_sha,
    write_json_create_once,
)
from .contracts import (
    StageContext,
    load_execution_authorization,
    load_stage_context,
)
from .receipts import (
    build_input_artifact_index,
    build_output_artifact_index,
    build_stage_receipt,
    create_attempt_root,
    write_attempt_json,
)


RUNNER_FREEZE_ENV = "ROUND_TRAINING_RUNNER_FREEZE_ROOT_SHA256"


def reject_ambient_environment(context: StageContext) -> None:
    forbidden = context.training_contract["execution"].get(
        "ambient_environment_variables_forbidden",
        [],
    )
    present = [
        name
        for name in forbidden
        if os.environ.get(name) not in (None, "")
    ]
    if present:
        raise ContractError(
            "AMBIENT_ENVIRONMENT_FORBIDDEN:"
            + ",".join(sorted(present))
        )


def _load_runtime_adapter(context: StageContext):
    path = context.runtime_adapter_path
    spec = importlib.util.spec_from_file_location(
        "round_training_runtime_adapter",
        path,
    )
    if spec is None or spec.loader is None:
        raise ContractError("RUNTIME_ADAPTER_IMPORT_SPEC_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    required = (
        "validate_profile_without_model_load",
        "input_artifact_refs",
        "execute_training_stage",
    )
    for name in required:
        if not callable(getattr(module, name, None)):
            raise ContractError(
                f"RUNTIME_ADAPTER_INTERFACE_MISSING:{name}"
            )
    return module


def _input_refs(
    context: StageContext,
    adapter,
) -> list[dict[str, Any]]:
    refs = []
    for logical_name, ref in (
        ("TRAINER_ROLE_BINDING", context.binding["trainer_role_binding_ref"]),
        ("TRAINING_CONTRACT", context.binding["training_contract_ref"]),
        ("SAMPLE_ORDER", context.binding["sample_order_ref"]),
        ("RUNTIME_ADAPTER", context.binding["runtime_adapter_ref"]),
    ):
        refs.append(
            {
                "logical_name": logical_name,
                "retention_class": "VALIDATED_SCIENTIFIC_ARTIFACT",
                "path": str(
                    (
                        context.package_root
                        / ref["path"]
                    ).resolve()
                ),
                "sha256": ref["sha256"],
                "schema_id": ref.get("schema_id"),
            }
        )
    for value in context.binding.get(
        "upstream_artifact_refs",
        [],
    ):
        if not isinstance(value, dict):
            raise ContractError("UPSTREAM_ARTIFACT_REF_INVALID")
        logical_name = value.get("logical_name")
        path_value = value.get("path")
        if not isinstance(logical_name, str) or not logical_name:
            raise ContractError("UPSTREAM_ARTIFACT_LOGICAL_NAME_INVALID")
        if not isinstance(path_value, str):
            raise ContractError("UPSTREAM_ARTIFACT_PATH_INVALID")
        path = Path(path_value).resolve()
        require_sha(
            path,
            value.get("sha256"),
            "UPSTREAM_ARTIFACT_" + logical_name,
        )
        normalized = dict(value)
        normalized["path"] = str(path)
        refs.append(normalized)

    direct_refs = adapter.input_artifact_refs(context)
    if not isinstance(direct_refs, list):
        raise ContractError("RUNTIME_ADAPTER_INPUT_REFS_INVALID")
    refs.extend(direct_refs)

    unique = {}
    ordered = []
    for value in refs:
        if not isinstance(value, dict):
            raise ContractError("INPUT_ARTIFACT_REF_INVALID")
        logical_name = value.get("logical_name")
        if not isinstance(logical_name, str) or not logical_name:
            raise ContractError("INPUT_ARTIFACT_LOGICAL_NAME_INVALID")
        previous = unique.get(logical_name)
        if previous is None:
            unique[logical_name] = value
            ordered.append(value)
            continue
        if (
            previous.get("path") != value.get("path")
            or previous.get("sha256") != value.get("sha256")
        ):
            raise ContractError(
                "INPUT_ARTIFACT_LOGICAL_NAME_CONFLICT:"
                + logical_name
            )
    return ordered


def run_training_stage(
    *,
    binding_path: Path,
    authorization_path: Path,
    runner_freeze_root_sha256: str,
) -> dict[str, Any]:
    if (
        not isinstance(runner_freeze_root_sha256, str)
        or len(runner_freeze_root_sha256) != 64
    ):
        raise ContractError("RUNNER_FREEZE_ROOT_SHA_INVALID")

    context = load_stage_context(binding_path)
    reject_ambient_environment(context)
    authorization = load_execution_authorization(
        authorization_path,
        context=context,
        runner_freeze_root_sha256=runner_freeze_root_sha256,
    )

    output_dir = Path(
        authorization["authorized_output_dir"]
    ).resolve()

    adapter = _load_runtime_adapter(context)
    adapter.validate_profile_without_model_load(context)
    input_refs = _input_refs(context, adapter)
    input_index = build_input_artifact_index(
        round_id=context.binding["round_id"],
        stage_id=context.binding["stage_id"],
        refs=input_refs,
    )

    attempt_root = create_attempt_root(
        Path(authorization["stage_attempt_root"])
    )
    write_attempt_json(
        attempt_root,
        "input_artifact_index.json",
        input_index,
    )

    started_receipt = build_stage_receipt(
        round_id=context.binding["round_id"],
        stage_id=context.binding["stage_id"],
        stage_attempt_id=authorization["execution_attempt_id"],
        input_artifact_index_sha256=input_index[
            "artifact_index_sha256"
        ],
        output_artifact_index_sha256=None,
        runner_freeze_root_sha256=runner_freeze_root_sha256,
        authorization_sha256=authorization["authorization_sha256"],
        started_from_receipt_sha256=None,
        previous_stage_receipt_sha256=context.binding.get(
            "previous_stage_receipt_sha256"
        ),
        terminal_status="STARTED",
        scientific_missingness_class=None,
        model_training_executed=False,
        model_training_execution_status="NOT_STARTED",
        failure_summary=None,
    )
    write_attempt_json(
        attempt_root,
        "started_stage_receipt.json",
        started_receipt,
    )

    try:
        result = adapter.execute_training_stage(
            context=context,
            output_dir=output_dir,
            runner_freeze_root_sha256=runner_freeze_root_sha256,
        )
        artifacts = result.get("artifacts")
        if not isinstance(artifacts, list):
            raise ContractError(
                "RUNTIME_ADAPTER_OUTPUT_ARTIFACTS_INVALID"
            )
        output_index = build_output_artifact_index(
            round_id=context.binding["round_id"],
            stage_id=context.binding["stage_id"],
            artifacts=artifacts,
        )
        write_attempt_json(
            attempt_root,
            "output_artifact_index.json",
            output_index,
        )
        terminal_receipt = build_stage_receipt(
            round_id=context.binding["round_id"],
            stage_id=context.binding["stage_id"],
            stage_attempt_id=authorization["execution_attempt_id"],
            input_artifact_index_sha256=input_index[
                "artifact_index_sha256"
            ],
            output_artifact_index_sha256=output_index[
                "artifact_index_sha256"
            ],
            runner_freeze_root_sha256=runner_freeze_root_sha256,
            authorization_sha256=authorization[
                "authorization_sha256"
            ],
            started_from_receipt_sha256=started_receipt[
                "stage_receipt_sha256"
            ],
            previous_stage_receipt_sha256=context.binding.get(
                "previous_stage_receipt_sha256"
            ),
            terminal_status="ACCEPTED",
            scientific_missingness_class=None,
            model_training_executed=True,
            model_training_execution_status="COMPLETED",
            failure_summary=None,
        )
        write_attempt_json(
            attempt_root,
            "terminal_stage_receipt.json",
            terminal_receipt,
        )
        return {
            "stage_receipt": terminal_receipt,
            "output_artifact_index": output_index,
            "run_manifest": result.get("run_manifest"),
        }
    except Exception as exc:
        failure = {
            "schema_id": "ROUND_TRAINING_STAGE_FAILURE_V1",
            "schema_version": 1,
            "round_id": context.binding["round_id"],
            "stage_id": context.binding["stage_id"],
            "stage_attempt_id": authorization[
                "execution_attempt_id"
            ],
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
        }
        write_json_create_once(
            attempt_root / "failure.json",
            failure,
        )
        terminal_receipt = build_stage_receipt(
            round_id=context.binding["round_id"],
            stage_id=context.binding["stage_id"],
            stage_attempt_id=authorization["execution_attempt_id"],
            input_artifact_index_sha256=input_index[
                "artifact_index_sha256"
            ],
            output_artifact_index_sha256=None,
            runner_freeze_root_sha256=runner_freeze_root_sha256,
            authorization_sha256=authorization[
                "authorization_sha256"
            ],
            started_from_receipt_sha256=started_receipt[
                "stage_receipt_sha256"
            ],
            previous_stage_receipt_sha256=context.binding.get(
                "previous_stage_receipt_sha256"
            ),
            terminal_status="INFRASTRUCTURE_OR_RUNTIME_FAILURE",
            scientific_missingness_class="UNRESOLVED_RUNTIME_FAILURE",
            model_training_executed=None,
            model_training_execution_status=(
                "AMBIGUOUS_AFTER_RUNTIME_ADAPTER_ENTRY"
            ),
            failure_summary=f"{type(exc).__name__}:{exc}",
        )
        write_attempt_json(
            attempt_root,
            "terminal_stage_receipt.json",
            terminal_receipt,
        )
        raise


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Execute a sealed round-local training stage through a "
            "registered runtime adapter."
        )
    )
    parser.add_argument(
        "--stage-binding",
        type=Path,
        required=True,
    )
    parser.add_argument(
        "--authorization",
        type=Path,
        required=True,
    )
    return parser


def main(argv=None) -> int:
    args = build_argument_parser().parse_args(argv)
    runner_freeze_root_sha256 = os.environ.get(
        RUNNER_FREEZE_ENV
    )
    if runner_freeze_root_sha256 is None:
        raise ContractError(f"{RUNNER_FREEZE_ENV}_REQUIRED")

    result = run_training_stage(
        binding_path=args.stage_binding,
        authorization_path=args.authorization,
        runner_freeze_root_sha256=runner_freeze_root_sha256,
    )
    receipt = result["stage_receipt"]
    print("ROUND_TRAINING_STAGE_COMPLETED")
    print(
        "stage_receipt_sha256="
        + receipt["stage_receipt_sha256"]
    )
    print(
        "output_artifact_index_sha256="
        + receipt["output_artifact_index_sha256"]
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
