from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from stage0.live_runner import (
    _bound_cell_fields,
    _execution_identity,
    _wire_value,
)
from stage0.constants import E1_DESIGN_MERGE_COMMIT
from stage0.preflight import (
    audit_materialized_readiness_authority,
)
from stage0.runtime_server import build_vllm_command


def _server_manifest(registry: list[dict]) -> dict:
    return {
        "dtype": "bfloat16",
        "tensor_parallel_size": 1,
        "generation_config_mode": "vllm",
        "chat_template_content_format": "string",
        "max_lora_rank": 16,
        "max_loras": 1,
        "max_cpu_loras": 2,
        "lora_dtype": "auto",
        "static_lora_registry": registry,
    }


def test_vllm_command_is_registry_order_independent() -> None:
    candidate = {
        "served_model_name": "P4-R2-HUMAN-T2-DIAGNOSTIC-TRAIN17",
        "adapter_path": "/candidate",
    }
    parent = {
        "served_model_name": "P4-R1-Q2-BAD-TRAIN17",
        "adapter_path": "/parent",
    }

    command = build_vllm_command(
        server_manifest=_server_manifest([candidate, parent]),
        base_model_path="/model",
        host="127.0.0.1",
        port=18000,
    )

    marker = command.index("--lora-modules")
    assert command[marker + 1:] == [
        "P4-R1-Q2-BAD-TRAIN17=/parent",
        "P4-R2-HUMAN-T2-DIAGNOSTIC-TRAIN17=/candidate",
    ]


@dataclass
class _Identity:
    scheduled_cell_id: str
    task_index: int
    task_id: str
    seed: int


@dataclass
class _Wrapper:
    execution_identity: _Identity


def test_bound_fields_read_outer_select_bound_cell_not_execution_identity() -> None:
    @dataclass
    class _ExecutionIdentityOnly:
        condition_cell_id: str

    @dataclass
    class _SelectBoundEpisodeCellLike:
        scheduled_cell_id: str
        task_index: int
        task_id: str
        seed: int
        execution_identity: _ExecutionIdentityOnly

    identity = _ExecutionIdentityOnly(
        condition_cell_id="cell",
    )
    bound = _SelectBoundEpisodeCellLike(
        scheduled_cell_id="cell",
        task_index=7,
        task_id="task",
        seed=31,
        execution_identity=identity,
    )

    assert _execution_identity(bound) is identity
    assert _bound_cell_fields(bound) == (
        "cell",
        7,
        "task",
        31,
    )

    try:
        _bound_cell_fields(identity)
    except Exception as exc:
        assert "BOUND_CELL" in str(exc)
    else:
        raise AssertionError(
            "bare execution identity was incorrectly accepted as a bound cell"
        )


def test_wire_value_accepts_enum_like_and_plain_values() -> None:
    class _EnumLike:
        value = "DEV_VISIBLE"

    assert _wire_value(_EnumLike()) == "DEV_VISIBLE"
    assert _wire_value("valid_unseen") == "valid_unseen"


