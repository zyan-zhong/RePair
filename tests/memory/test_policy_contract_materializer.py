"""Synthetic tests for the frozen Round-1 policy identity materializer."""

from __future__ import annotations

import ast
import hashlib
from importlib import util
import json
import os
from pathlib import Path
import stat
import sys

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = (
    REPO_ROOT
    / "scripts/memory/materialize_primary_policy_contract_v1.py"
)
TASK_CONFIG_PATH = (
    REPO_ROOT
    / "configs/memory/task_access_regeneration_v1.json"
)
POLICY_CONFIG_PATH = (
    REPO_ROOT
    / "configs/memory/round1_policy_source_identity_v1.json"
)


def _materializer():
    assert SCRIPT_PATH.is_file(), "policy identity materializer script missing"
    name = "failure_memory_policy_identity_materializer_test_module"
    spec = util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode("utf-8")


def _write_json(path: Path, payload: object) -> bytes:
    data = _canonical_bytes(payload)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    return data



def _synthetic_a01_record(
    root: Path,
    root_seal: str,
) -> dict[str, object]:
    return {
        "absolute_path": str(root.resolve(strict=True)),
        "exists": True,
        "file_count": 23,
        "role": "training checkpoint archive",
        "slot_id": "A01_CHECKPOINTS",
        "total_bytes": 359767109,
        "tree_digest_sha256": root_seal,
    }


