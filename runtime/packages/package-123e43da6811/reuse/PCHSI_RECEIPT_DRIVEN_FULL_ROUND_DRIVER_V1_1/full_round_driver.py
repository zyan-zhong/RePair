#!/usr/bin/env python3
"""Thin receipt-driven control plane for one PCHSI policy-improvement round.

This driver intentionally does not implement rollout, Analyzer, Planner, F0/F1,
Memory, training, evaluation, or promotion logic. It only binds already-frozen
stage commands into a dependency DAG, verifies terminal receipts, and resumes by
reusing completed receipts rather than blindly repeating side effects.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import subprocess
import sys
import time
from typing import Any

SCHEMA_ID = "PCHSI_FULL_ROUND_PLAN_V1"
SAFE_BINDINGS = {"BOUND", "UNBOUND"}
SIDE_EFFECT_CLASSES = {
    "DETERMINISTIC",
    "PROVIDER_OR_ENVIRONMENT",
    "TRAINING",
    "PROMOTION",
}


class DriverError(RuntimeError):
    pass


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        raise DriverError(f"JSON_LOAD_FAILED={path}:{type(e).__name__}:{e}") from e


def write_once_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(value) + b"\n"
    if path.exists():
        if path.read_bytes() != raw:
            raise DriverError(f"IMMUTABLE_DRIVER_RECEIPT_MISMATCH={path}")
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(raw)
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def validate_plan(plan: Any) -> list[dict[str, Any]]:
    if not isinstance(plan, dict):
        raise DriverError("PLAN_MUST_BE_OBJECT")
    if plan.get("schema_id") != SCHEMA_ID or plan.get("schema_version") != 1:
        raise DriverError("PLAN_SCHEMA_ID_OR_VERSION_INVALID")
    gates = plan.get("gates")
    if not isinstance(gates, list) or not gates:
        raise DriverError("PLAN_GATES_MUST_BE_NONEMPTY_ARRAY")
    ids: list[str] = []
    by_id: dict[str, dict[str, Any]] = {}
    for raw in gates:
        if not isinstance(raw, dict):
            raise DriverError("GATE_MUST_BE_OBJECT")
        gid = raw.get("gate_id")
        if not isinstance(gid, str) or not gid or len(gid) > 128:
            raise DriverError("GATE_ID_INVALID")
        if gid in by_id:
            raise DriverError(f"DUPLICATE_GATE_ID={gid}")
        binding = raw.get("binding_status")
        if binding not in SAFE_BINDINGS:
            raise DriverError(f"GATE_BINDING_STATUS_INVALID={gid}")
        side = raw.get("side_effect_class")
        if side not in SIDE_EFFECT_CLASSES:
            raise DriverError(f"GATE_SIDE_EFFECT_CLASS_INVALID={gid}")
        deps = raw.get("depends_on")
        if not isinstance(deps, list) or any(not isinstance(x, str) or not x for x in deps):
            raise DriverError(f"GATE_DEPENDS_ON_INVALID={gid}")
        if len(deps) != len(set(deps)):
            raise DriverError(f"GATE_DEPENDENCIES_DUPLICATE={gid}")
        command = raw.get("command")
        if not isinstance(command, list) or not command or any(not isinstance(x, str) or not x for x in command):
            raise DriverError(f"GATE_COMMAND_INVALID={gid}")
        receipt = raw.get("terminal_receipt")
        if not isinstance(receipt, str) or not receipt:
            raise DriverError(f"GATE_TERMINAL_RECEIPT_INVALID={gid}")
        contract = raw.get("terminal_contract")
        if not isinstance(contract, dict) or contract.get("kind") not in {"JSON_FIELD", "JSON_FIELD_IN", "FILE_EXISTS"}:
            raise DriverError(f"GATE_TERMINAL_CONTRACT_INVALID={gid}")
        ids.append(gid)
        by_id[gid] = raw
    all_ids = set(ids)
    for gid in ids:
        for dep in by_id[gid]["depends_on"]:
            if dep not in all_ids:
                raise DriverError(f"UNKNOWN_DEPENDENCY={gid}:{dep}")
            if dep == gid:
                raise DriverError(f"SELF_DEPENDENCY={gid}")
    # Stable Kahn topological order: retain plan order among ready nodes.
    pending = set(ids)
    done: set[str] = set()
    ordered: list[dict[str, Any]] = []
    while pending:
        progressed = False
        for gid in ids:
            if gid not in pending:
                continue
            if set(by_id[gid]["depends_on"]) <= done:
                ordered.append(by_id[gid])
                done.add(gid)
                pending.remove(gid)
                progressed = True
        if not progressed:
            raise DriverError("DEPENDENCY_CYCLE")
    return ordered


def expand_token(value: str, variables: dict[str, str]) -> str:
    out = value
    for key, replacement in variables.items():
        out = out.replace("{" + key + "}", replacement)
    unresolved = re.findall(r"\{[A-Z][A-Z0-9_]*\}", out)
    if unresolved:
        # Refuse accidental unresolved control-plane placeholders while allowing
        # braces that are ordinary data/code in an argv token.
        raise DriverError(f"UNRESOLVED_PLACEHOLDER={unresolved[0]}")
    return out


def resolved_gate(gate: dict[str, Any], variables: dict[str, str]) -> dict[str, Any]:
    out = dict(gate)
    out["command"] = [expand_token(x, variables) for x in gate["command"]]
    out["terminal_receipt"] = expand_token(gate["terminal_receipt"], variables)
    cwd = gate.get("cwd")
    out["cwd"] = None if cwd is None else expand_token(str(cwd), variables)
    return out


def terminal_valid(gate: dict[str, Any]) -> tuple[bool, str | None]:
    path = Path(gate["terminal_receipt"])
    if not path.is_file() or path.is_symlink():
        return False, None
    contract = gate["terminal_contract"]
    kind = contract["kind"]
    if kind == "FILE_EXISTS":
        return True, sha256_file(path)
    try:
        value = load_json(path)
    except DriverError:
        return False, None
    if not isinstance(value, dict):
        return False, None
    field = contract.get("field")
    if not isinstance(field, str) or not field:
        return False, None
    if kind == "JSON_FIELD":
        ok = value.get(field) == contract.get("equals")
    else:
        values = contract.get("in")
        ok = isinstance(values, list) and value.get(field) in values
    return (ok, sha256_file(path) if ok else None)


def git_output(repo: Path, *args: str) -> str:
    cp = subprocess.run(
        ["git", "-C", str(repo), *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=False,
    )
    if cp.returncode != 0:
        raise DriverError(f"GIT_PREFLIGHT_FAILED={' '.join(args)}:{cp.stderr.strip()}")
    return cp.stdout.strip()


def preflight_repo(plan: dict[str, Any], repo: Path | None) -> None:
    expected_head = plan.get("expected_repo_head")
    expected_branch = plan.get("expected_repo_branch")
    require_clean = bool(plan.get("require_clean_worktree", False))
    if expected_head is None and expected_branch is None and not require_clean:
        return
    if repo is None:
        raise DriverError("REPO_REQUIRED_BY_PLAN")
    repo = repo.resolve()
    if not (repo / ".git").exists():
        # Worktrees may have a .git file, too.
        if not (repo / ".git").is_file():
            raise DriverError(f"REPO_NOT_GIT_WORKTREE={repo}")
    if expected_head is not None and git_output(repo, "rev-parse", "HEAD") != expected_head:
        raise DriverError("REPO_HEAD_MISMATCH")
    if expected_branch is not None and git_output(repo, "branch", "--show-current") != expected_branch:
        raise DriverError("REPO_BRANCH_MISMATCH")
    if require_clean and git_output(repo, "status", "--porcelain=v1", "--untracked-files=all"):
        raise DriverError("REPO_WORKTREE_NOT_CLEAN")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--plan", required=True)
    ap.add_argument("--state-root", required=True)
    ap.add_argument("--repo")
    ap.add_argument("--preflight-only", action="store_true")
    args = ap.parse_args()

    plan_path = Path(args.plan).resolve()
    state_root = Path(args.state_root).resolve()
    repo = None if args.repo is None else Path(args.repo).resolve()
    plan = load_json(plan_path)
    ordered = validate_plan(plan)
    preflight_repo(plan, repo)
    variables = {
        "REPO": "" if repo is None else str(repo),
        "STATE_ROOT": str(state_root),
        "ROUND_ID": str(plan.get("round_id", "")),
        "POLICY_VERSION": str(plan.get("policy_version", "")),
    }
    resolved = [resolved_gate(g, variables) for g in ordered]
    unbound = [g["gate_id"] for g in resolved if g["binding_status"] != "BOUND"]
    if unbound:
        for gid in unbound:
            print(f"UNBOUND_GATE={gid}")
        raise DriverError("PLAN_HAS_UNBOUND_GATES")

    plan_sha = sha256_bytes(canonical_bytes(plan))
    state_root.mkdir(parents=True, exist_ok=True)
    write_once_json(
        state_root / "plan_binding.json",
        {
            "schema_id": "PCHSI_FULL_ROUND_PLAN_BINDING_V1",
            "schema_version": 1,
            "plan_path": str(plan_path),
            "plan_sha256": plan_sha,
            "round_id": plan.get("round_id"),
            "policy_version": plan.get("policy_version"),
            "expected_repo_head": plan.get("expected_repo_head"),
        },
    )

    # Preflight verifies every path/contract structurally but never executes a gate.
    if args.preflight_only:
        print(f"PCHSI_FULL_ROUND_PREFLIGHT_PASS gates={len(resolved)} plan_sha256={plan_sha}")
        print("PROVIDER_CALL_COUNT=0")
        print("ENVIRONMENT_CALL_COUNT=0")
        print("TRAINING_EXECUTION_COUNT=0")
        return 0

    completed: set[str] = set()
    for gate in resolved:
        gid = gate["gate_id"]
        missing_deps = [d for d in gate["depends_on"] if d not in completed]
        if missing_deps:
            raise DriverError(f"DEPENDENCY_NOT_TERMINAL={gid}:{','.join(missing_deps)}")
        valid, receipt_sha = terminal_valid(gate)
        gate_state = state_root / "gates" / gid
        terminal_state = gate_state / "terminal.json"
        started_state = gate_state / "started.json"
        command_sha = sha256_bytes(canonical_bytes({"command": gate["command"], "cwd": gate["cwd"]}))
        if valid:
            write_once_json(
                terminal_state,
                {
                    "schema_id": "PCHSI_FULL_ROUND_GATE_TERMINAL_V1",
                    "schema_version": 1,
                    "gate_id": gid,
                    "disposition": "REUSED_EXISTING_TERMINAL_RECEIPT",
                    "command_sha256": command_sha,
                    "terminal_receipt": gate["terminal_receipt"],
                    "terminal_receipt_sha256": receipt_sha,
                },
            )
            print(f"GATE_REUSED={gid}")
            completed.add(gid)
            continue
        if terminal_state.exists():
            raise DriverError(f"DRIVER_TERMINAL_WITHOUT_VALID_CHILD_RECEIPT={gid}")
        if started_state.exists():
            # No blind resend after an execution may have begun. The child stage must
            # first materialize a valid terminal receipt or be explicitly reconciled.
            raise DriverError(f"PARTIAL_UNSAFE_GATE={gid}")
        gate_state.mkdir(parents=True, exist_ok=True)
        write_once_json(
            started_state,
            {
                "schema_id": "PCHSI_FULL_ROUND_GATE_START_V1",
                "schema_version": 1,
                "gate_id": gid,
                "command_sha256": command_sha,
                "side_effect_class": gate["side_effect_class"],
                "started_unix_ns": time.time_ns(),
            },
        )
        cp = subprocess.run(
            gate["command"],
            cwd=gate["cwd"],
            shell=False,
        )
        if cp.returncode != 0:
            write_once_json(
                gate_state / "failed.json",
                {
                    "schema_id": "PCHSI_FULL_ROUND_GATE_FAILURE_V1",
                    "schema_version": 1,
                    "gate_id": gid,
                    "command_sha256": command_sha,
                    "returncode": cp.returncode,
                    "terminal_receipt_present": Path(gate["terminal_receipt"]).is_file(),
                },
            )
            raise DriverError(f"GATE_COMMAND_FAILED={gid}:rc={cp.returncode}")
        valid, receipt_sha = terminal_valid(gate)
        if not valid:
            raise DriverError(f"TERMINAL_RECEIPT_INVALID={gid}")
        write_once_json(
            terminal_state,
            {
                "schema_id": "PCHSI_FULL_ROUND_GATE_TERMINAL_V1",
                "schema_version": 1,
                "gate_id": gid,
                "disposition": "EXECUTED_AND_TERMINAL",
                "command_sha256": command_sha,
                "terminal_receipt": gate["terminal_receipt"],
                "terminal_receipt_sha256": receipt_sha,
            },
        )
        print(f"GATE_COMPLETE={gid}")
        completed.add(gid)

    final = {
        "schema_id": "PCHSI_FULL_ROUND_DRIVER_RESULT_V1",
        "schema_version": 1,
        "round_id": plan.get("round_id"),
        "policy_version": plan.get("policy_version"),
        "plan_sha256": plan_sha,
        "completed_gate_ids": [g["gate_id"] for g in resolved],
        "status": "ROUND_CONTROL_PLANE_TERMINAL",
    }
    write_once_json(state_root / "full_round_terminal.json", final)
    print(f"PCHSI_FULL_ROUND_DRIVER_PASS gates={len(resolved)}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except DriverError as e:
        print(f"STOP={e}", file=sys.stderr)
        raise SystemExit(2)
