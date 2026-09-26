"""Authority-driven, bounded repository preflight for the native rollout producer."""
from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _run(argv: list[str], timeout: int) -> dict[str, object]:
    try:
        cp = subprocess.run(
            argv,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False,
            check=False,
            timeout=timeout,
        )
        return {"returncode": cp.returncode, "stdout": cp.stdout, "stderr": cp.stderr}
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": "" if exc.stdout is None else str(exc.stdout),
            "stderr": "TIMEOUT:" + ("" if exc.stderr is None else str(exc.stderr)),
        }


def _require_regular(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError(label + ":" + str(path))
    return path


def _load_authority(path: Path) -> dict[str, object]:
    path = _require_regular(path, "RUNTIME_SURFACE_AUTHORITY_NOT_REGULAR")
    value = json.loads(path.read_text())
    if value.get("schema_id") != "R2_PRODUCER_RUNTIME_SURFACE_PREFLIGHT_V1":
        raise RuntimeError("RUNTIME_SURFACE_AUTHORITY_SCHEMA")
    surfaces = value.get("runtime_surface_pathspecs")
    if not isinstance(surfaces, list) or not surfaces or not all(isinstance(x, str) and x and not Path(x).is_absolute() and ".." not in Path(x).parts for x in surfaces):
        raise RuntimeError("RUNTIME_SURFACE_PATHS_INVALID")
    bindings = value.get("capsule_source_bindings", [])
    if not isinstance(bindings, list):
        raise RuntimeError("RUNTIME_SOURCE_BINDINGS_INVALID")
    return value


def _timeout_retry(argv: list[str], *, initial: int, retry: int) -> dict[str, object]:
    if type(initial) is not int or type(retry) is not int or initial <= 0 or retry <= initial:
        raise RuntimeError("RUNTIME_SURFACE_TIMEOUT_POLICY_INVALID")
    frozen = list(argv)
    first = _run(frozen, initial)
    timed_out = first["returncode"] == 124 and str(first.get("stderr", "")).startswith("TIMEOUT:")
    if not timed_out:
        return first
    second = _run(frozen, retry)
    if list(argv) != frozen:
        raise RuntimeError("RUNTIME_SURFACE_RETRY_ARGV_CHANGED")
    return second


def _nonempty_lines(text: object) -> list[str]:
    return [line for line in str(text or "").splitlines() if line.strip()]


def validate_runtime_surface(
    worktree: Path,
    capsule_root: Path,
    authority_path: Path | None = None,
) -> dict[str, object]:
    worktree = Path(worktree).resolve()
    capsule_root = None if capsule_root is None else Path(capsule_root).resolve()
    if authority_path is None:
        authority_path = Path(__file__).resolve().parents[1] / "audit" / "R2_PRODUCER_RUNTIME_SURFACE_PREFLIGHT_V1.json"
    authority = _load_authority(Path(authority_path))
    surfaces = list(authority["runtime_surface_pathspecs"])

    verified_sources = []
    for row in authority["capsule_source_bindings"]:
        if not isinstance(row, dict):
            raise RuntimeError("RUNTIME_SOURCE_BINDING_ROW_INVALID")
        cap_rel = row.get("capsule_relative")
        wt_rel = row.get("worktree_relative")
        if not isinstance(cap_rel, str) or not isinstance(wt_rel, str):
            raise RuntimeError("RUNTIME_SOURCE_BINDING_PATH_INVALID")
        if capsule_root is None:
            raise RuntimeError("CAPSULE_ROOT_REQUIRED_FOR_SOURCE_BINDING")
        cap = _require_regular(capsule_root / cap_rel, "CAPSULE_RUNTIME_SOURCE_MISSING")
        wt = _require_regular(worktree / wt_rel, "WORKTREE_RUNTIME_SOURCE_MISSING")
        cap_sha = _sha(cap)
        wt_sha = _sha(wt)
        if cap_sha != wt_sha:
            raise RuntimeError("RUNTIME_SOURCE_CAPSULE_MISMATCH:" + wt_rel)
        verified_sources.append({"worktree_relative": wt_rel, "sha256": wt_sha})


    tracked_policy = authority.get("tracked_scan")
    if not isinstance(tracked_policy, dict):
        raise RuntimeError("TRACKED_SCAN_POLICY_INVALID")
    tracked_argv = ["git", "-C", str(worktree), "diff", "--name-only", "HEAD", "--", *surfaces]
    tracked = _run(tracked_argv, int(tracked_policy.get("timeout_seconds", 0)))
    if tracked["returncode"] != 0:
        raise RuntimeError("RUNTIME_SURFACE_TRACKED_SCAN_FAILED:" + str(tracked.get("stderr", ""))[-1000:])
    tracked_dirty = _nonempty_lines(tracked.get("stdout"))
    if tracked_dirty:
        raise RuntimeError("RUNTIME_SURFACE_TRACKED_DIRTY:" + json.dumps(tracked_dirty, ensure_ascii=False))

    untracked_policy = authority.get("untracked_scan")
    if not isinstance(untracked_policy, dict) or untracked_policy.get("retry_condition") != "TIMEOUT_ONLY" or untracked_policy.get("maximum_attempts") != 2 or untracked_policy.get("argv_must_be_identical") is not True:
        raise RuntimeError("UNTRACKED_SCAN_POLICY_INVALID")
    untracked_argv = ["git", "-C", str(worktree), "ls-files", "--others", "--exclude-standard", "--", *surfaces]
    untracked = _timeout_retry(
        untracked_argv,
        initial=int(untracked_policy.get("initial_timeout_seconds", 0)),
        retry=int(untracked_policy.get("retry_timeout_seconds", 0)),
    )
    if untracked["returncode"] != 0:
        raise RuntimeError("RUNTIME_SURFACE_UNTRACKED_SCAN_FAILED:" + str(untracked.get("stderr", ""))[-1000:])
    untracked_paths = _nonempty_lines(untracked.get("stdout"))
    if untracked_paths:
        raise RuntimeError("RUNTIME_SURFACE_UNTRACKED:" + json.dumps(untracked_paths, ensure_ascii=False))

    return {
        "schema_id": "R2_PRODUCER_RUNTIME_SURFACE_PREFLIGHT_RECEIPT_V1",
        "status": "PASS",
        "authority_sha256": _sha(Path(authority_path)),
        "runtime_surface_pathspecs": surfaces,
        "tracked_runtime_surface_paths": [],
        "untracked_runtime_surface_paths": [],
        "capsule_bound_source_count": len(verified_sources),
        "capsule_bound_sources": verified_sources,
        "full_worktree_git_status_executed": False,
        "untracked_scan_argv": untracked_argv,
    }