def _synthetic_tree(tmp_path: Path):
    root = tmp_path / "formal_runs"
    root.mkdir()

    root_seal = "f" * 64
    base_model_repository = "Qwen/Qwen2.5-3B-Instruct"
    base_model_revision = "a" * 40
    tokenizer_bundle_sha256 = "4" * 64
    runner_freeze_root_sha256 = "9" * 64
    training_config_freeze_root_sha256 = "8" * 64
    dataset_freeze_root_sha256 = "7" * 64
    materialization_freeze_root_sha256 = "6" * 64
    training_config_sha256 = "5" * 64

    sources = []
    checkpoint_entries = []
    file_sha256: dict[str, str] = {}

    for seed in (17, 31, 47):
        seed_dir = root / f"seed_{seed}"
        adapter_dir = seed_dir / "adapter"
        adapter_dir.mkdir(parents=True)

        member_payloads = {
            "README.md": f"synthetic adapter {seed}\n".encode("utf-8"),
            "adapter_config.json": _canonical_bytes(
                {
                    "schema": "SYNTHETIC_ADAPTER_CONFIG",
                    "seed": seed,
                }
            ),
            "adapter_model.safetensors": (
                f"SYNTHETIC-MODEL-{seed}".encode("utf-8")
            ),
        }
        member_records = {}
        for name, data in member_payloads.items():
            member_path = adapter_dir / name
            member_path.write_bytes(data)
            member_sha = hashlib.sha256(data).hexdigest()
            member_records[name] = {
                "sha256": member_sha,
                "size_bytes": len(data),
            }
            file_sha256[f"seed_{seed}/adapter/{name}"] = member_sha

        adapter_bundle_sha256 = hashlib.sha256(
            f"adapter-bundle-{seed}".encode("utf-8")
        ).hexdigest()

        adapter_payload = {
            "adapter_bundle_sha256": adapter_bundle_sha256,
            "files": member_records,
            "required_files": [
                "adapter_config.json",
                "adapter_model.safetensors",
            ],
            "schema_id": "SYNTHETIC_ADAPTER_ARTIFACT_MANIFEST_V1",
            "schema_version": 1,
        }
        adapter_bytes = _write_json(
            seed_dir / "adapter_artifact_manifest.json",
            adapter_payload,
        )
        adapter_manifest_sha = hashlib.sha256(adapter_bytes).hexdigest()
        file_sha256[
            f"seed_{seed}/adapter_artifact_manifest.json"
        ] = adapter_manifest_sha

        initial_sha = hashlib.sha256(
            f"initial-{seed}".encode("utf-8")
        ).hexdigest()
        final_sha = hashlib.sha256(
            f"final-{seed}".encode("utf-8")
        ).hexdigest()

        formal_payload = {
            "adapter_bundle_sha256": adapter_bundle_sha256,
            "base_model_repository": base_model_repository,
            "base_model_revision": base_model_revision,
            "condition_id": "P4-R1-Q2-BAD",
            "dataset_freeze_root_sha256": dataset_freeze_root_sha256,
            "final_trainable_parameter_sha256": final_sha,
            "formal_training_seed": seed,
            "initial_trainable_parameter_sha256": initial_sha,
            "intermediate_scientific_checkpoint_used": False,
            "materialization_freeze_root_sha256": materialization_freeze_root_sha256,
            "run_status": "FORMAL_TRAINING_COMPLETED",
            "runner_freeze_root_sha256": runner_freeze_root_sha256,
            "schema_id": "SYNTHETIC_FORMAL_RUN_MANIFEST_V1",
            "schema_version": 1,
            "scientific_checkpoint_rule": "FINAL_STEP_ONLY",
            "select_used_for_training_or_model_selection": False,
            "tokenizer_bundle_sha256": tokenizer_bundle_sha256,
            "training_config_freeze_root_sha256": training_config_freeze_root_sha256,
            "training_config_sha256": training_config_sha256,
        }
        formal_bytes = _write_json(
            seed_dir / "formal_run_manifest.json",
            formal_payload,
        )
        formal_sha = hashlib.sha256(formal_bytes).hexdigest()
        file_sha256[
            f"seed_{seed}/formal_run_manifest.json"
        ] = formal_sha

        training_ledger = f"synthetic-ledger-{seed}\n".encode("utf-8")
        ledger_path = seed_dir / "training_step_ledger.jsonl"
        ledger_path.write_bytes(training_ledger)
        ledger_sha = hashlib.sha256(training_ledger).hexdigest()
        file_sha256[
            f"seed_{seed}/training_step_ledger.jsonl"
        ] = ledger_sha

        sources.append(
            {
                "training_seed": seed,
                "formal_run_manifest_relative_path": (
                    f"seed_{seed}/formal_run_manifest.json"
                ),
                "formal_run_manifest_sha256": formal_sha,
                "adapter_artifact_manifest_relative_path": (
                    f"seed_{seed}/adapter_artifact_manifest.json"
                ),
                "adapter_artifact_manifest_sha256": adapter_manifest_sha,
            }
        )
        checkpoint_entries.append(
            {
                "adapter_artifact_manifest_sha256": adapter_manifest_sha,
                "adapter_bundle_sha256": adapter_bundle_sha256,
                "adapter_relative_path": f"seed_{seed}/adapter",
                "final_trainable_parameter_sha256": final_sha,
                "formal_run_manifest_sha256": formal_sha,
                "initial_trainable_parameter_sha256": initial_sha,
                "slurm_job_id": 100000 + seed,
                "training_seed": seed,
                "training_step_ledger_sha256": ledger_sha,
            }
        )

    provenance = root / "provenance"
    provenance.mkdir()

    runner_payload = {
        "condition_id": "P4-R1-Q2-BAD",
        "dataset_freeze_root_sha256": dataset_freeze_root_sha256,
        "formal_optimizer_steps_per_seed": 210,
        "formal_target_loss_tokens_per_seed": 9670,
        "formal_training_seeds": [17, 31, 47],
        "materialization_freeze_root_sha256": materialization_freeze_root_sha256,
        "runner_status": "FROZEN_READY_FOR_FORMAL_TRAINING",
        "schema_id": "SYNTHETIC_RUNNER_MANIFEST_V1",
        "schema_version": 1,
        "select_used_for_training_or_model_selection": False,
        "training_config_freeze_root_sha256": training_config_freeze_root_sha256,
        "training_config_sha256": training_config_sha256,
    }
    runner_bytes = _write_json(
        provenance / "runner_manifest.json",
        runner_payload,
    )
    runner_sha = hashlib.sha256(runner_bytes).hexdigest()
    file_sha256["provenance/runner_manifest.json"] = runner_sha

    execution_spec_bytes = _write_json(
        provenance / "execution_spec.json",
        {
            "schema_id": "SYNTHETIC_EXECUTION_SPEC_V1",
            "formal_training_seeds": [17, 31, 47],
        },
    )
    file_sha256[
        "provenance/execution_spec.json"
    ] = hashlib.sha256(
        execution_spec_bytes
    ).hexdigest()

    submission_ledger_bytes = (
        b'{"seed":17,"status":"SUBMITTED"}\n'
        b'{"seed":31,"status":"SUBMITTED"}\n'
        b'{"seed":47,"status":"SUBMITTED"}\n'
    )
    submission_ledger_path = (
        provenance
        / "formal_submission_ledger.jsonl"
    )
    submission_ledger_path.write_bytes(
        submission_ledger_bytes
    )
    file_sha256[
        "provenance/formal_submission_ledger.jsonl"
    ] = hashlib.sha256(
        submission_ledger_bytes
    ).hexdigest()

    checkpoint_set_payload = {
        "base_model_repository": base_model_repository,
        "base_model_revision": base_model_revision,
        "checkpoint_count": 3,
        "checkpoint_set_status": "FROZEN_READY_FOR_HARNESS_OFF_SELECT",
        "checkpoints": checkpoint_entries,
        "condition_id": "P4-R1-Q2-BAD",
        "dataset_freeze_root_sha256": dataset_freeze_root_sha256,
        "file_sha256": file_sha256,
        "formal_execution_spec_freeze_root_sha256": "3" * 64,
        "materialization_freeze_root_sha256": materialization_freeze_root_sha256,
        "policy_version": "pi1",
        "runner_freeze_root_sha256": runner_freeze_root_sha256,
        "schema_id": "SYNTHETIC_CHECKPOINT_SET_MANIFEST_V1",
        "schema_version": 1,
        "scientific_checkpoint_rule": "FINAL_STEP_ONLY",
        "secondary_mix_arm_status": "NOT_APPLICABLE",
        "select_aggregation_rule": "ALL_THREE",
        "select_execution_status": "READY",
        "teacher_or_runtime_harness_in_select": False,
        "training_config_freeze_root_sha256": training_config_freeze_root_sha256,
        "training_seed_schedule": [17, 31, 47],
        "training_seed_selection": "ALL_THREE_REQUIRED_NO_BEST_SEED_SELECTION",
    }
    _write_json(
        root / "checkpoint_set_manifest.json",
        checkpoint_set_payload,
    )

    config = {
        "schema": "ROUND1_POLICY_SOURCE_IDENTITY_V1",
        "historical_authority_id": "A01_CHECKPOINTS",
        "historical_identity_kind": "ROOT_SEAL",
        "checkpoint_set_root_seal": root_seal,
        "selection_rule": (
            "MINIMUM_POLICY_TRAINING_SEED_FROM_FROZEN_ROUND1_CHECKPOINT_SET"
        ),
        "primary_training_seed": 17,
        "secondary_training_seeds": [31, 47],
        "source_record_effect_policy": "ORIGINAL_SOURCE_CHECKPOINT",
        "secondary_audit_condition": (
            "FM0_NO_PERSISTENT_MEMORY_VS_FM3_GATED_PRESCRIPTIVE_MEMORY"
        ),
        "no_best_of_checkpoint": True,
        "all_secondary_results_reported": True,
        "policy_sources": sources,
    }
    config_path = tmp_path / "policy_config.json"
    _write_json(config_path, config)

    authority_path = tmp_path / "root_seals.json"
    _write_json(
        authority_path,
        [_synthetic_a01_record(root, root_seal)],
    )

    return root, config_path, authority_path, config

