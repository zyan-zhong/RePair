"""Immutable distillation task-access governance contracts."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
import re
from typing import ClassVar, Self

from .canonical_evidence import (
    canonical_json_text,
    require_lower_sha256,
    strict_json_loads,
)
from .schema_contract import validate_payload_against_schema


_SHA1 = re.compile(r"^[0-9a-f]{40}$")


def _mapping(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("wire value must be a JSON object")
    if any(not isinstance(key, str) for key in value):
        raise TypeError("wire object keys must be strings")
    return value


def _expect_keys(payload: dict[str, object], expected: set[str]) -> None:
    missing = sorted(expected - set(payload))
    unknown = sorted(set(payload) - expected)
    if missing:
        raise ValueError(f"wire object is missing required fields: {missing}")
    if unknown:
        raise ValueError(f"wire object contains unknown fields: {unknown}")


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be a non-empty string")
    if any(character in value for character in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains a forbidden character")
    return value


def _optional_date(name: str, value: object) -> str | None:
    if value is None:
        return None
    text = _text(name, value)
    try:
        parsed = date.fromisoformat(text)
    except ValueError as error:
        raise ValueError(f"{name} must be YYYY-MM-DD") from error
    if parsed.isoformat() != text:
        raise ValueError(f"{name} must be canonical YYYY-MM-DD")
    return text


def _sha1(name: str, value: object) -> str:
    if not isinstance(value, str) or _SHA1.fullmatch(value) is None:
        raise ValueError(f"{name} must be a 40-character lowercase SHA-1")
    return value


def _tuple_strings(name: str, value: object) -> tuple[str, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be tuple")
    result = tuple(_text(f"{name} item", item) for item in value)
    if not result:
        raise ValueError(f"{name} must not be empty")
    if len(set(result)) != len(result):
        raise ValueError(f"{name} contains duplicates")
    return result


def _wire_string_tuple(name: str, value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a JSON array")
    return tuple(value)


class HistoricalAccessFlag(str, Enum):
    NO_KNOWN_PRIOR_ACCESS = "NO_KNOWN_PRIOR_ACCESS"
    ACCESS_HISTORY_INCOMPLETE = "ACCESS_HISTORY_INCOMPLETE"
    AGGREGATE_ONLY = "AGGREGATE_ONLY"
    EXECUTED_NOT_INSPECTED = "EXECUTED_NOT_INSPECTED"
    TRAJECTORY_INSPECTED = "TRAJECTORY_INSPECTED"
    USED_FOR_METHOD_DESIGN = "USED_FOR_METHOD_DESIGN"
    SENT_TO_EXTERNAL_MODEL = "SENT_TO_EXTERNAL_MODEL"


class DistillationAccessClass(str, Enum):
    DEV_VISIBLE = "DEV_VISIBLE"
    SELECT_SUMMARY_ONLY = "SELECT_SUMMARY_ONLY"
    CONFIRMATORY_SEALED = "CONFIRMATORY_SEALED"
    HISTORICALLY_EXPOSED = "HISTORICALLY_EXPOSED"


def _flags(
    name: str,
    value: object,
) -> tuple[HistoricalAccessFlag, ...]:
    if type(value) is not tuple:
        raise TypeError(f"{name} must be tuple")
    if not value:
        raise ValueError(f"{name} must not be empty")
    if any(type(item) is not HistoricalAccessFlag for item in value):
        raise TypeError(f"{name} items must be HistoricalAccessFlag")
    result = tuple(value)
    if len(set(result)) != len(result):
        raise ValueError(f"{name} contains duplicates")
    if (
        HistoricalAccessFlag.NO_KNOWN_PRIOR_ACCESS in result
        and len(result) != 1
    ):
        raise ValueError(
            "NO_KNOWN_PRIOR_ACCESS must be the sole historical flag"
        )
    return result


def _wire_flags(
    name: str,
    value: object,
) -> tuple[HistoricalAccessFlag, ...]:
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a JSON array")
    try:
        return tuple(HistoricalAccessFlag(item) for item in value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} contains an unknown flag") from error


@dataclass(frozen=True, slots=True)
class HistoricalAccessAuditRecordV1:
    task_id: str
    gamefile: str
    dataset_split: str
    first_known_access_date: str | None
    access_flags: tuple[HistoricalAccessFlag, ...]
    evidence_sources: tuple[str, ...]

    _KEYS: ClassVar[set[str]] = {
        "task_id",
        "gamefile",
        "dataset_split",
        "first_known_access_date",
        "access_flags",
        "evidence_sources",
    }

    def __post_init__(self) -> None:
        _text("task_id", self.task_id)
        _text("gamefile", self.gamefile)
        _text("dataset_split", self.dataset_split)
        _optional_date(
            "first_known_access_date",
            self.first_known_access_date,
        )
        _flags("access_flags", self.access_flags)
        _tuple_strings("evidence_sources", self.evidence_sources)

    def to_dict(self) -> dict[str, object]:
        return {
            "task_id": self.task_id,
            "gamefile": self.gamefile,
            "dataset_split": self.dataset_split,
            "first_known_access_date": self.first_known_access_date,
            "access_flags": [item.value for item in self.access_flags],
            "evidence_sources": list(self.evidence_sources),
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "HistoricalAccessAuditRecordV1":
        payload = _mapping(value)
        _expect_keys(payload, cls._KEYS)
        return cls(
            task_id=payload["task_id"],
            gamefile=payload["gamefile"],
            dataset_split=payload["dataset_split"],
            first_known_access_date=payload["first_known_access_date"],
            access_flags=_wire_flags(
                "access_flags",
                payload["access_flags"],
            ),
            evidence_sources=_wire_string_tuple(
                "evidence_sources",
                payload["evidence_sources"],
            ),
        )


@dataclass(frozen=True, slots=True)
class HistoricalAccessAuditV1:
    SCHEMA_ID: ClassVar[str] = (
        "DISTILLATION_HISTORICAL_ACCESS_AUDIT_V1"
    )
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    audit_id: str
    dataset_version: str
    record_count: int
    records: tuple[HistoricalAccessAuditRecordV1, ...]

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "audit_id",
        "dataset_version",
        "record_count",
        "records",
    }

    def __post_init__(self) -> None:
        if self.schema_id != self.SCHEMA_ID:
            raise ValueError("schema_id mismatch")
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("schema_version mismatch")
        _text("audit_id", self.audit_id)
        _text("dataset_version", self.dataset_version)
        if type(self.record_count) is not int:
            raise TypeError("record_count must be int")
        if type(self.records) is not tuple:
            raise TypeError("records must be tuple")
        if not self.records:
            raise ValueError("records must not be empty")
        if any(
            type(record) is not HistoricalAccessAuditRecordV1
            for record in self.records
        ):
            raise TypeError(
                "records items must be HistoricalAccessAuditRecordV1"
            )
        if self.record_count != len(self.records):
            raise ValueError("record_count must equal len(records)")
        task_ids = [record.task_id for record in self.records]
        gamefiles = [record.gamefile for record in self.records]
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("audit task_id values must be unique")
        if len(set(gamefiles)) != len(gamefiles):
            raise ValueError("audit gamefile values must be unique")
        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "audit_id": self.audit_id,
            "dataset_version": self.dataset_version,
            "record_count": self.record_count,
            "records": [record.to_dict() for record in self.records],
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> Self:
        payload = _mapping(value)
        _expect_keys(payload, cls._KEYS)
        records = payload["records"]
        if not isinstance(records, list):
            raise TypeError("records must be a JSON array")
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            audit_id=payload["audit_id"],
            dataset_version=payload["dataset_version"],
            record_count=payload["record_count"],
            records=tuple(
                HistoricalAccessAuditRecordV1.from_dict(item)
                for item in records
            ),
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> Self:
        return cls.from_dict(strict_json_loads(value))


@dataclass(frozen=True, slots=True)
class TaskAccessRecordV1:
    manifest_index: int
    task_id: str
    dataset_split: str
    task_type: str
    gamefile: str
    gamefile_sha1: str
    gamefile_sha256: str
    historical_access_flags: tuple[HistoricalAccessFlag, ...]
    access_class: DistillationAccessClass
    teacher_call_permitted: bool
    training_permitted: bool
    select_evaluation_permitted: bool
    confirmatory_permitted: bool
    provenance_sources: tuple[str, ...]

    _KEYS: ClassVar[set[str]] = {
        "manifest_index",
        "task_id",
        "dataset_split",
        "task_type",
        "gamefile",
        "gamefile_sha1",
        "gamefile_sha256",
        "historical_access_flags",
        "access_class",
        "teacher_call_permitted",
        "training_permitted",
        "select_evaluation_permitted",
        "confirmatory_permitted",
        "provenance_sources",
    }

    def __post_init__(self) -> None:
        if type(self.manifest_index) is not int:
            raise TypeError("manifest_index must be int")
        if self.manifest_index < 0:
            raise ValueError("manifest_index must be non-negative")
        for name in ("task_id", "dataset_split", "task_type", "gamefile"):
            _text(name, getattr(self, name))
        _sha1("gamefile_sha1", self.gamefile_sha1)
        require_lower_sha256("gamefile_sha256", self.gamefile_sha256)
        _flags("historical_access_flags", self.historical_access_flags)
        if type(self.access_class) is not DistillationAccessClass:
            raise TypeError(
                "access_class must be DistillationAccessClass"
            )
        for name in (
            "teacher_call_permitted",
            "training_permitted",
            "select_evaluation_permitted",
            "confirmatory_permitted",
        ):
            if type(getattr(self, name)) is not bool:
                raise TypeError(f"{name} must be bool")
        _tuple_strings("provenance_sources", self.provenance_sources)
        permissions = (
            self.teacher_call_permitted,
            self.training_permitted,
            self.select_evaluation_permitted,
            self.confirmatory_permitted,
        )
        if self.access_class is DistillationAccessClass.DEV_VISIBLE:
            if permissions != (True, True, False, False):
                raise ValueError(
                    "DEV_VISIBLE permission tuple must be "
                    "(true,true,false,false)"
                )
        elif (
            self.access_class
            is DistillationAccessClass.SELECT_SUMMARY_ONLY
        ):
            if permissions != (False, False, True, False):
                raise ValueError(
                    "SELECT_SUMMARY_ONLY permission tuple must be "
                    "(false,false,true,false)"
                )
        elif (
            self.access_class
            is DistillationAccessClass.CONFIRMATORY_SEALED
        ):
            if permissions != (False, False, False, True):
                raise ValueError(
                    "CONFIRMATORY_SEALED permission tuple must be "
                    "(false,false,false,true)"
                )
            disqualifying = {
                HistoricalAccessFlag.ACCESS_HISTORY_INCOMPLETE,
                HistoricalAccessFlag.TRAJECTORY_INSPECTED,
                HistoricalAccessFlag.USED_FOR_METHOD_DESIGN,
                HistoricalAccessFlag.SENT_TO_EXTERNAL_MODEL,
            }
            if disqualifying.intersection(
                self.historical_access_flags
            ):
                raise ValueError(
                    "CONFIRMATORY_SEALED rejects disqualifying "
                    "historical access"
                )
        elif self.confirmatory_permitted:
            raise ValueError(
                "HISTORICALLY_EXPOSED cannot be confirmatory"
            )

    def to_dict(self) -> dict[str, object]:
        return {
            "manifest_index": self.manifest_index,
            "task_id": self.task_id,
            "dataset_split": self.dataset_split,
            "task_type": self.task_type,
            "gamefile": self.gamefile,
            "gamefile_sha1": self.gamefile_sha1,
            "gamefile_sha256": self.gamefile_sha256,
            "historical_access_flags": [
                item.value for item in self.historical_access_flags
            ],
            "access_class": self.access_class.value,
            "teacher_call_permitted": self.teacher_call_permitted,
            "training_permitted": self.training_permitted,
            "select_evaluation_permitted": (
                self.select_evaluation_permitted
            ),
            "confirmatory_permitted": self.confirmatory_permitted,
            "provenance_sources": list(self.provenance_sources),
        }

    @classmethod
    def from_dict(cls, value: object) -> "TaskAccessRecordV1":
        payload = _mapping(value)
        _expect_keys(payload, cls._KEYS)
        try:
            access_class = DistillationAccessClass(
                payload["access_class"]
            )
        except (TypeError, ValueError) as error:
            raise ValueError("unknown access_class") from error
        return cls(
            manifest_index=payload["manifest_index"],
            task_id=payload["task_id"],
            dataset_split=payload["dataset_split"],
            task_type=payload["task_type"],
            gamefile=payload["gamefile"],
            gamefile_sha1=payload["gamefile_sha1"],
            gamefile_sha256=payload["gamefile_sha256"],
            historical_access_flags=_wire_flags(
                "historical_access_flags",
                payload["historical_access_flags"],
            ),
            access_class=access_class,
            teacher_call_permitted=payload["teacher_call_permitted"],
            training_permitted=payload["training_permitted"],
            select_evaluation_permitted=payload[
                "select_evaluation_permitted"
            ],
            confirmatory_permitted=payload[
                "confirmatory_permitted"
            ],
            provenance_sources=_wire_string_tuple(
                "provenance_sources",
                payload["provenance_sources"],
            ),
        )


@dataclass(frozen=True, slots=True)
class TaskAccessManifestV1:
    SCHEMA_ID: ClassVar[str] = (
        "DISTILLATION_TASK_ACCESS_MANIFEST_V1"
    )
    SCHEMA_VERSION: ClassVar[int] = 1

    schema_id: str
    schema_version: int
    manifest_id: str
    dataset_version: str
    historical_access_audit_sha256: str
    record_count: int
    records: tuple[TaskAccessRecordV1, ...]

    _KEYS: ClassVar[set[str]] = {
        "schema_id",
        "schema_version",
        "manifest_id",
        "dataset_version",
        "historical_access_audit_sha256",
        "record_count",
        "records",
    }

    def __post_init__(self) -> None:
        if self.schema_id != self.SCHEMA_ID:
            raise ValueError("schema_id mismatch")
        if self.schema_version != self.SCHEMA_VERSION:
            raise ValueError("schema_version mismatch")
        _text("manifest_id", self.manifest_id)
        _text("dataset_version", self.dataset_version)
        require_lower_sha256(
            "historical_access_audit_sha256",
            self.historical_access_audit_sha256,
        )
        if type(self.record_count) is not int:
            raise TypeError("record_count must be int")
        if type(self.records) is not tuple:
            raise TypeError("records must be tuple")
        if not self.records:
            raise ValueError("records must not be empty")
        if any(
            type(record) is not TaskAccessRecordV1
            for record in self.records
        ):
            raise TypeError("records items must be TaskAccessRecordV1")
        if self.record_count != len(self.records):
            raise ValueError("record_count must equal len(records)")
        indices = [record.manifest_index for record in self.records]
        if indices != list(range(self.record_count)):
            raise ValueError(
                "manifest_index must be contiguous in record order"
            )
        task_ids = [record.task_id for record in self.records]
        gamefiles = [record.gamefile for record in self.records]
        if len(set(task_ids)) != len(task_ids):
            raise ValueError("task_id values must be unique")
        if len(set(gamefiles)) != len(gamefiles):
            raise ValueError("gamefile values must be unique")
        validate_payload_against_schema(
            schema_id=self.SCHEMA_ID,
            payload=self.to_dict(),
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "manifest_id": self.manifest_id,
            "dataset_version": self.dataset_version,
            "historical_access_audit_sha256": (
                self.historical_access_audit_sha256
            ),
            "record_count": self.record_count,
            "records": [record.to_dict() for record in self.records],
        }

    def to_json(self) -> str:
        return canonical_json_text(self.to_dict())

    @classmethod
    def from_dict(cls, value: object) -> Self:
        payload = _mapping(value)
        _expect_keys(payload, cls._KEYS)
        records = payload["records"]
        if not isinstance(records, list):
            raise TypeError("records must be a JSON array")
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            manifest_id=payload["manifest_id"],
            dataset_version=payload["dataset_version"],
            historical_access_audit_sha256=payload[
                "historical_access_audit_sha256"
            ],
            record_count=payload["record_count"],
            records=tuple(
                TaskAccessRecordV1.from_dict(item)
                for item in records
            ),
        )

    @classmethod
    def from_json(cls, value: str | bytes) -> Self:
        return cls.from_dict(strict_json_loads(value))
