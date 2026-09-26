from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback

from smoke.common import (
    SmokeError,
    domain_sha256,
    load_json_object,
    require_domain_sha,
    require_sha,
    sha256_file,
    write_json_create_once,
)


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
REVIEW_MANIFEST_PATH = (
    PACKAGE_ROOT
    / "authorities/"
    "ROUND_GENERIC_TRAINING_STAGE_V2_1_REVIEW_MANIFEST.json"
)
BINDING_PATH = (
    PACKAGE_ROOT
    / "authorities/"
    "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_BINDING_V1.json"
)
AUTHORIZATION_PATH = (
    PACKAGE_ROOT
    / "authorities/"
    "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_AUTHORIZATION_V1.json"
)


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise SmokeError(f"MODULE_IMPORT_SPEC_FAILED:{path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _find_review_file_sha(review: dict, suffix: str) -> str:
    matches = [
        row["sha256"]
        for row in review.get("files", [])
        if isinstance(row, dict)
        and isinstance(row.get("path"), str)
        and row["path"].endswith(suffix)
    ]
    if len(matches) != 1:
        raise SmokeError(
            f"REVIEW_FILE_SUFFIX_NOT_EXACTLY_ONE:{suffix}:{len(matches)}"
        )
    return matches[0]


def verify_reviewed_fixed_head() -> tuple[dict, dict]:
    review = load_json_object(REVIEW_MANIFEST_PATH)
    binding = load_json_object(BINDING_PATH)
    require_domain_sha(
        binding,
        schema_id=(
            "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_BINDING_V1"
        ),
        sha_field="smoke_binding_sha256",
    )

    reviewed_root = Path(
        binding["reviewed_training_stage_root"]
    ).resolve()
    if not reviewed_root.is_dir():
        raise SmokeError(
            f"REVIEWED_TRAINING_STAGE_ROOT_MISSING:{reviewed_root}"
        )

    for row in review.get("files", []):
        if not isinstance(row, dict):
            raise SmokeError("REVIEW_FILE_ROW_INVALID")
        relative = row.get("path")
        if not isinstance(relative, str):
            raise SmokeError("REVIEW_FILE_PATH_INVALID")
        path = reviewed_root / relative
        require_sha(
            path,
            row.get("sha256"),
            "REVIEWED_FILE_" + relative.replace("/", "_"),
        )
        if path.stat().st_size != row.get("size"):
            raise SmokeError(
                f"REVIEWED_FILE_SIZE_MISMATCH:{relative}"
            )

    stage_binding_path = Path(
        binding["training_stage_binding_path"]
    )
    require_sha(
        stage_binding_path,
        binding["training_stage_binding_file_sha256"],
        "TRAINING_STAGE_BINDING",
    )
    stage_binding = load_json_object(stage_binding_path)
    if stage_binding.get("stage_binding_sha256") != (
        binding["training_stage_binding_domain_sha256"]
    ):
        raise SmokeError("TRAINING_STAGE_BINDING_DOMAIN_SHA_MISMATCH")

    freeze_payload = {
        "files": review["files"],
        "stage_binding_sha256": (
            binding["training_stage_binding_domain_sha256"]
        ),
        "training_contract_file_sha256": _find_review_file_sha(
            review,
            "ROUND_LOCAL_TRAINING_CONTRACT_V1.json",
        ),
        "sample_order_file_sha256": _find_review_file_sha(
            review,
            "ROUND_SAMPLE_ORDER_MANIFEST_V1.json",
        ),
        "runtime_adapter_sha256": _find_review_file_sha(
            review,
            "frozen_formal_train_peft.py",
        ),
    }
    observed_freeze = hashlib.sha256(
        json.dumps(
            freeze_payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()
    expected_freeze = binding[
        "reviewed_training_stage_freeze_root_sha256"
    ]
    if observed_freeze != expected_freeze:
        raise SmokeError(
            f"REVIEWED_FREEZE_ROOT_MISMATCH:"
            f"{observed_freeze}:{expected_freeze}"
        )
    if review.get("runner_freeze_root_sha256") != expected_freeze:
        raise SmokeError("REVIEW_MANIFEST_FREEZE_ROOT_MISMATCH")
    if review.get("training_execution_authorized") is not False:
        raise SmokeError("REVIEW_UNEXPECTEDLY_AUTHORIZES_TRAINING")
    if review.get("training_execution_count") != 0:
        raise SmokeError("REVIEW_TRAINING_COUNT_NOT_ZERO")
    if review.get("model_load_count") != 0:
        raise SmokeError("REVIEW_MODEL_LOAD_COUNT_NOT_ZERO")

    return review, binding


def verify_authorization(binding: dict) -> dict:
    value = load_json_object(AUTHORIZATION_PATH)
    require_domain_sha(
        value,
        schema_id=(
            "ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_"
            "AUTHORIZATION_V1"
        ),
        sha_field="authorization_sha256",
    )
    expected = {
        "authorization_status": "APPROVED",
        "authorization_scope": (
            "MODEL_LOAD_ONLY_NO_FORWARD_NO_BACKWARD_NO_OPTIMIZER"
        ),
        "round_id": binding["round_id"],
        "profile_id": binding["profile_id"],
        "stage_id": binding["stage_id"],
        "reviewed_training_stage_freeze_root_sha256": (
            binding["reviewed_training_stage_freeze_root_sha256"]
        ),
        "training_stage_binding_file_sha256": (
            binding["training_stage_binding_file_sha256"]
        ),
        "training_stage_binding_domain_sha256": (
            binding["training_stage_binding_domain_sha256"]
        ),
        "execution_attempt_id": binding["attempt_id"],
        "attempt_root": binding["attempt_root"],
        "result_root": binding["result_root"],
        "authorized_model_load_count": 1,
        "authorized_forward_count": 0,
        "authorized_backward_count": 0,
        "authorized_optimizer_construction_count": 0,
        "authorized_optimizer_step_count": 0,
        "authorized_training_execution_count": 0,
        "diagnostic_only": True,
        "promotion_eligible": False,
    }
    observed = {key: value.get(key) for key in expected}
    if observed != expected:
        raise SmokeError(
            "SMOKE_AUTHORIZATION_MISMATCH:"
            + repr(observed)
            + ":"
            + repr(expected)
        )
    return value


def run_smoke() -> dict:
    review, binding = verify_reviewed_fixed_head()
    authorization = verify_authorization(binding)

    reviewed_root = Path(
        binding["reviewed_training_stage_root"]
    ).resolve()
    reviewed_root_text = str(reviewed_root)
    if reviewed_root_text not in sys.path:
        sys.path.insert(0, reviewed_root_text)

    from round_training.contracts import load_stage_context
    from round_training.receipts import (
        build_input_artifact_index,
        build_output_artifact_index,
        build_stage_receipt,
    )

    context = load_stage_context(
        Path(binding["training_stage_binding_path"])
    )

    smoke_adapter_path = (
        PACKAGE_ROOT
        / binding["smoke_runtime_adapter_ref"]["path"]
    ).resolve()
    require_sha(
        smoke_adapter_path,
        binding["smoke_runtime_adapter_ref"]["sha256"],
        "SMOKE_RUNTIME_ADAPTER",
    )
    smoke_adapter = _load_module(
        smoke_adapter_path,
        "model_init_smoke_adapter",
    )

    attempt_root = Path(binding["attempt_root"]).resolve()
    result_root = Path(binding["result_root"]).resolve()
    if attempt_root.exists():
        raise SmokeError(
            f"SMOKE_ATTEMPT_ROOT_ALREADY_EXISTS:{attempt_root}"
        )
    if result_root.exists():
        raise SmokeError(
            f"SMOKE_RESULT_ROOT_ALREADY_EXISTS:{result_root}"
        )

    # Complete all non-model preflight before creating the attempt root.
    reviewed_adapter = _load_module(
        context.runtime_adapter_path,
        "reviewed_runtime_adapter_preflight",
    )
    reviewed_adapter.validate_profile_without_model_load(context)

    input_refs = [
        {
            "logical_name": "V2_1_REVIEW_MANIFEST",
            "retention_class": "VALIDATED_SCIENTIFIC_ARTIFACT",
            "path": str(REVIEW_MANIFEST_PATH.resolve()),
            "sha256": sha256_file(REVIEW_MANIFEST_PATH),
            "schema_id": review["schema_id"],
        },
        {
            "logical_name": "MODEL_INIT_SMOKE_BINDING",
            "retention_class": "DECISION_ARTIFACT",
            "path": str(BINDING_PATH.resolve()),
            "sha256": sha256_file(BINDING_PATH),
            "schema_id": binding["schema_id"],
        },
        {
            "logical_name": "MODEL_INIT_SMOKE_AUTHORIZATION",
            "retention_class": "DECISION_ARTIFACT",
            "path": str(AUTHORIZATION_PATH.resolve()),
            "sha256": sha256_file(AUTHORIZATION_PATH),
            "schema_id": authorization["schema_id"],
        },
        {
            "logical_name": "TRAINING_STAGE_BINDING",
            "retention_class": "VALIDATED_SCIENTIFIC_ARTIFACT",
            "path": binding["training_stage_binding_path"],
            "sha256": binding[
                "training_stage_binding_file_sha256"
            ],
            "schema_id": "ROUND_TRAINING_STAGE_BINDING_V1",
        },
    ]
    direct_refs = reviewed_adapter.input_artifact_refs(context)
    input_refs.extend(direct_refs)
    input_index = build_input_artifact_index(
        round_id=binding["round_id"],
        stage_id=binding["stage_id"],
        refs=input_refs,
    )

    attempt_root.mkdir(parents=True, exist_ok=False)
    write_json_create_once(
        attempt_root / "input_artifact_index.json",
        input_index,
    )
    started = build_stage_receipt(
        round_id=binding["round_id"],
        stage_id=binding["stage_id"],
        stage_attempt_id=binding["attempt_id"],
        input_artifact_index_sha256=input_index[
            "artifact_index_sha256"
        ],
        output_artifact_index_sha256=None,
        runner_freeze_root_sha256=binding[
            "reviewed_training_stage_freeze_root_sha256"
        ],
        authorization_sha256=authorization[
            "authorization_sha256"
        ],
        started_from_receipt_sha256=None,
        previous_stage_receipt_sha256=None,
        terminal_status="STARTED",
        scientific_missingness_class=None,
        model_training_executed=False,
        model_training_execution_status="NOT_EXECUTED",
        failure_summary=None,
    )
    write_json_create_once(
        attempt_root / "started_stage_receipt.json",
        started,
    )

    try:
        result_root.mkdir(parents=False, exist_ok=False)
        result = smoke_adapter.execute_model_initialization_smoke(
            reviewed_root=reviewed_root,
            training_stage_binding_path=Path(
                binding["training_stage_binding_path"]
            ),
        )
        result["reviewed_training_stage_freeze_root_sha256"] = (
            binding["reviewed_training_stage_freeze_root_sha256"]
        )
        result["smoke_binding_sha256"] = binding[
            "smoke_binding_sha256"
        ]
        result["authorization_sha256"] = authorization[
            "authorization_sha256"
        ]
        result["result_sha256"] = domain_sha256(
            result["schema_id"],
            result,
            sha_field="result_sha256",
        )
        result_path = result_root / "smoke_result.json"
        write_json_create_once(result_path, result)

        output_index = build_output_artifact_index(
            round_id=binding["round_id"],
            stage_id=binding["stage_id"],
            artifacts=[
                {
                    "logical_name": "MODEL_INIT_SMOKE_RESULT",
                    "retention_class": (
                        "VALIDATED_SCIENTIFIC_ARTIFACT"
                    ),
                    "path": str(result_path),
                    "sha256": sha256_file(result_path),
                    "size_bytes": result_path.stat().st_size,
                    "schema_id": result["schema_id"],
                }
            ],
        )
        write_json_create_once(
            attempt_root / "output_artifact_index.json",
            output_index,
        )
        terminal = build_stage_receipt(
            round_id=binding["round_id"],
            stage_id=binding["stage_id"],
            stage_attempt_id=binding["attempt_id"],
            input_artifact_index_sha256=input_index[
                "artifact_index_sha256"
            ],
            output_artifact_index_sha256=output_index[
                "artifact_index_sha256"
            ],
            runner_freeze_root_sha256=binding[
                "reviewed_training_stage_freeze_root_sha256"
            ],
            authorization_sha256=authorization[
                "authorization_sha256"
            ],
            started_from_receipt_sha256=started[
                "stage_receipt_sha256"
            ],
            previous_stage_receipt_sha256=None,
            terminal_status="ACCEPTED",
            scientific_missingness_class=None,
            model_training_executed=False,
            model_training_execution_status="NOT_EXECUTED",
            failure_summary=None,
        )
        write_json_create_once(
            attempt_root / "terminal_stage_receipt.json",
            terminal,
        )
        return {
            "result": result,
            "terminal_receipt": terminal,
        }
    except Exception as exc:
        failure = {
            "schema_id": (
                "ROUND_TRAINING_MODEL_INITIALIZATION_"
                "SMOKE_FAILURE_V1"
            ),
            "schema_version": 1,
            "round_id": binding["round_id"],
            "profile_id": binding["profile_id"],
            "stage_id": binding["stage_id"],
            "attempt_id": binding["attempt_id"],
            "exception_type": type(exc).__name__,
            "exception_message": str(exc),
            "traceback": traceback.format_exc(),
            "forward_count": 0,
            "backward_count": 0,
            "optimizer_constructed": False,
            "optimizer_step_count": 0,
            "training_execution_count": 0,
        }
        write_json_create_once(
            attempt_root / "failure.json",
            failure,
        )
        terminal = build_stage_receipt(
            round_id=binding["round_id"],
            stage_id=binding["stage_id"],
            stage_attempt_id=binding["attempt_id"],
            input_artifact_index_sha256=input_index[
                "artifact_index_sha256"
            ],
            output_artifact_index_sha256=None,
            runner_freeze_root_sha256=binding[
                "reviewed_training_stage_freeze_root_sha256"
            ],
            authorization_sha256=authorization[
                "authorization_sha256"
            ],
            started_from_receipt_sha256=started[
                "stage_receipt_sha256"
            ],
            previous_stage_receipt_sha256=None,
            terminal_status="INFRASTRUCTURE_OR_MODEL_LOAD_FAILURE",
            scientific_missingness_class=(
                "MODEL_INITIALIZATION_SMOKE_FAILURE"
            ),
            model_training_executed=False,
            model_training_execution_status="NOT_EXECUTED",
            failure_summary=f"{type(exc).__name__}:{exc}",
        )
        write_json_create_once(
            attempt_root / "terminal_stage_receipt.json",
            terminal,
        )
        raise


def main() -> int:
    outcome = run_smoke()
    result = outcome["result"]
    receipt = outcome["terminal_receipt"]
    print("ROUND_TRAINING_MODEL_INITIALIZATION_SMOKE_PASS")
    print(
        "observed_initial_trainable_parameter_sha256="
        + result["observed_initial_trainable_parameter_sha256"]
    )
    print(
        "terminal_stage_receipt_sha256="
        + receipt["stage_receipt_sha256"]
    )
    print("MODEL_LOAD_COUNT=1")
    print("FORWARD_COUNT=0")
    print("BACKWARD_COUNT=0")
    print("OPTIMIZER_STEP_COUNT=0")
    print("TRAINING_EXECUTION_COUNT=0")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