def _run(
    module,
    tmp_path: Path,
    *,
    root: Path,
    config_path: Path,
    authority_path: Path,
    name: str = "contract.json",
):
    output = tmp_path / name
    report = module.materialize_primary_policy_contract(
        source_root=root,
        root_seal_authority_path=authority_path,
        config_path=config_path,
        output_path=output,
    )
    return output, report


def test_materializer_writes_deterministic_contract_with_train17_primary(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)

    output, report = _run(
        module,
        tmp_path,
        root=root,
        config_path=config_path,
        authority_path=authority_path,
    )

    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["primary_training_seed"] == 17
    assert payload["secondary_training_seeds"] == [31, 47]
    assert payload["source_record_effect_policy"] == "ORIGINAL_SOURCE_CHECKPOINT"
    assert payload["no_best_of_checkpoint"] is True
    assert payload["all_secondary_results_reported"] is True
    assert report["primary_training_seed"] == 17
    assert report["secondary_training_seeds"] == [31, 47]
    assert report["source_count"] == 3
    assert report["contract_sha256"] == hashlib.sha256(output.read_bytes()).hexdigest()


def test_materializer_is_deterministic_across_distinct_outputs(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)

    first, _ = _run(
        module,
        tmp_path,
        root=root,
        config_path=config_path,
        authority_path=authority_path,
        name="first.json",
    )
    second, _ = _run(
        module,
        tmp_path,
        root=root,
        config_path=config_path,
        authority_path=authority_path,
        name="second.json",
    )
    assert first.read_bytes() == second.read_bytes()


