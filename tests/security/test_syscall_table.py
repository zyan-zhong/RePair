from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from pchsi.security.canonical import strict_json_loadb
from pchsi.security.syscall_table import (
    AUDIT_ARCH_X86_64,
    SECCOMP_RET_KILL_PROCESS,
    X32_SYSCALL_BIT,
    BpfInstruction,
    build_seccomp_instruction_records,
    derive_p7_case_ids,
    load_syscall_table,
    p7_aggregate_deadline_seconds,
    verify_seccomp_instruction_records,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = (
    Path(__file__).resolve().parent
    / "fixtures"
    / "syscall_table_x86_64.json"
)


def test_load_frozen_x86_64_table() -> None:
    table = load_syscall_table(FIXTURE)

    assert table.architecture == "x86_64"
    assert table.audit_arch == AUDIT_ARCH_X86_64
    assert table.entries[0].number == 0
    assert table.entries[-1].number == 435
    assert len(table.exact_semantics_sha256) == 64


def test_p7_case_identity_and_deadline() -> None:
    table = load_syscall_table(FIXTURE)
    allowlist = frozenset({0, 1, 3, 60, 231})
    cases = derive_p7_case_ids(
        syscall_table=table,
        collector_allowlist=allowlist,
    )

    assert "P7.0" not in cases
    assert "P7.56" in cases
    assert "P7.435" in cases
    assert len(cases) == len(table.entries) - len(allowlist)
    assert p7_aggregate_deadline_seconds(len(cases)) == (
        30 + 3 * len(cases)
    )


def test_filter_records_have_arch_x32_and_default_deny() -> None:
    table = load_syscall_table(FIXTURE)
    instructions = build_seccomp_instruction_records(
        syscall_table=table,
        collector_allowlist=frozenset({0, 1, 3}),
    )

    assert instructions[1].value == AUDIT_ARCH_X86_64
    assert instructions[2].value == SECCOMP_RET_KILL_PROCESS
    assert instructions[4].value == X32_SYSCALL_BIT
    assert instructions[5].value == SECCOMP_RET_KILL_PROCESS
    assert instructions[-1].value == SECCOMP_RET_KILL_PROCESS

    verify_seccomp_instruction_records(
        syscall_table=table,
        collector_allowlist=frozenset({0, 1, 3}),
        instructions=instructions,
    )


def test_filter_verifier_rejects_mutation() -> None:
    table = load_syscall_table(FIXTURE)
    allowlist = frozenset({0, 1})
    instructions = list(
        build_seccomp_instruction_records(
            syscall_table=table,
            collector_allowlist=allowlist,
        )
    )
    instructions[1] = BpfInstruction(
        instructions[1].operation,
        0,
        instructions[1].jump_true,
        instructions[1].jump_false,
    )

    with pytest.raises(ValueError, match="program mismatch"):
        verify_seccomp_instruction_records(
            syscall_table=table,
            collector_allowlist=allowlist,
            instructions=tuple(instructions),
        )


def test_unknown_allowlist_syscall_is_rejected() -> None:
    table = load_syscall_table(FIXTURE)

    with pytest.raises(ValueError, match="unknown syscall"):
        derive_p7_case_ids(
            syscall_table=table,
            collector_allowlist=frozenset({999999}),
        )


def _subprocess_environment() -> dict[str, str]:
    environment = os.environ.copy()
    source = str(REPO_ROOT / "src")
    current = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source if not current else os.pathsep.join((source, current))
    )
    return environment


def test_generation_scripts_are_nonexecuting(tmp_path: Path) -> None:
    canonical_table = tmp_path / "table.json"
    filter_manifest = tmp_path / "filter.json"

    first = subprocess.run(
        [
            sys.executable,
            "scripts/security/generate_syscall_table.py",
            "--input",
            str(FIXTURE),
            "--output",
            str(canonical_table),
        ],
        cwd=REPO_ROOT,
        env=_subprocess_environment(),
        check=False,
        text=True,
        capture_output=True,
    )
    assert first.returncode == 0, first.stderr

    second = subprocess.run(
        [
            sys.executable,
            "scripts/security/generate_seccomp_filters.py",
            "--syscall-table",
            str(canonical_table),
            "--allowlist",
            "0,1,3,60,231",
            "--output",
            str(filter_manifest),
        ],
        cwd=REPO_ROOT,
        env=_subprocess_environment(),
        check=False,
        text=True,
        capture_output=True,
    )
    assert second.returncode == 0, second.stderr

    payload = strict_json_loadb(filter_manifest.read_bytes())
    assert (
        payload["status"]
        == "candidate_pending_static_and_semantic_review"
    )
    assert payload["p7_case_timeout_seconds"] == 2
    assert payload["candidate_exact_sha256"]
# ---------------------------------------------------------------------------
# Task 12: P7 case manifest remains isolated and attributable
# ---------------------------------------------------------------------------

import json as _task12_json
from pathlib import Path as _Task12Path


def test_p7_payload_manifest_is_isolated() -> None:
    root = (
        _Task12Path(__file__).resolve().parents[2]
        / "configs"
        / "security"
        / "probes"
    )

    p7 = _task12_json.loads(
        (root / "p07.json").read_text(encoding="utf-8")
    )

    assert p7["probe_id"] == "P07"
    assert p7["profile_id"] == "S1_P7_SYSCALL_CASE_V1"
    assert p7["timeout_seconds"] == 2
    assert p7["expected_normalized_outcome"] == "KILLED"

    p15 = {
        _task12_json.loads(path.read_text(encoding="utf-8"))["probe_id"]
        for path in root.glob("p15_*.json")
    }
    p18 = {
        _task12_json.loads(path.read_text(encoding="utf-8"))["probe_id"]
        for path in root.glob("p18_*.json")
    }

    assert p15 == {"P15_CONTROL", "P15_LIMITED"}
    assert p18 == {"P18_BASELINE", "P18_RESTRICTED"}
# ---------------------------------------------------------------------------
# Task 14: candidate status is explicit
# ---------------------------------------------------------------------------

def test_candidate_artifact_status_is_not_approved() -> None:
    from pchsi.security.syscall_table import CANDIDATE_ARTIFACT_STATUS

    assert CANDIDATE_ARTIFACT_STATUS == (
        "candidate_pending_static_and_semantic_review"
    )
