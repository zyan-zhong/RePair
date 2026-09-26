from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, sha256_bytes
from pchsi.memory.procedural_builder import ProceduralFailureMemoryRecordV1
from pchsi.memory.projection_common import ProjectionRecordBindingV1
from pchsi.memory.sequence_failure_experience import SequenceFailureExperienceV1


class MemorySourceIntegrityFailureCodeV1(str, Enum):
    SOURCE_COUNT_MISMATCH = "SOURCE_COUNT_MISMATCH"
    SOURCE_BINDING_MISMATCH = "SOURCE_BINDING_MISMATCH"


@dataclass(frozen=True, slots=True)
class MemorySourceIntegrityReportV1:
    record_binding: ProjectionRecordBindingV1
    status: str
    failure_codes: tuple[MemorySourceIntegrityFailureCodeV1, ...]
    source_experience_ids: tuple[str, ...]
    source_experience_sha256s: tuple[str, ...]
    report_sha256: str | None = None

    def __post_init__(self) -> None:
        if self.status not in {"VERIFIED", "FAILED"}:
            raise ValueError("invalid source-integrity status")
        if (self.status == "FAILED") != bool(self.failure_codes):
            raise ValueError("status/failure_codes mismatch")
        expected = sha256_bytes(
            b"MEMORY_SOURCE_INTEGRITY_REPORT_V1\0"
            + canonical_json_bytes(self._payload())
        )
        if self.report_sha256 is None:
            object.__setattr__(self, "report_sha256", expected)
        elif self.report_sha256 != expected:
            raise ValueError("report_sha256 mismatch")

    def _payload(self) -> dict[str, object]:
        return {
            "schema_id": "MEMORY_SOURCE_INTEGRITY_REPORT_V1",
            "schema_version": 1,
            "record_binding": self.record_binding.to_dict(),
            "status": self.status,
            "failure_codes": [x.value for x in self.failure_codes],
            "source_experience_ids": list(self.source_experience_ids),
            "source_experience_sha256s": list(self.source_experience_sha256s),
        }

    def to_dict(self) -> dict[str, object]:
        return {**self._payload(), "report_sha256": self.report_sha256}

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())


def _binding(record: ProceduralFailureMemoryRecordV1) -> ProjectionRecordBindingV1:
    return ProjectionRecordBindingV1(
        memory_lineage_id=record.memory_lineage_id,
        record_version=record.record_version,
        canonical_record_sha256=record.canonical_record_sha256,
    )


def audit_memory_source_integrity_v1(
    *,
    record: ProceduralFailureMemoryRecordV1,
    registered_experiences: tuple[SequenceFailureExperienceV1, ...],
) -> MemorySourceIntegrityReportV1:
    if type(registered_experiences) is not tuple:
        raise TypeError("registered_experiences must be tuple")
    failures = []
    bindings = record.provenance.factual_sequence_bindings
    if len(bindings) != len(registered_experiences):
        failures.append(MemorySourceIntegrityFailureCodeV1.SOURCE_COUNT_MISMATCH)
    for binding, experience in zip(bindings, registered_experiences):
        try:
            binding.validate_against(experience)
        except (TypeError, ValueError):
            failures.append(MemorySourceIntegrityFailureCodeV1.SOURCE_BINDING_MISMATCH)
    ordered = tuple(dict.fromkeys(failures))
    return MemorySourceIntegrityReportV1(
        record_binding=_binding(record),
        status="FAILED" if ordered else "VERIFIED",
        failure_codes=ordered,
        source_experience_ids=tuple(x.experience_id for x in registered_experiences),
        source_experience_sha256s=tuple(
            sha256_bytes(x.canonical_bytes()) for x in registered_experiences
        ),
    )