def test_materializer_refuses_existing_output(tmp_path: Path) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    output = tmp_path / "contract.json"
    output.write_text("sentinel", encoding="utf-8")

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="OUTPUT_ALREADY_EXISTS",
    ):
        module.materialize_primary_policy_contract(
            source_root=root,
            root_seal_authority_path=authority_path,
            config_path=config_path,
            output_path=output,
        )
    assert output.read_text(encoding="utf-8") == "sentinel"


@pytest.mark.parametrize("seed", [17, 31, 47])
def test_materializer_rejects_missing_formal_run_manifest(
    tmp_path: Path,
    seed: int,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    (root / f"seed_{seed}/formal_run_manifest.json").unlink()

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match=f"FORMAL_RUN_SEED_{seed}_MISSING",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_materializer_rejects_wrong_formal_run_sha(tmp_path: Path) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    path = root / "seed_17/formal_run_manifest.json"
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="FORMAL_RUN_SHA256_MISMATCH_SEED_17",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


@pytest.mark.parametrize("seed", [17, 31, 47])
def test_materializer_rejects_missing_adapter_manifest(
    tmp_path: Path,
    seed: int,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    (root / f"seed_{seed}/adapter_artifact_manifest.json").unlink()

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match=f"ADAPTER_MANIFEST_SEED_{seed}_MISSING",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_materializer_rejects_wrong_adapter_manifest_sha(tmp_path: Path) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    path = root / "seed_31/adapter_artifact_manifest.json"
    path.write_bytes(path.read_bytes() + b" ")

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="ADAPTER_MANIFEST_SHA256_MISMATCH_SEED_31",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )



def test_materializer_rejects_formal_adapter_linkage_mismatch(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)

    formal_path = root / "seed_47/formal_run_manifest.json"
    payload = json.loads(
        formal_path.read_text(encoding="utf-8")
    )
    payload["adapter_bundle_sha256"] = "0" * 64
    formal_bytes = _write_json(formal_path, payload)

    config = json.loads(
        config_path.read_text(encoding="utf-8")
    )
    changed_sha = hashlib.sha256(formal_bytes).hexdigest()
    for entry in config["policy_sources"]:
        if entry["training_seed"] == 47:
            entry["formal_run_manifest_sha256"] = changed_sha
    _write_json(config_path, config)

    checkpoint_path = root / "checkpoint_set_manifest.json"
    checkpoint = json.loads(
        checkpoint_path.read_text(encoding="utf-8")
    )
    checkpoint["file_sha256"][
        "seed_47/formal_run_manifest.json"
    ] = changed_sha
    for entry in checkpoint["checkpoints"]:
        if entry["training_seed"] == 47:
            entry["formal_run_manifest_sha256"] = changed_sha
    _write_json(checkpoint_path, checkpoint)

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="FORMAL_ADAPTER_BUNDLE_MISMATCH_SEED_47",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )

def test_policy_config_rejects_duplicate_training_seed(tmp_path: Path) -> None:
    module = _materializer()
    _, config_path, _, config = _synthetic_tree(tmp_path)
    config["policy_sources"][1]["training_seed"] = 17
    _write_json(config_path, config)

    with pytest.raises(
        (module.PolicyIdentityMaterializationError, ValueError),
    ):
        module.load_policy_source_config(config_path)


