"""Frozen x86-64 syscall-table and seccomp-policy helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .canonical import (
    CanonicalJsonError,
    canonical_json_bytes,
    sha256_hex,
    strict_json_loadb,
)


AUDIT_ARCH_X86_64 = 0xC000003E
X32_SYSCALL_BIT = 0x40000000
SECCOMP_RET_KILL_PROCESS = 0x80000000
SECCOMP_RET_ALLOW = 0x7FFF0000

_BPF_LD_W_ABS = "LD_W_ABS"
_BPF_JEQ_K = "JEQ_K"
_BPF_JSET_K = "JSET_K"
_BPF_RET_K = "RET_K"


@dataclass(frozen=True, slots=True)
class SyscallEntry:
    name: str
    number: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.name, str)
            or not self.name
            or not self.name.replace("_", "").isalnum()
        ):
            raise ValueError("invalid syscall name")
        if (
            isinstance(self.number, bool)
            or not isinstance(self.number, int)
            or self.number < 0
            or self.number & X32_SYSCALL_BIT
        ):
            raise ValueError("invalid syscall number")


@dataclass(frozen=True, slots=True)
class SyscallTable:
    schema_version: str
    architecture: str
    audit_arch: int
    entries: tuple[SyscallEntry, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "s1_syscall_table_v1":
            raise ValueError("unsupported syscall-table schema")
        if self.architecture != "x86_64":
            raise ValueError("unsupported architecture")
        if self.audit_arch != AUDIT_ARCH_X86_64:
            raise ValueError("audit architecture mismatch")
        if not isinstance(self.entries, tuple):
            raise ValueError("entries must be a tuple")

        numbers = tuple(entry.number for entry in self.entries)
        names = tuple(entry.name for entry in self.entries)

        if numbers != tuple(sorted(numbers)):
            raise ValueError("syscall numbers must be sorted")
        if len(set(numbers)) != len(numbers):
            raise ValueError("duplicate syscall number")
        if len(set(names)) != len(names):
            raise ValueError("duplicate syscall name")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "architecture": self.architecture,
            "audit_arch": self.audit_arch,
            "entries": [
                {
                    "name": entry.name,
                    "number": entry.number,
                }
                for entry in self.entries
            ],
        }

    @property
    def exact_semantics_sha256(self) -> str:
        return sha256_hex(canonical_json_bytes(self.to_dict()))


@dataclass(frozen=True, slots=True)
class BpfInstruction:
    operation: str
    value: int
    jump_true: int = 0
    jump_false: int = 0

    def to_dict(self) -> dict[str, object]:
        return {
            "operation": self.operation,
            "value": self.value,
            "jump_true": self.jump_true,
            "jump_false": self.jump_false,
        }


def load_syscall_table(path: Path) -> SyscallTable:
    value = strict_json_loadb(path.read_bytes())

    if not isinstance(value, dict):
        raise CanonicalJsonError("syscall table must be an object")

    required = {
        "schema_version",
        "architecture",
        "audit_arch",
        "entries",
    }
    if set(value) != required:
        raise CanonicalJsonError("unexpected syscall-table fields")

    raw_entries = value["entries"]
    if not isinstance(raw_entries, list):
        raise CanonicalJsonError("entries must be an array")

    entries: list[SyscallEntry] = []
    for raw_entry in raw_entries:
        if (
            not isinstance(raw_entry, dict)
            or set(raw_entry) != {"name", "number"}
        ):
            raise CanonicalJsonError("invalid syscall entry")
        entries.append(
            SyscallEntry(
                name=raw_entry["name"],
                number=raw_entry["number"],
            )
        )

    return SyscallTable(
        schema_version=value["schema_version"],
        architecture=value["architecture"],
        audit_arch=value["audit_arch"],
        entries=tuple(entries),
    )


def _validated_allowlist(
    *,
    table: SyscallTable,
    collector_allowlist: Iterable[int],
) -> tuple[int, ...]:
    allowed = tuple(sorted(collector_allowlist))

    if len(set(allowed)) != len(allowed):
        raise ValueError("duplicate allowlist syscall")

    table_numbers = {entry.number for entry in table.entries}
    if not set(allowed).issubset(table_numbers):
        raise ValueError("allowlist contains unknown syscall")

    return allowed


def derive_p7_case_ids(
    *,
    syscall_table: SyscallTable,
    collector_allowlist: frozenset[int],
) -> tuple[str, ...]:
    allowed = set(
        _validated_allowlist(
            table=syscall_table,
            collector_allowlist=collector_allowlist,
        )
    )
    return tuple(
        f"P7.{entry.number}"
        for entry in syscall_table.entries
        if entry.number not in allowed
    )


def p7_aggregate_deadline_seconds(case_count: int) -> int:
    if (
        isinstance(case_count, bool)
        or not isinstance(case_count, int)
        or case_count < 0
    ):
        raise ValueError("case_count must be a non-negative integer")
    return 30 + (3 * case_count)


def build_seccomp_instruction_records(
    *,
    syscall_table: SyscallTable,
    collector_allowlist: frozenset[int],
) -> tuple[BpfInstruction, ...]:
    allowed = _validated_allowlist(
        table=syscall_table,
        collector_allowlist=collector_allowlist,
    )

    instructions: list[BpfInstruction] = [
        BpfInstruction(_BPF_LD_W_ABS, 4),
        BpfInstruction(_BPF_JEQ_K, AUDIT_ARCH_X86_64, 1, 0),
        BpfInstruction(_BPF_RET_K, SECCOMP_RET_KILL_PROCESS),
        BpfInstruction(_BPF_LD_W_ABS, 0),
        BpfInstruction(_BPF_JSET_K, X32_SYSCALL_BIT, 0, 1),
        BpfInstruction(_BPF_RET_K, SECCOMP_RET_KILL_PROCESS),
    ]

    for syscall_number in allowed:
        instructions.append(
            BpfInstruction(_BPF_JEQ_K, syscall_number, 0, 1)
        )
        instructions.append(
            BpfInstruction(_BPF_RET_K, SECCOMP_RET_ALLOW)
        )

    instructions.append(
        BpfInstruction(_BPF_RET_K, SECCOMP_RET_KILL_PROCESS)
    )
    return tuple(instructions)


def verify_seccomp_instruction_records(
    *,
    syscall_table: SyscallTable,
    collector_allowlist: frozenset[int],
    instructions: tuple[BpfInstruction, ...],
) -> None:
    expected = build_seccomp_instruction_records(
        syscall_table=syscall_table,
        collector_allowlist=collector_allowlist,
    )
    if instructions != expected:
        raise ValueError("seccomp instruction program mismatch")
# Task 14 candidate-artifact status marker.
CANDIDATE_ARTIFACT_STATUS = (
    "candidate_pending_static_and_semantic_review"
)