def test_materialized_readiness_authority_does_not_require_execution_provenance(
    tmp_path: Path,
) -> None:
    import hashlib

    artifact_values = {
        "e1_gamefile_sha256_preflight_v1.json": {
            "schema_id": "E1_GAMEFILE_SHA256_PREFLIGHT_V1",
        },
        "alfworld_environment_runtime_manifest_v1.json": {
            "schema_id": "ALFWORLD_ENVIRONMENT_RUNTIME_MANIFEST_V1",
        },
        "e1_policy_runtime_manifest_v1.json": {
            "schema_id": "E1_POLICY_RUNTIME_MANIFEST_V1",
        },
        "tokenizer_identity_manifest.json": {
            "schema_id": "TOKENIZER_IDENTITY_MANIFEST_V1",
        },
        "e1_evaluator_candidate_config_v1.json": {
            "schema_id": "E1_EVALUATOR_CANDIDATE_CONFIG_V1",
        },
    }
    hashes = {}
    for name, value in artifact_values.items():
        path = tmp_path / name
        path.write_text(
            json.dumps(value),
            encoding="utf-8",
        )
        hashes[name] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()

    summary = tmp_path / "readiness_summary.json"
    summary.write_text(
        json.dumps({
            "gamefile_identity_manifest_sha256":
                hashes["e1_gamefile_sha256_preflight_v1.json"],
            "environment_runtime_manifest_sha256":
                hashes["alfworld_environment_runtime_manifest_v1.json"],
            "policy_runtime_manifest_sha256":
                hashes["e1_policy_runtime_manifest_v1.json"],
            "tokenizer_identity_manifest_sha256":
                hashes["tokenizer_identity_manifest.json"],
            "candidate_config_sha256":
                hashes["e1_evaluator_candidate_config_v1.json"],
            "real_environment_executed": False,
            "model_called": False,
        }),
        encoding="utf-8",
    )

    result = audit_materialized_readiness_authority(tmp_path)

    runtime = tmp_path / "alfworld_environment_runtime_manifest_v1.json"
    assert result["environment_runtime_manifest_path"] == str(runtime)
    assert result["environment_runtime_manifest_sha256"] == (
        hashes["alfworld_environment_runtime_manifest_v1.json"]
    )
    assert result["readiness_summary_path"] == str(summary)
    assert "design_merge_commit" not in result
    assert "split_access_sha256" not in result


def test_historical_e1_design_merge_identity_is_exact() -> None:
    assert E1_DESIGN_MERGE_COMMIT == (
        "5cddface67c220c8c799d1b0699cf611d7ffc78a"
    )


def test_select_live_runner_uses_bound_task_access_for_split_access() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/live_runner.py"
    ).read_text(encoding="utf-8")
    assert (
        "split_access_sha256=identity.task_access_manifest_sha256"
        in source
    )
    assert "task_access_manifest_sha256=(" in source
    assert "identity.task_access_manifest_sha256" in source



def test_policy_request_authority_is_exact_source_file_not_recursive_discovery(
    tmp_path: Path,
) -> None:
    import hashlib
    import inspect

    import stage0.preflight as preflight

    helper = getattr(
        preflight,
        "audit_policy_request_source_authority",
        None,
    )
    assert helper is not None

    worktree = tmp_path / "wt"
    source = (
        worktree
        / "src/pchsi/evaluation/policy_request.py"
    )
    source.parent.mkdir(parents=True)
    source.write_text(
        "frozen request source\n",
        encoding="utf-8",
    )
    expected = hashlib.sha256(
        source.read_bytes()
    ).hexdigest()

    result = helper(
        worktree=worktree,
        expected_sha256=expected,
    )

    assert result == {
        "policy_request_source_path": str(source),
        "policy_request_schema_sha256": expected,
    }

    run_source = inspect.getsource(
        preflight.run_preflight
    )
    assert (
        "discover_policy_request_schema_authority("
        not in run_source
    )


def test_historical_policy_request_source_identity_is_exact() -> None:
    from stage0.constants import (
        E1_POLICY_REQUEST_SCHEMA_SHA256,
        E1_POLICY_REQUEST_SOURCE_RELATIVE_PATH,
    )

    assert E1_POLICY_REQUEST_SOURCE_RELATIVE_PATH == (
        "src/pchsi/evaluation/policy_request.py"
    )
    assert E1_POLICY_REQUEST_SCHEMA_SHA256 == (
        "a0edd1091b57224b70f3f403838e9f166ea8af0358da0661f1e636252bd0fc3a"
    )



def test_runtime_readiness_uses_explicit_proxy_free_opener() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/runtime_server.py"
    ).read_text(encoding="utf-8")

    assert "ProxyHandler({})" in source
    assert "_DIRECT_LOOPBACK_OPENER" in source
    assert "urlopen(" not in source


def test_loopback_http_rejects_non_loopback_targets() -> None:
    import stage0.runtime_server as runtime_server

    helper = getattr(
        runtime_server,
        "_validate_loopback_url",
        None,
    )
    assert helper is not None

    assert helper("http://127.0.0.1:18000/health") == (
        "127.0.0.1",
        18000,
    )
    assert helper("http://localhost:18000/v1/models") == (
        "localhost",
        18000,
    )

    try:
        helper("http://example.com:18000/health")
    except Exception as exc:
        assert "LOOPBACK" in str(exc).upper()
    else:
        raise AssertionError("non-loopback URL was accepted")