def test_policy_config_rejects_missing_training_seed(tmp_path: Path) -> None:
    module = _materializer()
    _, config_path, _, config = _synthetic_tree(tmp_path)
    config["policy_sources"] = config["policy_sources"][:-1]
    _write_json(config_path, config)

    with pytest.raises(
        (module.PolicyIdentityMaterializationError, ValueError),
    ):
        module.load_policy_source_config(config_path)


def test_policy_config_rejects_extra_training_seed(tmp_path: Path) -> None:
    module = _materializer()
    _, config_path, _, config = _synthetic_tree(tmp_path)
    extra = dict(config["policy_sources"][-1])
    extra["training_seed"] = 53
    config["policy_sources"].append(extra)
    _write_json(config_path, config)

    with pytest.raises(
        (module.PolicyIdentityMaterializationError, ValueError),
    ):
        module.load_policy_source_config(config_path)


def test_policy_config_rejects_result_or_performance_fields(
    tmp_path: Path,
) -> None:
    module = _materializer()
    _, config_path, _, config = _synthetic_tree(tmp_path)
    config["result_metrics"] = {"17": 1.0}
    _write_json(config_path, config)

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
    ):
        module.load_policy_source_config(config_path)


def test_policy_config_rejects_unsafe_member_path(tmp_path: Path) -> None:
    module = _materializer()
    _, config_path, _, config = _synthetic_tree(tmp_path)
    config["policy_sources"][0][
        "formal_run_manifest_relative_path"
    ] = "../outside/formal_run_manifest.json"
    _write_json(config_path, config)

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
    ):
        module.load_policy_source_config(config_path)



def test_root_seal_authority_record_is_required(tmp_path: Path) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    _write_json(authority_path, [])

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="ROOT_SEAL_AUTHORITY_RECORD_MISSING",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_root_seal_authority_record_must_be_unambiguous(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    record = _synthetic_a01_record(root, "f" * 64)
    _write_json(
        authority_path,
        [record, dict(record)],
    )

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="ROOT_SEAL_AUTHORITY_RECORD_AMBIGUOUS",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_wrong_historical_root_seal_is_rejected(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    record = _synthetic_a01_record(root, "0" * 64)
    _write_json(authority_path, [record])

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="ROOT_SEAL_AUTHORITY_VALUE_MISMATCH",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )

@pytest.mark.parametrize(
    "member",
    [
        "seed_17/formal_run_manifest.json",
        "seed_31/adapter_artifact_manifest.json",
    ],
)
def test_member_symlink_is_rejected(
    tmp_path: Path,
    member: str,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    path = root / member
    target = tmp_path / "outside.json"
    target.write_bytes(path.read_bytes())
    path.unlink()
    path.symlink_to(target)

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="SYMLINK_FORBIDDEN",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_source_root_symlink_is_rejected(tmp_path: Path) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    link = tmp_path / "linked_root"
    link.symlink_to(root, target_is_directory=True)

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="SOURCE_ROOT_SYMLINK_FORBIDDEN",
    ):
        _run(
            module,
            tmp_path,
            root=link,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_root_seal_authority_symlink_is_rejected(tmp_path: Path) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    link = tmp_path / "linked_authority.json"
    link.symlink_to(authority_path)

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="ROOT_SEAL_AUTHORITY_SYMLINK_FORBIDDEN",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=link,
        )


def test_output_uses_restrictive_permissions_on_posix(tmp_path: Path) -> None:
    if os.name != "posix":
        pytest.skip("POSIX permission assertion")
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    output, _ = _run(
        module,
        tmp_path,
        root=root,
        config_path=config_path,
        authority_path=authority_path,
    )
    assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_materializer_does_not_scan_result_files(tmp_path: Path) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    poison = root / "memory_results.json"
    poison.write_text(
        '{"best_seed":47,"performance":999}',
        encoding="utf-8",
    )
    poison.chmod(0)

    output, _ = _run(
        module,
        tmp_path,
        root=root,
        config_path=config_path,
        authority_path=authority_path,
    )
    assert output.is_file()


def test_materializer_source_has_no_model_environment_or_tree_hash_runtime() -> None:
    _materializer()
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)

    forbidden_import_roots = {
        "alfworld",
        "torch",
        "vllm",
        "openai",
        "anthropic",
        "google",
    }
    forbidden_calls = {
        "walk",
        "rglob",
        "glob",
    }

    violations = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".", 1)[0] in forbidden_import_roots:
                    violations.append(("import", alias.name))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".", 1)[0] in forbidden_import_roots:
                violations.append(("from", module))
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if node.func.attr in forbidden_calls:
                    violations.append(("call", node.func.attr))
    assert violations == []


