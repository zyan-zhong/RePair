"""Deterministic round-to-round Failure Memory maintenance.

Within one self-improvement round the active snapshot is immutable. New evidence is
append-only shadow evidence and is never readable by Policy/Analyzer/Researcher in
the same round. Only after the verifier result is available may the round close and
emit a next-round snapshot plan.

This module does not mutate governed Memory record bytes. It maintains bindings and
dispositions so that record/version updates remain explicit and content addressed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    strict_json_loads,
)


def _require_sha(name: str, value: object) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"{name} must be 64 lowercase hex")
    return value


def _require_text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be nonempty str")
    if any(ch in value for ch in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains forbidden control character")
    return value


def _domain_sha(domain: str, value: object) -> str:
    return hashlib.sha256(
        domain.encode("utf-8")
        + b"\0"
        + canonical_json_bytes(value)
    ).hexdigest()


class MemoryRoundPhaseV1(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class MemorySourcePartitionV1(str, Enum):
    TRAIN_MEMORY_SOURCE = "TRAIN_MEMORY_SOURCE"
    TRAIN_RETRIEVAL_DEV = "TRAIN_RETRIEVAL_DEV"
    VALID_SEEN = "VALID_SEEN"
    VALID_UNSEEN = "VALID_UNSEEN"
    FORMAL_EVALUATION = "FORMAL_EVALUATION"


class VerifierEffectV1(str, Enum):
    BENEFIT = "Benefit"
    HARM = "Harm"
    NEUTRAL = "Neutral"
    UNCERTAIN = "Uncertain"
    INFRASTRUCTURE_NO_OUTCOME = "INFRASTRUCTURE_NO_OUTCOME"


class ShadowDispositionV1(str, Enum):
    PROMOTE_NEXT_ROUND = "PROMOTE_NEXT_ROUND"
    QUARANTINE = "QUARANTINE"
    DESCRIPTIVE_ONLY = "DESCRIPTIVE_ONLY"
    STAGING_UNRESOLVED = "STAGING_UNRESOLVED"
    SHADOW_ONLY_NO_ACTIVE_WRITEBACK = (
        "SHADOW_ONLY_NO_ACTIVE_WRITEBACK"
    )
    FORBIDDEN_EVALUATION_WRITEBACK = (
        "FORBIDDEN_EVALUATION_WRITEBACK"
    )
    REJECT_INFRASTRUCTURE_ONLY = (
        "REJECT_INFRASTRUCTURE_ONLY"
    )


@dataclass(frozen=True, slots=True)
class MemoryRecordBindingV1:
    memory_lineage_id: str
    record_version: int
    canonical_record_sha256: str

    def __post_init__(self) -> None:
        _require_sha(
            "memory_lineage_id",
            self.memory_lineage_id,
        )
        _require_sha(
            "canonical_record_sha256",
            self.canonical_record_sha256,
        )
        if type(self.record_version) is not int or self.record_version < 1:
            raise ValueError("record_version must be positive int")

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "canonical_record_sha256": (
                self.canonical_record_sha256
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryRecordBindingV1":
        if not isinstance(value, dict) or set(value) != {
            "memory_lineage_id",
            "record_version",
            "canonical_record_sha256",
        }:
            raise ValueError("record binding fields mismatch")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class MemoryRoundStateV1:
    round_id: str
    policy_identity_sha256: str
    active_snapshot_sha256: str
    active_record_bindings: tuple[
        MemoryRecordBindingV1, ...
    ]
    phase: MemoryRoundPhaseV1 = MemoryRoundPhaseV1.OPEN
    parent_round_id: str | None = None
    state_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_text("round_id", self.round_id)
        _require_sha(
            "policy_identity_sha256",
            self.policy_identity_sha256,
        )
        _require_sha(
            "active_snapshot_sha256",
            self.active_snapshot_sha256,
        )
        if not isinstance(self.phase, MemoryRoundPhaseV1):
            raise TypeError("phase type mismatch")
        if self.parent_round_id is not None:
            _require_text(
                "parent_round_id",
                self.parent_round_id,
            )
        if type(self.active_record_bindings) is not tuple:
            raise TypeError(
                "active_record_bindings must be tuple"
            )
        lineages = tuple(
            row.memory_lineage_id
            for row in self.active_record_bindings
        )
        if len(lineages) != len(set(lineages)):
            raise ValueError(
                "active record lineages must be unique"
            )
        expected = _domain_sha(
            "MEMORY_ROUND_STATE_V1",
            self._without_sha(),
        )
        if self.state_sha256 is None:
            object.__setattr__(self, "state_sha256", expected)
        elif self.state_sha256 != expected:
            raise ValueError("round state SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "round_id": self.round_id,
            "policy_identity_sha256": (
                self.policy_identity_sha256
            ),
            "active_snapshot_sha256": (
                self.active_snapshot_sha256
            ),
            "active_record_bindings": [
                row.to_dict()
                for row in self.active_record_bindings
            ],
            "phase": self.phase.value,
            "parent_round_id": self.parent_round_id,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "MEMORY_ROUND_STATE_V1",
            "schema_version": 1,
            **self._without_sha(),
            "state_sha256": self.state_sha256,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryRoundStateV1":
        if not isinstance(value, dict):
            raise TypeError("round state must be object")
        expected = {
            "schema_id",
            "schema_version",
            "round_id",
            "policy_identity_sha256",
            "active_snapshot_sha256",
            "active_record_bindings",
            "phase",
            "parent_round_id",
            "state_sha256",
        }
        if set(value) != expected:
            raise ValueError("round state fields mismatch")
        if (
            value["schema_id"] != "MEMORY_ROUND_STATE_V1"
            or value["schema_version"] != 1
        ):
            raise ValueError("round state schema mismatch")
        raw = value["active_record_bindings"]
        if not isinstance(raw, list):
            raise TypeError(
                "active_record_bindings must be array"
            )
        return cls(
            round_id=value["round_id"],
            policy_identity_sha256=(
                value["policy_identity_sha256"]
            ),
            active_snapshot_sha256=(
                value["active_snapshot_sha256"]
            ),
            active_record_bindings=tuple(
                MemoryRecordBindingV1.from_dict(row)
                for row in raw
            ),
            phase=MemoryRoundPhaseV1(value["phase"]),
            parent_round_id=value["parent_round_id"],
            state_sha256=value["state_sha256"],
        )

    @classmethod
    def from_json(
        cls,
        value: bytes | str,
    ) -> "MemoryRoundStateV1":
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return cls.from_dict(strict_json_loads(value))


@dataclass(frozen=True, slots=True)
class MemoryShadowEventV1:
    round_id: str
    record_binding: MemoryRecordBindingV1
    source_partition: MemorySourcePartitionV1
    analyzer_finding_sha256: str
    candidate_repair_sha256: str
    verifier_effect: VerifierEffectV1
    f0_evidence_sha256: str | None
    f1_evidence_sha256: str | None
    evidence_complete: bool
    evaluation_contamination_clean: bool
    event_id: str | None = None

    def __post_init__(self) -> None:
        _require_text("round_id", self.round_id)
        if not isinstance(
            self.record_binding,
            MemoryRecordBindingV1,
        ):
            raise TypeError("record_binding type mismatch")
        if not isinstance(
            self.source_partition,
            MemorySourcePartitionV1,
        ):
            raise TypeError("source_partition type mismatch")
        if not isinstance(
            self.verifier_effect,
            VerifierEffectV1,
        ):
            raise TypeError("verifier_effect type mismatch")
        _require_sha(
            "analyzer_finding_sha256",
            self.analyzer_finding_sha256,
        )
        _require_sha(
            "candidate_repair_sha256",
            self.candidate_repair_sha256,
        )
        for name in (
            "f0_evidence_sha256",
            "f1_evidence_sha256",
        ):
            value = getattr(self, name)
            if value is not None:
                _require_sha(name, value)
        if type(self.evidence_complete) is not bool:
            raise TypeError("evidence_complete must be bool")
        if type(self.evaluation_contamination_clean) is not bool:
            raise TypeError(
                "evaluation_contamination_clean must be bool"
            )
        if (
            self.verifier_effect
            is not VerifierEffectV1.INFRASTRUCTURE_NO_OUTCOME
            and self.evidence_complete
            and (
                self.f0_evidence_sha256 is None
                or self.f1_evidence_sha256 is None
            )
        ):
            raise ValueError(
                "complete scientific effect requires F0 and F1 evidence"
            )
        expected = _domain_sha(
            "MEMORY_SHADOW_EVENT_V1",
            self._without_id(),
        )
        if self.event_id is None:
            object.__setattr__(self, "event_id", expected)
        elif self.event_id != expected:
            raise ValueError("shadow event ID mismatch")

    def _without_id(self) -> dict[str, object]:
        return {
            "round_id": self.round_id,
            "record_binding": self.record_binding.to_dict(),
            "source_partition": self.source_partition.value,
            "analyzer_finding_sha256": (
                self.analyzer_finding_sha256
            ),
            "candidate_repair_sha256": (
                self.candidate_repair_sha256
            ),
            "verifier_effect": self.verifier_effect.value,
            "f0_evidence_sha256": self.f0_evidence_sha256,
            "f1_evidence_sha256": self.f1_evidence_sha256,
            "evidence_complete": self.evidence_complete,
            "evaluation_contamination_clean": (
                self.evaluation_contamination_clean
            ),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "MEMORY_SHADOW_EVENT_V1",
            "schema_version": 1,
            **self._without_id(),
            "event_id": self.event_id,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryShadowEventV1":
        if not isinstance(value, dict):
            raise TypeError("shadow event must be object")
        expected = {
            "schema_id",
            "schema_version",
            "round_id",
            "record_binding",
            "source_partition",
            "analyzer_finding_sha256",
            "candidate_repair_sha256",
            "verifier_effect",
            "f0_evidence_sha256",
            "f1_evidence_sha256",
            "evidence_complete",
            "evaluation_contamination_clean",
            "event_id",
        }
        if set(value) != expected:
            raise ValueError("shadow event fields mismatch")
        if (
            value["schema_id"] != "MEMORY_SHADOW_EVENT_V1"
            or value["schema_version"] != 1
        ):
            raise ValueError("shadow event schema mismatch")
        return cls(
            round_id=value["round_id"],
            record_binding=MemoryRecordBindingV1.from_dict(
                value["record_binding"]
            ),
            source_partition=MemorySourcePartitionV1(
                value["source_partition"]
            ),
            analyzer_finding_sha256=(
                value["analyzer_finding_sha256"]
            ),
            candidate_repair_sha256=(
                value["candidate_repair_sha256"]
            ),
            verifier_effect=VerifierEffectV1(
                value["verifier_effect"]
            ),
            f0_evidence_sha256=value["f0_evidence_sha256"],
            f1_evidence_sha256=value["f1_evidence_sha256"],
            evidence_complete=value["evidence_complete"],
            evaluation_contamination_clean=(
                value["evaluation_contamination_clean"]
            ),
            event_id=value["event_id"],
        )


@dataclass(frozen=True, slots=True)
class MemoryRoundDispositionV1:
    event_id: str
    record_binding: MemoryRecordBindingV1
    disposition: ShadowDispositionV1
    reason: str

    def __post_init__(self) -> None:
        _require_sha("event_id", self.event_id)
        if not isinstance(
            self.record_binding,
            MemoryRecordBindingV1,
        ):
            raise TypeError("record_binding type mismatch")
        if not isinstance(
            self.disposition,
            ShadowDispositionV1,
        ):
            raise TypeError("disposition type mismatch")
        _require_text("reason", self.reason)

    def to_dict(self) -> dict[str, object]:
        return {
            "event_id": self.event_id,
            "record_binding": self.record_binding.to_dict(),
            "disposition": self.disposition.value,
            "reason": self.reason,
        }


@dataclass(frozen=True, slots=True)
class MemoryRoundClosureV1:
    closed_round_id: str
    parent_state_sha256: str
    dispositions: tuple[
        MemoryRoundDispositionV1, ...
    ]
    next_active_record_bindings: tuple[
        MemoryRecordBindingV1, ...
    ]
    next_snapshot_plan_sha256: str
    closure_sha256: str | None = None

    def __post_init__(self) -> None:
        _require_text(
            "closed_round_id",
            self.closed_round_id,
        )
        _require_sha(
            "parent_state_sha256",
            self.parent_state_sha256,
        )
        _require_sha(
            "next_snapshot_plan_sha256",
            self.next_snapshot_plan_sha256,
        )
        if type(self.dispositions) is not tuple:
            raise TypeError("dispositions must be tuple")
        if type(self.next_active_record_bindings) is not tuple:
            raise TypeError(
                "next_active_record_bindings must be tuple"
            )
        lineages = tuple(
            row.memory_lineage_id
            for row in self.next_active_record_bindings
        )
        if len(lineages) != len(set(lineages)):
            raise ValueError(
                "next active lineages must be unique"
            )
        expected = _domain_sha(
            "MEMORY_ROUND_CLOSURE_V1",
            self._without_sha(),
        )
        if self.closure_sha256 is None:
            object.__setattr__(
                self,
                "closure_sha256",
                expected,
            )
        elif self.closure_sha256 != expected:
            raise ValueError("closure SHA mismatch")

    def _without_sha(self) -> dict[str, object]:
        return {
            "closed_round_id": self.closed_round_id,
            "parent_state_sha256": self.parent_state_sha256,
            "dispositions": [
                row.to_dict() for row in self.dispositions
            ],
            "next_active_record_bindings": [
                row.to_dict()
                for row in self.next_active_record_bindings
            ],
            "next_snapshot_plan_sha256": (
                self.next_snapshot_plan_sha256
            ),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "MEMORY_ROUND_CLOSURE_V1",
            "schema_version": 1,
            **self._without_sha(),
            "closure_sha256": self.closure_sha256,
        }


def classify_shadow_event_v1(
    event: MemoryShadowEventV1,
) -> MemoryRoundDispositionV1:
    partition = event.source_partition
    effect = event.verifier_effect

    if partition in {
        MemorySourcePartitionV1.VALID_SEEN,
        MemorySourcePartitionV1.VALID_UNSEEN,
        MemorySourcePartitionV1.FORMAL_EVALUATION,
    }:
        return MemoryRoundDispositionV1(
            event_id=event.event_id,
            record_binding=event.record_binding,
            disposition=(
                ShadowDispositionV1
                .FORBIDDEN_EVALUATION_WRITEBACK
            ),
            reason=(
                "held-out/formal evaluation evidence cannot write "
                "back into active Memory"
            ),
        )

    if partition is MemorySourcePartitionV1.TRAIN_RETRIEVAL_DEV:
        return MemoryRoundDispositionV1(
            event_id=event.event_id,
            record_binding=event.record_binding,
            disposition=(
                ShadowDispositionV1
                .SHADOW_ONLY_NO_ACTIVE_WRITEBACK
            ),
            reason=(
                "TRAIN_RETRIEVAL_DEV is diagnostic shadow-only"
            ),
        )

    if effect is VerifierEffectV1.INFRASTRUCTURE_NO_OUTCOME:
        return MemoryRoundDispositionV1(
            event_id=event.event_id,
            record_binding=event.record_binding,
            disposition=(
                ShadowDispositionV1
                .REJECT_INFRASTRUCTURE_ONLY
            ),
            reason=(
                "infrastructure-only incident has no scientific "
                "Memory/training authority"
            ),
        )

    if effect is VerifierEffectV1.HARM:
        return MemoryRoundDispositionV1(
            event_id=event.event_id,
            record_binding=event.record_binding,
            disposition=ShadowDispositionV1.QUARANTINE,
            reason="verified Harm is quarantined",
        )

    if effect is VerifierEffectV1.BENEFIT:
        if (
            event.evidence_complete
            and event.evaluation_contamination_clean
            and event.f0_evidence_sha256 is not None
            and event.f1_evidence_sha256 is not None
        ):
            return MemoryRoundDispositionV1(
                event_id=event.event_id,
                record_binding=event.record_binding,
                disposition=(
                    ShadowDispositionV1.PROMOTE_NEXT_ROUND
                ),
                reason=(
                    "clean complete train-side Benefit may enter "
                    "the next round only"
                ),
            )
        return MemoryRoundDispositionV1(
            event_id=event.event_id,
            record_binding=event.record_binding,
            disposition=(
                ShadowDispositionV1.STAGING_UNRESOLVED
            ),
            reason=(
                "Benefit label lacks complete clean F0/F1 authority"
            ),
        )

    if effect is VerifierEffectV1.NEUTRAL:
        return MemoryRoundDispositionV1(
            event_id=event.event_id,
            record_binding=event.record_binding,
            disposition=ShadowDispositionV1.DESCRIPTIVE_ONLY,
            reason=(
                "Neutral may remain descriptive but is not "
                "positive/prescriptive authority"
            ),
        )

    return MemoryRoundDispositionV1(
        event_id=event.event_id,
        record_binding=event.record_binding,
        disposition=ShadowDispositionV1.STAGING_UNRESOLVED,
        reason="Uncertain evidence remains staging-only",
    )


def active_bindings_for_current_round_v1(
    state: MemoryRoundStateV1,
) -> tuple[MemoryRecordBindingV1, ...]:
    if state.phase is not MemoryRoundPhaseV1.OPEN:
        raise ValueError("current-round access requires OPEN state")
    return state.active_record_bindings


def _next_bindings(
    state: MemoryRoundStateV1,
    dispositions: Iterable[MemoryRoundDispositionV1],
) -> tuple[MemoryRecordBindingV1, ...]:
    active = {
        row.memory_lineage_id: row
        for row in state.active_record_bindings
    }
    for row in dispositions:
        if (
            row.disposition
            is not ShadowDispositionV1.PROMOTE_NEXT_ROUND
        ):
            continue
        candidate = row.record_binding
        previous = active.get(candidate.memory_lineage_id)
        if previous is not None:
            if candidate.record_version <= previous.record_version:
                raise ValueError(
                    "promoted record version must advance lineage"
                )
        active[candidate.memory_lineage_id] = candidate
    return tuple(
        active[lineage]
        for lineage in sorted(active)
    )


def close_memory_round_v1(
    *,
    state: MemoryRoundStateV1,
    shadow_events: Iterable[MemoryShadowEventV1],
) -> MemoryRoundClosureV1:
    if state.phase is not MemoryRoundPhaseV1.OPEN:
        raise ValueError("only OPEN round may close")
    events = tuple(shadow_events)
    event_ids = tuple(row.event_id for row in events)
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("shadow event IDs must be unique")
    for event in events:
        if event.round_id != state.round_id:
            raise ValueError("shadow event belongs to another round")

    dispositions = tuple(
        classify_shadow_event_v1(event)
        for event in sorted(
            events,
            key=lambda row: row.event_id,
        )
    )
    next_bindings = _next_bindings(
        state,
        dispositions,
    )
    next_plan = {
        "parent_round_id": state.round_id,
        "parent_state_sha256": state.state_sha256,
        "active_snapshot_sha256": (
            state.active_snapshot_sha256
        ),
        "next_active_record_bindings": [
            row.to_dict() for row in next_bindings
        ],
        "dispositions": [
            row.to_dict() for row in dispositions
        ],
        "same_round_readback_used": False,
        "activation_timing": "NEXT_ROUND_ONLY",
    }
    plan_sha = _domain_sha(
        "NEXT_MEMORY_SNAPSHOT_PLAN_V1",
        next_plan,
    )
    return MemoryRoundClosureV1(
        closed_round_id=state.round_id,
        parent_state_sha256=state.state_sha256,
        dispositions=dispositions,
        next_active_record_bindings=next_bindings,
        next_snapshot_plan_sha256=plan_sha,
    )


def next_round_state_v1(
    *,
    previous_state: MemoryRoundStateV1,
    closure: MemoryRoundClosureV1,
    next_round_id: str,
    next_snapshot_sha256: str,
    next_policy_identity_sha256: str,
) -> MemoryRoundStateV1:
    if closure.closed_round_id != previous_state.round_id:
        raise ValueError("closure/previous round mismatch")
    if closure.parent_state_sha256 != previous_state.state_sha256:
        raise ValueError("closure parent state mismatch")
    return MemoryRoundStateV1(
        round_id=next_round_id,
        parent_round_id=previous_state.round_id,
        policy_identity_sha256=(
            next_policy_identity_sha256
        ),
        active_snapshot_sha256=next_snapshot_sha256,
        active_record_bindings=(
            closure.next_active_record_bindings
        ),
        phase=MemoryRoundPhaseV1.OPEN,
    )


def _write_new(path: Path, data: bytes) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("write made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def initialize_round_store_v1(
    *,
    root: Path,
    state: MemoryRoundStateV1,
) -> Path:
    root = Path(root)
    if root.exists() or root.is_symlink():
        raise FileExistsError(str(root))
    root.mkdir(parents=True, mode=0o700)
    _write_new(
        root / "ROUND_STATE_V1.json",
        canonical_json_bytes(state.to_dict()),
    )
    (root / "shadow").mkdir(mode=0o700)
    (root / "shadow/events").mkdir(mode=0o700)
    return root


def append_shadow_event_v1(
    *,
    root: Path,
    state: MemoryRoundStateV1,
    event: MemoryShadowEventV1,
) -> Path:
    if state.phase is not MemoryRoundPhaseV1.OPEN:
        raise ValueError("cannot append to closed round")
    if event.round_id != state.round_id:
        raise ValueError("event round mismatch")
    root = Path(root)
    if (root / "ROUND_CLOSURE_V1.json").exists():
        raise ValueError("cannot append after round closure")
    stored = MemoryRoundStateV1.from_json(
        (root / "ROUND_STATE_V1.json").read_bytes()
    )
    if stored != state:
        raise ValueError("round-store state mismatch")
    path = root / "shadow/events" / f"{event.event_id}.json"
    _write_new(path, canonical_json_bytes(event.to_dict()))
    ledger = root / "shadow/SHADOW_EVENT_LEDGER_V1.jsonl"
    line = canonical_json_bytes(event.to_dict())
    fd = os.open(
        ledger,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
    try:
        view = memoryview(line)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("append write made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)
    return path


def finalize_round_store_v1(
    *,
    root: Path,
    state: MemoryRoundStateV1,
) -> MemoryRoundClosureV1:
    root = Path(root)
    event_root = root / "shadow/events"
    events = tuple(
        MemoryShadowEventV1.from_dict(
            strict_json_loads(path.read_bytes())
        )
        for path in sorted(event_root.glob("*.json"))
    )
    closure = close_memory_round_v1(
        state=state,
        shadow_events=events,
    )
    _write_new(
        root / "ROUND_CLOSURE_V1.json",
        canonical_json_bytes(closure.to_dict()),
    )
    return closure
