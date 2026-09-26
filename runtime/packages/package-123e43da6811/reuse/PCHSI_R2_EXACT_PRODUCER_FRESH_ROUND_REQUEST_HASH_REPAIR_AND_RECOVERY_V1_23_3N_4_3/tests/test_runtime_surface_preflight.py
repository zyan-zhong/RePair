from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "producer"))


def git(repo: Path, *args: str) -> str:
    cp = subprocess.run(["git", "-C", str(repo), *args], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    assert cp.returncode == 0, cp.stderr
    return cp.stdout.strip()


def make_repo(tmp_path: Path):
    repo = tmp_path / "repo"
    repo.mkdir()
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "fixture@example.invalid")
    git(repo, "config", "user.name", "fixture")
    files = {
        "src/pchsi/evaluation/episode_evaluator.py": "# eval\n",
        "src/pchsi/evaluation/policy_attempt_adapter.py": "# adapter\n",
        "src/pchsi/round_control/attempt_receipts.py": "# receipt\n",
        "src/pchsi/round_control/clean_execution_binding.py": "# binding\n",
        "src/pchsi/round_control/rollout_collection.py": "# rollout\n",
        "scripts/evaluation/build_environment_runtime_manifest.py": "# env builder\n",
        "docs/unrelated.txt": "outside\n",
    }
    for rel, text in files.items():
        p = repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixture")

    capsule = tmp_path / "capsule"
    for rel in [
        "src/pchsi/evaluation/episode_evaluator.py",
        "src/pchsi/evaluation/policy_attempt_adapter.py",
        "src/pchsi/round_control/attempt_receipts.py",
        "src/pchsi/round_control/clean_execution_binding.py",
        "src/pchsi/round_control/rollout_collection.py",
    ]:
        dst = capsule / "repo_source" / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((repo / rel).read_bytes())

    authority = tmp_path / "authority.json"
    authority.write_text(json.dumps({
        "schema_id": "R2_PRODUCER_RUNTIME_SURFACE_PREFLIGHT_V1",
        "runtime_surface_pathspecs": [
            "src/pchsi/evaluation",
            "src/pchsi/round_control",
            "scripts/evaluation",
        ],
        "capsule_source_bindings": [
            {"capsule_relative": "repo_source/src/pchsi/evaluation/episode_evaluator.py", "worktree_relative": "src/pchsi/evaluation/episode_evaluator.py"},
            {"capsule_relative": "repo_source/src/pchsi/evaluation/policy_attempt_adapter.py", "worktree_relative": "src/pchsi/evaluation/policy_attempt_adapter.py"},
            {"capsule_relative": "repo_source/src/pchsi/round_control/attempt_receipts.py", "worktree_relative": "src/pchsi/round_control/attempt_receipts.py"},
            {"capsule_relative": "repo_source/src/pchsi/round_control/clean_execution_binding.py", "worktree_relative": "src/pchsi/round_control/clean_execution_binding.py"},
            {"capsule_relative": "repo_source/src/pchsi/round_control/rollout_collection.py", "worktree_relative": "src/pchsi/round_control/rollout_collection.py"},
        ],
        "tracked_scan": {
            "command": "git diff --name-only HEAD -- <runtime surfaces>",
            "timeout_seconds": 60,
            "require_empty_stdout": True,
        },
        "untracked_scan": {
            "command": "git ls-files --others --exclude-standard -- <runtime surfaces>",
            "initial_timeout_seconds": 30,
            "retry_timeout_seconds": 180,
            "retry_condition": "TIMEOUT_ONLY",
            "maximum_attempts": 2,
            "argv_must_be_identical": True,
        },
    }, sort_keys=True))
    return repo, capsule, authority


def module():
    import runtime_surface_preflight as m
    return m


def test_broad_git_status_is_not_present_in_production_sources():
    bad = "status" + "','--porcelain=v1','--untracked-files=all"
    for path in [
        ROOT / "native_preflight.py",
        ROOT / "producer/shard_worker.py",
        ROOT / "producer/formal_rollout_support.py",
        ROOT / "analyzer_preflight.py",
        ROOT / "supervise.py",
    ]:
        text = path.read_text()
        assert "--untracked-files=all" not in text
        assert bad not in text