def test_task_access_config_is_exact_canonical_authority() -> None:
    assert TASK_CONFIG_PATH.is_file(), "task-access config missing"
    raw = TASK_CONFIG_PATH.read_bytes()
    payload = json.loads(raw)
    assert payload == {
        "access_policy_id": "MEMORY_TASK_ACCESS_V2_1",
        "approved_design_commit": "b3cb816e2e727600f79f1947a77c73ce87d4a97c",
        "approved_v2_1_manifest_sha256": (
            "6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a"
        ),
        "disclosure_policy_id": "HELDOUT_IDENTITY_DISCLOSURE_POLICY_V1",
        "expected_populations": {
            "TRAIN_MEMORY_SOURCE": 2367,
            "TRAIN_RETRIEVAL_DEV": 1186,
            "VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED": 140,
            "VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED": 134,
        },
        "schema": "TASK_ACCESS_REGENERATION_CONFIG_V1",
    }
    assert raw == _canonical_bytes(payload)


def test_policy_source_config_is_exact_registered_round1_authority() -> None:
    assert POLICY_CONFIG_PATH.is_file(), "policy source config missing"
    raw = POLICY_CONFIG_PATH.read_bytes()
    payload = json.loads(raw)
    assert raw == _canonical_bytes(payload)
    assert payload["checkpoint_set_root_seal"] == (
        "6dd3ad3389869d6f929af24283589f2e22f4c687a800072af16bb6f23b5092f8"
    )
    assert payload["historical_authority_id"] == "A01_CHECKPOINTS"
    assert payload["historical_identity_kind"] == "ROOT_SEAL"
    assert payload["primary_training_seed"] == 17
    assert payload["secondary_training_seeds"] == [31, 47]
    assert [entry["training_seed"] for entry in payload["policy_sources"]] == [
        17,
        31,
        47,
    ]
    module = _materializer()
    loaded = module.load_policy_source_config(POLICY_CONFIG_PATH)
    assert tuple(entry.training_seed for entry in loaded.policy_sources) == (
        17,
        31,
        47,
    )
    expected = {
        17: (
            "ce44dd66ccf675da5d73fe9ac6b6273799df51e90b72bd92398ef521f1d103e6",
            "cfcff4c187429f5f9a82b55a47bb3ce4a9123e224a541fdfefa45ed09e9073a7",
        ),
        31: (
            "8b14bab7bf9d0396600c0d9bb5fc60340d0bd9336323dd9a3ad4047e76e8bd83",
            "ca06e6807803d82ed803e0ecdbc5b018bb1fdd85a8347f3b05a821cbb117170d",
        ),
        47: (
            "57db3c1dd720d758a21150389df840343cfec53a473b1b59b984303dd43eeb78",
            "b491aec5dc1f65a3b8f2083e605241473b171aa351c07ccf8d252bfaed206159",
        ),
    }
    for entry in payload["policy_sources"]:
        assert (
            entry["formal_run_manifest_sha256"],
            entry["adapter_artifact_manifest_sha256"],
        ) == expected[entry["training_seed"]]




def test_task_access_v2_config_is_accepted_by_existing_task_materializer() -> None:
    task_config_v2_path = (
        REPO_ROOT
        / "configs/memory/task_access_regeneration_v2.json"
    )
    assert task_config_v2_path.is_file(), "task-access V2 config missing"

    task_script = REPO_ROOT / "scripts/memory/materialize_task_access_v1.py"
    assert task_script.is_file()

    name = "failure_memory_task_access_materializer_config_compat_test"
    spec = util.spec_from_file_location(name, task_script)
    assert spec is not None
    assert spec.loader is not None

    module = util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)

    authority = module.load_real_authority_config(
        task_config_v2_path
    )

    assert authority.original_failure_memory_design_commit == (
        "b3cb816e2e727600f79f1947a77c73ce87d4a97c"
    )
    assert authority.sha_authority_correction_design_commit == (
        "08aa577a299012aa59b03d75a4a0654ae0d74d69"
    )
    assert authority.historical_design_candidate_sha256 == (
        "6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a"
    )
    assert authority.approved_exact_contract_protected_sha256 == (
        "260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea"
    )


