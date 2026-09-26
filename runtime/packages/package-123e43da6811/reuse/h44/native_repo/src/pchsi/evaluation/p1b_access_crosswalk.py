"""P1-B reviewed legacy/current task identity crosswalk."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import re
from typing import ClassVar, Self

from .canonical_evidence import canonical_json_text, require_lower_sha256, strict_json_loads
from .schema_contract import validate_payload_against_schema
from .task_manifest import FrozenTaskRecord

_SHA1 = re.compile(r"^[0-9a-f]{40}$")

class LegacyMatchStatus(str, Enum):
    EXACT_GAMEFILE_SHA1_MATCH = "EXACT_GAMEFILE_SHA1_MATCH"
    EXACT_TASK_ID_AND_PATH_MATCH = "EXACT_TASK_ID_AND_PATH_MATCH"
    TASK_ID_ONLY_INSUFFICIENT = "TASK_ID_ONLY_INSUFFICIENT"
    NO_MATCH = "NO_MATCH"
    LEGACY_RECORD_INCOMPLETE = "LEGACY_RECORD_INCOMPLETE"


def _text(name: str, value: object, *, optional: bool=False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty str")
    if any(c in value for c in ("\x00","\r","\n")):
        raise ValueError(f"{name} contains forbidden character")
    return value


def _sha1(name: str, value: object, *, optional: bool=False) -> str | None:
    if value is None and optional:
        return None
    if not isinstance(value, str) or _SHA1.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase SHA-1")
    return value

@dataclass(frozen=True, slots=True)
class LegacyTaskIdentityV1:
    legacy_source: str
    legacy_task_id: str | None
    legacy_gamefile: str | None
    legacy_gamefile_sha1: str | None
    evidence_source: str
    manual_same_gamefile_confirmed: bool = False

    def __post_init__(self) -> None:
        _text("legacy_source", self.legacy_source)
        _text("legacy_task_id", self.legacy_task_id, optional=True)
        _text("legacy_gamefile", self.legacy_gamefile, optional=True)
        _sha1("legacy_gamefile_sha1", self.legacy_gamefile_sha1, optional=True)
        _text("evidence_source", self.evidence_source)
        if type(self.manual_same_gamefile_confirmed) is not bool:
            raise TypeError("manual_same_gamefile_confirmed must be bool")

@dataclass(frozen=True, slots=True)
class LegacyCurrentTaskCrosswalkRecordV1:
    legacy_source: str
    legacy_task_id: str | None
    legacy_gamefile: str | None
    legacy_gamefile_sha1: str | None
    current_manifest_index: int
    current_task_id: str
    current_gamefile: str
    current_gamefile_sha1: str
    manual_same_gamefile_confirmed: bool
    match_status: LegacyMatchStatus
    evidence_source: str
    confidence_class: str

    def to_dict(self) -> dict[str, object]:
        return {
            "legacy_source": self.legacy_source,
            "legacy_task_id": self.legacy_task_id,
            "legacy_gamefile": self.legacy_gamefile,
            "legacy_gamefile_sha1": self.legacy_gamefile_sha1,
            "current_manifest_index": self.current_manifest_index,
            "current_task_id": self.current_task_id,
            "current_gamefile": self.current_gamefile,
            "current_gamefile_sha1": self.current_gamefile_sha1,
            "manual_same_gamefile_confirmed": self.manual_same_gamefile_confirmed,
            "match_status": self.match_status.value,
            "evidence_source": self.evidence_source,
            "confidence_class": self.confidence_class,
        }


def match_legacy_to_current(*, legacy: LegacyTaskIdentityV1, current: FrozenTaskRecord) -> LegacyCurrentTaskCrosswalkRecordV1:
    if not isinstance(legacy, LegacyTaskIdentityV1):
        raise TypeError("legacy must be LegacyTaskIdentityV1")
    if not isinstance(current, FrozenTaskRecord):
        raise TypeError("current must be FrozenTaskRecord")

    if legacy.legacy_gamefile_sha1 is not None and legacy.legacy_gamefile_sha1 == current.gamefile_sha1:
        status = LegacyMatchStatus.EXACT_GAMEFILE_SHA1_MATCH
        confidence = "HIGH"
    elif (
        legacy.legacy_task_id == current.task_id
        and legacy.legacy_gamefile == current.gamefile
        and legacy.manual_same_gamefile_confirmed
    ):
        status = LegacyMatchStatus.EXACT_TASK_ID_AND_PATH_MATCH
        confidence = "HIGH"
    elif legacy.legacy_task_id == current.task_id:
        status = LegacyMatchStatus.TASK_ID_ONLY_INSUFFICIENT
        confidence = "LOW"
    elif legacy.legacy_task_id is None and legacy.legacy_gamefile is None and legacy.legacy_gamefile_sha1 is None:
        status = LegacyMatchStatus.LEGACY_RECORD_INCOMPLETE
        confidence = "LOW"
    else:
        status = LegacyMatchStatus.NO_MATCH
        confidence = "LOW"

    return LegacyCurrentTaskCrosswalkRecordV1(
        legacy_source=legacy.legacy_source,
        legacy_task_id=legacy.legacy_task_id,
        legacy_gamefile=legacy.legacy_gamefile,
        legacy_gamefile_sha1=legacy.legacy_gamefile_sha1,
        current_manifest_index=current.index,
        current_task_id=current.task_id,
        current_gamefile=current.gamefile,
        current_gamefile_sha1=current.gamefile_sha1,
        manual_same_gamefile_confirmed=legacy.manual_same_gamefile_confirmed,
        match_status=status,
        evidence_source=legacy.evidence_source,
        confidence_class=confidence,
    )

@dataclass(frozen=True, slots=True)
class LegacyCurrentTaskCrosswalkV1:
    SCHEMA_ID: ClassVar[str] = "LEGACY_CURRENT_TASK_CROSSWALK_V1"
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    crosswalk_id: str
    current_task_manifest_sha256: str
    record_count: int
    records: tuple[LegacyCurrentTaskCrosswalkRecordV1, ...]

    def __post_init__(self) -> None:
        if self.schema_id != self.SCHEMA_ID or self.schema_version != 1:
            raise ValueError("crosswalk schema identity mismatch")
        _text("crosswalk_id", self.crosswalk_id)
        require_lower_sha256("current_task_manifest_sha256", self.current_task_manifest_sha256)
        if type(self.records) is not tuple or not self.records:
            raise ValueError("records must be non-empty tuple")
        if self.record_count != len(self.records):
            raise ValueError("record_count mismatch")
        validate_payload_against_schema(schema_id=self.SCHEMA_ID, payload=self.to_dict())

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "crosswalk_id": self.crosswalk_id,
            "current_task_manifest_sha256": self.current_task_manifest_sha256,
            "record_count": self.record_count,
            "records": [r.to_dict() for r in self.records],
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())