def test_untracked_outside_runtime_surfaces_does_not_block(tmp_path):
    repo, capsule, authority = make_repo(tmp_path)
    (repo / "scratch.txt").write_text("outside untracked\n")
    result = module().validate_runtime_surface(repo, capsule, authority)
    assert result["status"] == "PASS"
    assert result["untracked_runtime_surface_paths"] == []


def test_untracked_inside_runtime_surface_fails_closed(tmp_path):
    repo, capsule, authority = make_repo(tmp_path)
    p = repo / "src/pchsi/evaluation/rogue.py"
    p.write_text("# rogue\n")
    with pytest.raises(RuntimeError, match="RUNTIME_SURFACE_UNTRACKED"):
        module().validate_runtime_surface(repo, capsule, authority)


def test_tracked_change_inside_runtime_surface_fails_closed(tmp_path):
    repo, capsule, authority = make_repo(tmp_path)
    p = repo / "scripts/evaluation/build_environment_runtime_manifest.py"
    p.write_text("# changed\n")
    with pytest.raises(RuntimeError, match="RUNTIME_SURFACE_TRACKED_DIRTY"):
        module().validate_runtime_surface(repo, capsule, authority)


def test_tracked_change_outside_runtime_surface_does_not_block(tmp_path):
    repo, capsule, authority = make_repo(tmp_path)
    (repo / "docs/unrelated.txt").write_text("changed outside\n")
    result = module().validate_runtime_surface(repo, capsule, authority)
    assert result["status"] == "PASS"


def test_capsule_bound_source_mismatch_fails_closed(tmp_path):
    repo, capsule, authority = make_repo(tmp_path)
    p = repo / "src/pchsi/evaluation/episode_evaluator.py"
    p.write_text("# changed\n")
    with pytest.raises(RuntimeError, match="RUNTIME_SOURCE_CAPSULE_MISMATCH"):
        module().validate_runtime_surface(repo, capsule, authority)


def test_untracked_timeout_retries_identical_bounded_argv_once(monkeypatch, tmp_path):
    repo, capsule, authority = make_repo(tmp_path)
    m = module()
    original = m._run
    calls = []

    def fake(argv, timeout):
        calls.append((list(argv), timeout))
        if "ls-files" in argv and len([x for x in calls if "ls-files" in x[0]]) == 1:
            return {"returncode": 124, "stdout": "", "stderr": "TIMEOUT:"}
        return original(argv, timeout)

    monkeypatch.setattr(m, "_run", fake)
    result = m.validate_runtime_surface(repo, capsule, authority)
    ls_calls = [x for x in calls if "ls-files" in x[0]]
    assert result["status"] == "PASS"
    assert len(ls_calls) == 2
    assert ls_calls[0][0] == ls_calls[1][0]
    assert ls_calls[0][1] == 30
    assert ls_calls[1][1] == 180
    assert "status" not in ls_calls[0][0]
    assert ls_calls[0][0][-3:] == ["src/pchsi/evaluation", "src/pchsi/round_control", "scripts/evaluation"]


def test_native_preflight_and_worker_share_runtime_surface_validator():
    native = (ROOT / "native_preflight.py").read_text()
    worker = (ROOT / "producer/shard_worker.py").read_text()
    assert "validate_runtime_surface" in native
    assert "validate_runtime_surface" in worker


def test_analyzer_preflight_and_monitor_use_bounded_surface_validator():
    analyzer = (ROOT / "analyzer_preflight.py").read_text()
    monitor = (ROOT / "supervise.py").read_text()
    assert "ANALYZER_RUNTIME_SURFACE_PREFLIGHT_V1.json" in analyzer
    assert "validate_runtime_surface" in analyzer
    assert "validate_runtime_surface" in monitor
    assert "--untracked-files=all" not in analyzer
    assert "--untracked-files=all" not in monitor