def test_policy_source_config_contains_no_observed_memory_outcomes() -> None:
    payload = json.loads(POLICY_CONFIG_PATH.read_bytes())
    flattened = json.dumps(payload, sort_keys=True).lower()
    for forbidden in (
        "memory_result",
        "performance",
        "reward",
        "success_rate",
        "best_seed",
        "best_checkpoint",
    ):
        assert forbidden not in flattened


def test_review_hardening_real_schema_policy_materialization_succeeds(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    output, report = _run(
        module,
        tmp_path,
        root=root,
        config_path=config_path,
        authority_path=authority_path,
    )
    assert output.is_file()
    assert report["primary_training_seed"] == 17
    assert report["source_count"] == 3
    assert report["tokenizer_bundle_sha256"] == "4" * 64


def test_review_hardening_exact_a01_field_binding_rejects_unrelated_hash(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    record = _synthetic_a01_record(root, "0" * 64)
    record["unrelated_note"] = "f" * 64
    _write_json(authority_path, [record])

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match=(
            "ROOT_SEAL_AUTHORITY_SCHEMA_INVALID"
            "|ROOT_SEAL_AUTHORITY_VALUE_MISMATCH"
        ),
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_review_hardening_policy_output_cannot_write_into_source_root(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    output = root / "forbidden_contract.json"

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="OUTPUT_INSIDE_SOURCE_ROOT",
    ):
        module.materialize_primary_policy_contract(
            source_root=root,
            root_seal_authority_path=authority_path,
            config_path=config_path,
            output_path=output,
        )

    assert not output.exists()


def test_review_hardening_adapter_member_bytes_are_verified(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    member = root / "seed_31/adapter/adapter_model.safetensors"
    member.write_bytes(member.read_bytes() + b"CORRUPTION")

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="ADAPTER_MEMBER_SHA256_MISMATCH_SEED_31",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_review_hardening_checkpoint_set_manifest_binds_registered_manifests(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    path = root / "checkpoint_set_manifest.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["checkpoints"][0][
        "adapter_artifact_manifest_sha256"
    ] = "0" * 64
    _write_json(path, payload)

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match=(
            "CHECKPOINT_SET_ADAPTER_MANIFEST_SHA256_MISMATCH_SEED_17"
        ),
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_review_hardening_runner_manifest_bytes_are_verified(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    runner = root / "provenance/runner_manifest.json"
    runner.write_bytes(runner.read_bytes() + b" ")

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match="RUNNER_MANIFEST_SHA256_MISMATCH",
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )



def test_final_member_coverage_execution_spec_is_verified(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    target = root / "provenance/execution_spec.json"
    target.write_bytes(
        target.read_bytes()
        + b"CORRUPTION"
    )

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match=(
            "REGISTERED_MEMBER_SHA256_MISMATCH_"
            "PROVENANCE_EXECUTION_SPEC_JSON"
        ),
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )


def test_final_member_coverage_submission_ledger_is_verified(
    tmp_path: Path,
) -> None:
    module = _materializer()
    root, config_path, authority_path, _ = _synthetic_tree(tmp_path)
    target = (
        root
        / "provenance/formal_submission_ledger.jsonl"
    )
    target.write_bytes(
        target.read_bytes()
        + b"CORRUPTION"
    )

    with pytest.raises(
        module.PolicyIdentityMaterializationError,
        match=(
            "REGISTERED_MEMBER_SHA256_MISMATCH_"
            "PROVENANCE_FORMAL_SUBMISSION_LEDGER_JSONL"
        ),
    ):
        _run(
            module,
            tmp_path,
            root=root,
            config_path=config_path,
            authority_path=authority_path,
        )