def test_v14_slurm_clears_proxy_environment_for_loopback_server() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "slurm/human_pilot_stage0_offoff.sbatch"
    ).read_text(encoding="utf-8")

    for name in (
        "http_proxy",
        "https_proxy",
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "all_proxy",
        "ALL_PROXY",
    ):
        assert f"unset {name}" in source

    assert 'export NO_PROXY="127.0.0.1,localhost"' in source
    assert 'export no_proxy="127.0.0.1,localhost"' in source


def test_patch_release_uses_v15_preflight_and_authorization_receipt_roots() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/constants.py"
    ).read_text(encoding="utf-8")

    assert 'PREFLIGHT_ROOT = STAGE0_ROOT / "preflight_v1_9"' in source
    assert (
        'AUTHORIZATION_ROOT = '
        'STAGE0_ROOT / "authorization_v1_9"'
        in source
    )



def test_preflight_contains_first_select_cell_binding_dry_run() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/preflight.py"
    ).read_text(encoding="utf-8")

    assert "audit_first_select_cell_binding_contract" in source
    assert "_bound_cell_fields(" in source
    assert "bound" in source
    assert "_execution_identity(" in source
    assert "identity = _execution_identity" in source
    assert "first_select_cell_binding_audit" in source


def test_runtime_readiness_receipt_is_job_specific() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/slurm_entry.py"
    ).read_text(encoding="utf-8")

    assert "RUNTIME_READINESS_JOB_" in source
    assert 'runtime_root / "RUNTIME_READINESS_V1.json"' not in source


def test_v15_uses_new_preflight_and_authorization_receipt_roots() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/constants.py"
    ).read_text(encoding="utf-8")

    assert 'PREFLIGHT_ROOT = STAGE0_ROOT / "preflight_v1_9"' in source
    assert (
        'AUTHORIZATION_ROOT = '
        'STAGE0_ROOT / "authorization_v1_9"'
        in source
    )



def test_v17_submit_flow_applies_generic_select_artifact_patch_before_preflight() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "RUN_PREFLIGHT_AND_SUBMIT.sh"
    ).read_text(encoding="utf-8")

    assert "05_APPLY_GENERIC_SELECT_ARTIFACT_PATCH.py" in source
    assert (
        source.index("05_APPLY_GENERIC_SELECT_ARTIFACT_PATCH.py")
        < source.index("10_OFFLINE_PREFLIGHT.py")
    )


def test_v17_fixed_head_expected_paths_include_artifact_identity_closure() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/preflight.py"
    ).read_text(encoding="utf-8")

    for path in (
        "src/pchsi/evaluation/action_trace.py",
        "src/pchsi/evaluation/schema_models.py",
        "configs/evaluation/schemas/e1_episode_artifact_v1.json",
        "tests/evaluation/test_generic_select_artifact_identity_v1.py",
    ):
        assert path in source


def test_v17_live_runner_closes_environment_in_finally() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/live_runner.py"
    ).read_text(encoding="utf-8")

    assert "finally:" in source
    assert "environment.close()" in source
    assert "STAGE0_ENVIRONMENT_CLEANUP_ERROR" in source


def test_v17_uses_new_preflight_and_authorization_roots() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/constants.py"
    ).read_text(encoding="utf-8")

    assert 'PREFLIGHT_ROOT = STAGE0_ROOT / "preflight_v1_9"' in source
    assert (
        'AUTHORIZATION_ROOT = '
        'STAGE0_ROOT / "authorization_v1_9"'
        in source
    )
    assert "GENERIC_SELECT_ARTIFACT_PATCH_ROOT" in source



