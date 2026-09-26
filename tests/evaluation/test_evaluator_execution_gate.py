from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts/evaluation/run_e1_evaluator.py"


def _run(*arguments: str):
    return subprocess.run(
        [sys.executable, "-S", str(SCRIPT), *arguments],
        check=False,
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
    )


def test_describe_is_deterministic_and_nonexecuting() -> None:
    first = _run("--describe")
    second = _run("--describe")
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert first.stdout == second.stdout
    payload = json.loads(first.stdout)
    assert payload == {
        "calls_model": False,
        "design_id": "E1_ALFWORLD_EVALUATOR_V1",
        "executes_environment": False,
        "execution_exit_code": 77,
        "modes": ["describe", "validate-config", "execute-closed"],
        "status": "CANDIDATE_EXECUTION_NOT_APPROVED",
        "writes_run_artifacts": False,
    }


def test_validate_config_is_pure_and_rejects_missing_readiness_artifacts(
    tmp_path: Path,
) -> None:
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "schema_id": "E1_EVALUATOR_CANDIDATE_CONFIG_V1",
                "task_manifest": str(tmp_path / "task.jsonl"),
                "gamefile_identity_manifest": str(tmp_path / "gamefiles.json"),
                "environment_runtime_manifest": str(tmp_path / "environment.json"),
                "policy_runtime_manifest": str(tmp_path / "policy.json"),
            }
        ),
        encoding="utf-8",
    )
    before = set(tmp_path.iterdir())
    result = _run("--validate-config", str(config))
    after = set(tmp_path.iterdir())
    assert result.returncode == 2
    assert before == after
    assert "MISSING_READINESS_ARTIFACT" in result.stderr


def test_execute_always_returns_77() -> None:
    result = _run("--execute")
    assert result.returncode == 77
    assert result.stdout.strip() == (
        "E1_EVALUATOR_EXECUTION_NOT_APPROVED"
    )


def test_no_force_unsafe_debug_or_environment_bypass_exists() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    for forbidden in (
        "--force",
        "--unsafe",
        "--debug-execute",
        "os.environ",
        "getenv(",
        "environ[",
    ):
        assert forbidden not in source

    help_result = _run("--help")
    assert help_result.returncode == 0
    assert "--describe" in help_result.stdout
    assert "--validate-config" in help_result.stdout
    assert "--execute" in help_result.stdout
    assert "--force" not in help_result.stdout


def test_repository_approval_string_cannot_self_authorize(
    tmp_path: Path,
) -> None:
    config = tmp_path / "config.json"
    config.write_text(
        json.dumps(
            {
                "schema_id": "E1_EVALUATOR_CANDIDATE_CONFIG_V1",
                "task_manifest": str(tmp_path / "missing-a"),
                "gamefile_identity_manifest": str(tmp_path / "missing-b"),
                "environment_runtime_manifest": str(tmp_path / "missing-c"),
                "policy_runtime_manifest": str(tmp_path / "missing-d"),
                "approval": "E1_DEV_EXECUTION_APPROVED",
                "execute": True,
            }
        ),
        encoding="utf-8",
    )
    result = _run("--validate-config", str(config))
    assert result.returncode == 2
    assert "UNKNOWN_CONFIG_FIELD" in result.stderr


def test_cli_has_no_hidden_execute_true_configuration_path() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert '"execute"' not in source
    assert "execute=True" not in source
    assert "execution_approved" not in source.casefold()