def test_v18_attempt_allocator_skips_started_only_orphan(tmp_path: Path) -> None:
    from stage0.attempt_recovery import (
        audit_cell_attempt_state,
    )

    run_root = tmp_path / "candidate/evaluator_run"
    ledger = run_root / "attempt_ledger"
    ledger.mkdir(parents=True)

    cell = "p4-candidate-t00002-s0000000017"
    started = ledger / f"{cell}-a000.started.json"
    started.write_text(
        json.dumps({
            "schema_id": "E1_ATTEMPT_RECEIPT_V1",
            "schema_version": 1,
            "receipt_kind": "STARTED",
            "scheduled_cell_id": cell,
            "execution_attempt_id": f"{cell}-a000",
            "attempt_ordinal": 0,
        }),
        encoding="utf-8",
    )

    state = audit_cell_attempt_state(
        evaluator_root=run_root,
        scheduled_cell_id=cell,
    )

    assert state["published_attempt_ids"] == []
    assert state["started_only_attempt_ids"] == [
        f"{cell}-a000"
    ]
    assert state["next_attempt_ordinal"] == 1
    assert state["next_execution_attempt_id"] == (
        f"{cell}-a001"
    )


def test_v18_attempt_allocator_reuses_published_attempt(tmp_path: Path) -> None:
    from stage0.attempt_recovery import (
        audit_cell_attempt_state,
    )

    run_root = tmp_path / "parent/evaluator_run"
    attempts = run_root / "attempts"
    ledger = run_root / "attempt_ledger"
    attempts.mkdir(parents=True)
    ledger.mkdir(parents=True)

    cell = "p4-parent-t00002-s0000000017"
    attempt = f"{cell}-a000"
    (attempts / attempt).mkdir()
    (ledger / f"{attempt}.started.json").write_text(
        "{}",
        encoding="utf-8",
    )
    (ledger / f"{attempt}.terminal.json").write_text(
        "{}",
        encoding="utf-8",
    )

    state = audit_cell_attempt_state(
        evaluator_root=run_root,
        scheduled_cell_id=cell,
    )

    assert state["published_attempt_ids"] == [attempt]
    assert state["next_attempt_ordinal"] is None


def test_v18_live_runner_uses_recovery_allocator_not_hardcoded_a000() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/live_runner.py"
    ).read_text(encoding="utf-8")

    assert "audit_cell_attempt_state" in source
    assert "next_attempt_ordinal" in source
    assert "attempt_ordinal=0" not in source


def test_v18_preflight_audits_resume_state_before_gpu_execution() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/preflight.py"
    ).read_text(encoding="utf-8")

    assert "audit_stage0_resume_state" in source
    assert '"resume_state_audit"' in source


def test_v18_uses_new_preflight_and_authorization_roots() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/constants.py"
    ).read_text(encoding="utf-8")

    assert 'PREFLIGHT_ROOT = STAGE0_ROOT / "preflight_v1_9"' in source
    assert (
        'AUTHORIZATION_ROOT = '
        'STAGE0_ROOT / "authorization_v1_9"'
        in source
    )



def test_v19_new_attempt_binds_attempt_dir_before_post_publication_reload() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/live_runner.py"
    ).read_text(encoding="utf-8")

    assignment = (
        'attempt_dir = (\n'
        '        evaluator_root\n'
        '        / "attempts"\n'
        '        / attempt_id\n'
        '    )'
    )
    assert assignment in source
    assert (
        source.index(assignment)
        < source.index(
            'result = types["run_single_episode"]('
        )
    )


def test_v19_recovery_prefers_published_attempt_before_new_attempt() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/live_runner.py"
    ).read_text(encoding="utf-8")

    published_branch = source.index(
        'if published_attempt_ids:'
    )
    next_attempt = source.index(
        'attempt_ordinal = recovery['
    )
    assert published_branch < next_attempt


def test_v19_uses_new_preflight_and_authorization_roots() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "stage0/constants.py"
    ).read_text(encoding="utf-8")

    assert 'PREFLIGHT_ROOT = STAGE0_ROOT / "preflight_v1_9"' in source
    assert (
        'AUTHORIZATION_ROOT = '
        'STAGE0_ROOT / "authorization_v1_9"'
        in source
    )
