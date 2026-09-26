"""Immutable calibrated DEV descriptive snapshot for Failure Memory Package B."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil
from typing import ClassVar

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.matched_raw_view import (
    FM1MatchedRawEpisodicViewV1,
)
from pchsi.memory.policy_projection import (
    FailureMemoryPolicyProjectionV1,
)
from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
)
from pchsi.memory.projection_common import (
    ProjectionBuildDispositionV1,
    ProjectionClassV1,
)
from pchsi.memory.retrieval_key import (
    MemoryRetrievalKeyV1,
)
from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
)


SNAPSHOT_SCHEMA_V2 = "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V2"
SNAPSHOT_DOMAIN_V2 = "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_ID_V2"


def _regular(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} must be regular non-symlink file")
    return path


def _dir(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{label} must be existing non-symlink directory")
    return path


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _fsync_directory(path: Path) -> None:
    fd = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


@dataclass(frozen=True, slots=True)
class CalibratedSnapshotMemberV2:
    memory_lineage_id: str
    record_version: int
    governed_record_sha256: str
    retrieval_key_sha256: str
    fm1_sha256: str
    fm1_build_disposition: str
    fm2_sha256: str
    fm2_build_disposition: str
    relative_directory: str

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "memory_lineage_id",
            "record_version",
            "governed_record_sha256",
            "retrieval_key_sha256",
            "fm1_sha256",
            "fm1_build_disposition",
            "fm2_sha256",
            "fm2_build_disposition",
            "relative_directory",
        }
    )

    def __post_init__(self) -> None:
        require_lower_sha256(
            "memory_lineage_id",
            self.memory_lineage_id,
        )
        if type(self.record_version) is not int or self.record_version < 1:
            raise ValueError("record_version must be positive int")
        for name in (
            "governed_record_sha256",
            "retrieval_key_sha256",
            "fm1_sha256",
            "fm2_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        ProjectionBuildDispositionV1(
            self.fm1_build_disposition
        )
        if (
            ProjectionBuildDispositionV1(
                self.fm2_build_disposition
            )
            is not ProjectionBuildDispositionV1.ELIGIBLE
        ):
            raise ValueError("active descriptive snapshot requires FM2 ELIGIBLE")
        if (
            not isinstance(self.relative_directory, str)
            or not self.relative_directory
            or Path(self.relative_directory).is_absolute()
            or ".." in Path(self.relative_directory).parts
        ):
            raise ValueError("relative_directory invalid")

    def to_dict(self) -> dict[str, object]:
        return {
            "memory_lineage_id": self.memory_lineage_id,
            "record_version": self.record_version,
            "governed_record_sha256": self.governed_record_sha256,
            "retrieval_key_sha256": self.retrieval_key_sha256,
            "fm1_sha256": self.fm1_sha256,
            "fm1_build_disposition": self.fm1_build_disposition,
            "fm2_sha256": self.fm2_sha256,
            "fm2_build_disposition": self.fm2_build_disposition,
            "relative_directory": self.relative_directory,
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "CalibratedSnapshotMemberV2":
        if not isinstance(value, dict) or frozenset(value) != cls._KEYS:
            raise ValueError("snapshot V2 member fields mismatch")
        return cls(**value)


@dataclass(frozen=True, slots=True)
class MemoryDevDescriptiveSnapshotV2:
    schema_id: str
    schema_version: int
    package_a_sealed_head: str
    historical_package_a_snapshot_sha256: str
    token_budget_contract_sha256: str
    source_materialization_manifest_sha256: str
    access_policy: str
    effect_authority: str
    previous_package_a_exposure: str
    tokenizer_id: str
    tokenizer_revision: str
    single_record_hard_ceiling: int
    library_total_hard_ceiling: int
    max_record_count: int
    members: tuple[CalibratedSnapshotMemberV2, ...]
    snapshot_sha256: str | None = None

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "package_a_sealed_head",
            "historical_package_a_snapshot_sha256",
            "token_budget_contract_sha256",
            "source_materialization_manifest_sha256",
            "access_policy",
            "effect_authority",
            "previous_package_a_exposure",
            "tokenizer_id",
            "tokenizer_revision",
            "single_record_hard_ceiling",
            "library_total_hard_ceiling",
            "max_record_count",
            "members",
            "snapshot_sha256",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != SNAPSHOT_SCHEMA_V2 or self.schema_version != 2:
            raise ValueError("snapshot V2 schema mismatch")
        if (
            not isinstance(self.package_a_sealed_head, str)
            or len(self.package_a_sealed_head) != 40
            or any(
                ch not in "0123456789abcdef"
                for ch in self.package_a_sealed_head
            )
        ):
            raise ValueError("package_a_sealed_head invalid")
        for name in (
            "historical_package_a_snapshot_sha256",
            "token_budget_contract_sha256",
            "source_materialization_manifest_sha256",
        ):
            require_lower_sha256(name, getattr(self, name))
        if self.access_policy != "SAME_TASK_DEV_ALLOWED":
            raise ValueError("snapshot V2 access policy mismatch")
        if self.effect_authority != "UNTESTED":
            raise ValueError("snapshot V2 effect authority mismatch")
        if self.previous_package_a_exposure != "NOT_EXPOSED_PACKAGE_A":
            raise ValueError("snapshot V2 exposure authority mismatch")
        if (
            not isinstance(self.tokenizer_id, str)
            or not self.tokenizer_id
            or not isinstance(self.tokenizer_revision, str)
            or not self.tokenizer_revision
        ):
            raise ValueError("tokenizer identity invalid")
        if (
            type(self.single_record_hard_ceiling) is not int
            or self.single_record_hard_ceiling <= 0
        ):
            raise ValueError("single_record_hard_ceiling invalid")
        if (
            type(self.library_total_hard_ceiling) is not int
            or self.library_total_hard_ceiling <= 0
        ):
            raise ValueError("library_total_hard_ceiling invalid")
        if self.max_record_count != 3:
            raise ValueError("snapshot V2 max record count must equal 3")
        if type(self.members) is not tuple or not self.members:
            raise ValueError("snapshot V2 members must be nonempty tuple")
        if any(
            not isinstance(item, CalibratedSnapshotMemberV2)
            for item in self.members
        ):
            raise TypeError("snapshot V2 member type mismatch")

        order = tuple(
            (item.memory_lineage_id, item.record_version)
            for item in self.members
        )
        if order != tuple(sorted(order)) or len(order) != len(set(order)):
            raise ValueError("snapshot V2 members must be unique deterministic order")

        expected = sha256_bytes(
            SNAPSHOT_DOMAIN_V2.encode("utf-8")
            + b"\0"
            + canonical_json_bytes(
                self._payload_without_sha()
            )
        )
        if self.snapshot_sha256 is None:
            object.__setattr__(
                self,
                "snapshot_sha256",
                expected,
            )
        elif self.snapshot_sha256 != expected:
            raise ValueError("snapshot V2 SHA mismatch")

    def _payload_without_sha(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "package_a_sealed_head": self.package_a_sealed_head,
            "historical_package_a_snapshot_sha256": (
                self.historical_package_a_snapshot_sha256
            ),
            "token_budget_contract_sha256": (
                self.token_budget_contract_sha256
            ),
            "source_materialization_manifest_sha256": (
                self.source_materialization_manifest_sha256
            ),
            "access_policy": self.access_policy,
            "effect_authority": self.effect_authority,
            "previous_package_a_exposure": (
                self.previous_package_a_exposure
            ),
            "tokenizer_id": self.tokenizer_id,
            "tokenizer_revision": self.tokenizer_revision,
            "single_record_hard_ceiling": (
                self.single_record_hard_ceiling
            ),
            "library_total_hard_ceiling": (
                self.library_total_hard_ceiling
            ),
            "max_record_count": self.max_record_count,
            "members": [
                item.to_dict()
                for item in self.members
            ],
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self._payload_without_sha(),
            "snapshot_sha256": self.snapshot_sha256,
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.to_dict())

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryDevDescriptiveSnapshotV2":
        if not isinstance(value, dict) or frozenset(value) != cls._KEYS:
            raise ValueError("snapshot V2 fields mismatch")
        raw_members = value["members"]
        if not isinstance(raw_members, list):
            raise TypeError("snapshot V2 members must be array")
        return cls(
            schema_id=value["schema_id"],
            schema_version=value["schema_version"],
            package_a_sealed_head=value["package_a_sealed_head"],
            historical_package_a_snapshot_sha256=value[
                "historical_package_a_snapshot_sha256"
            ],
            token_budget_contract_sha256=value[
                "token_budget_contract_sha256"
            ],
            source_materialization_manifest_sha256=value[
                "source_materialization_manifest_sha256"
            ],
            access_policy=value["access_policy"],
            effect_authority=value["effect_authority"],
            previous_package_a_exposure=value[
                "previous_package_a_exposure"
            ],
            tokenizer_id=value["tokenizer_id"],
            tokenizer_revision=value["tokenizer_revision"],
            single_record_hard_ceiling=value[
                "single_record_hard_ceiling"
            ],
            library_total_hard_ceiling=value[
                "library_total_hard_ceiling"
            ],
            max_record_count=value["max_record_count"],
            members=tuple(
                CalibratedSnapshotMemberV2.from_dict(item)
                for item in raw_members
            ),
            snapshot_sha256=value["snapshot_sha256"],
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "MemoryDevDescriptiveSnapshotV2":
        return cls.from_dict(strict_json_loads(value))


def build_calibrated_snapshot_v2(
    *,
    package_a_sealed_head: str,
    historical_package_a_snapshot_sha256: str,
    token_budget_contract: FailureMemoryTokenBudgetContractV1,
    source_materialization_manifest_sha256: str,
    member_artifacts: tuple[
        tuple[
            bytes,
            bytes,
            bytes,
            bytes,
        ],
        ...,
    ],
):
    if type(member_artifacts) is not tuple or not member_artifacts:
        raise ValueError("member_artifacts must be nonempty tuple")

    values = []

    for (
        record_bytes,
        key_bytes,
        fm1_bytes,
        fm2_bytes,
    ) in member_artifacts:
        record = ProceduralFailureMemoryRecordV1.from_json(
            record_bytes
        )
        key = MemoryRetrievalKeyV1.from_json(
            key_bytes
        )
        fm1 = FM1MatchedRawEpisodicViewV1.from_json(
            fm1_bytes
        )
        fm2 = FailureMemoryPolicyProjectionV1.from_json(
            fm2_bytes
        )

        if (
            fm2.projection_class
            is not ProjectionClassV1.FM2
            or fm2.build_disposition
            is not ProjectionBuildDispositionV1.ELIGIBLE
        ):
            raise ValueError("snapshot V2 requires eligible FM2")

        for binding in (
            key.record_binding,
            fm1.record_binding,
            fm2.record_binding,
        ):
            if (
                binding.memory_lineage_id
                != record.memory_lineage_id
                or binding.record_version
                != record.record_version
                or binding.canonical_record_sha256
                != record.canonical_record_sha256
            ):
                raise ValueError("snapshot V2 record binding mismatch")

        relative = (
            f"members/{record.memory_lineage_id}"
            f".v{record.record_version}"
        )
        member = CalibratedSnapshotMemberV2(
            memory_lineage_id=record.memory_lineage_id,
            record_version=record.record_version,
            governed_record_sha256=sha256_bytes(
                record_bytes
            ),
            retrieval_key_sha256=sha256_bytes(
                key_bytes
            ),
            fm1_sha256=sha256_bytes(fm1_bytes),
            fm1_build_disposition=(
                fm1.build_disposition.value
            ),
            fm2_sha256=sha256_bytes(fm2_bytes),
            fm2_build_disposition=(
                fm2.build_disposition.value
            ),
            relative_directory=relative,
        )
        files = {
            "governed_record.json": record_bytes,
            "retrieval_key.json": key_bytes,
            "fm1.json": fm1_bytes,
            "fm2.json": fm2_bytes,
        }
        values.append((member, files))

    values.sort(
        key=lambda item: (
            item[0].memory_lineage_id,
            item[0].record_version,
        )
    )

    snapshot = MemoryDevDescriptiveSnapshotV2(
        schema_id=SNAPSHOT_SCHEMA_V2,
        schema_version=2,
        package_a_sealed_head=package_a_sealed_head,
        historical_package_a_snapshot_sha256=(
            historical_package_a_snapshot_sha256
        ),
        token_budget_contract_sha256=(
            token_budget_contract.contract_sha256
        ),
        source_materialization_manifest_sha256=(
            source_materialization_manifest_sha256
        ),
        access_policy="SAME_TASK_DEV_ALLOWED",
        effect_authority="UNTESTED",
        previous_package_a_exposure="NOT_EXPOSED_PACKAGE_A",
        tokenizer_id=token_budget_contract.tokenizer_id,
        tokenizer_revision=token_budget_contract.tokenizer_revision,
        single_record_hard_ceiling=(
            token_budget_contract.single_record_hard_ceiling
        ),
        library_total_hard_ceiling=(
            token_budget_contract.library_total_hard_ceiling
        ),
        max_record_count=token_budget_contract.max_record_count,
        members=tuple(item[0] for item in values),
        snapshot_sha256=None,
    )
    return snapshot, {
        item[0].relative_directory: item[1]
        for item in values
    }


def _files_manifest(
    *,
    root: Path,
    snapshot_sha256: str,
) -> bytes:
    rows = []
    for path in sorted(
        item
        for item in root.rglob("*")
        if item.is_file()
        and item.name
        not in {
            "snapshot_files.json",
            "snapshot_files.sha256",
        }
    ):
        rows.append(
            {
                "relative_path": path.relative_to(root).as_posix(),
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )
    return canonical_json_bytes(
        {
            "schema_id": (
                "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_FILES_V2"
            ),
            "schema_version": 2,
            "snapshot_sha256": snapshot_sha256,
            "files": rows,
        }
    )


def publish_calibrated_snapshot_v2(
    *,
    output_root: Path,
    snapshot: MemoryDevDescriptiveSnapshotV2,
    member_files: dict[str, dict[str, bytes]],
) -> Path:
    root = _dir(output_root, "snapshot V2 output root")
    final = root / snapshot.snapshot_sha256
    temp = root / f".{snapshot.snapshot_sha256}.tmp"

    if final.exists() or final.is_symlink():
        raise FileExistsError(str(final))
    if temp.exists() or temp.is_symlink():
        raise FileExistsError(str(temp))

    temp.mkdir(mode=0o700)
    try:
        for member in snapshot.members:
            target = temp / member.relative_directory
            target.mkdir(
                parents=True,
                mode=0o700,
            )
            files = member_files.get(
                member.relative_directory
            )
            if files is None:
                raise ValueError("snapshot V2 member files missing")
            for name, data in sorted(files.items()):
                _write_once(target / name, data)
            _fsync_directory(target)
            _fsync_directory(target.parent)

        _write_once(
            temp / "snapshot.json",
            snapshot.canonical_bytes(),
        )
        manifest = _files_manifest(
            root=temp,
            snapshot_sha256=snapshot.snapshot_sha256,
        )
        _write_once(
            temp / "snapshot_files.json",
            manifest,
        )
        _write_once(
            temp / "snapshot_files.sha256",
            (
                sha256_bytes(manifest)
                + "\n"
            ).encode("ascii"),
        )
        _fsync_directory(temp)
        os.replace(temp, final)
        _fsync_directory(root)
    except BaseException:
        shutil.rmtree(
            temp,
            ignore_errors=True,
        )
        raise

    audit_calibrated_snapshot_v2(
        snapshot_directory=final,
        expected_snapshot_sha256=(
            snapshot.snapshot_sha256
        ),
    )
    return final


def audit_calibrated_snapshot_v2(
    *,
    snapshot_directory: Path,
    expected_snapshot_sha256: str,
) -> MemoryDevDescriptiveSnapshotV2:
    require_lower_sha256(
        "expected_snapshot_sha256",
        expected_snapshot_sha256,
    )
    root = _dir(
        snapshot_directory,
        "snapshot V2 directory",
    )
    if root.name != expected_snapshot_sha256:
        raise ValueError("snapshot V2 directory identity mismatch")

    snapshot_bytes = _regular(
        root / "snapshot.json",
        "snapshot V2 JSON",
    ).read_bytes()
    snapshot = MemoryDevDescriptiveSnapshotV2.from_json(
        snapshot_bytes
    )
    if snapshot.canonical_bytes() != snapshot_bytes:
        raise ValueError("snapshot V2 JSON is not canonical")
    if snapshot.snapshot_sha256 != expected_snapshot_sha256:
        raise ValueError("snapshot V2 SHA mismatch")

    manifest_bytes = _regular(
        root / "snapshot_files.json",
        "snapshot V2 files manifest",
    ).read_bytes()
    sidecar = _regular(
        root / "snapshot_files.sha256",
        "snapshot V2 files sidecar",
    ).read_text(encoding="ascii").strip()

    if sha256_bytes(manifest_bytes) != sidecar:
        raise ValueError("snapshot V2 file-manifest sidecar mismatch")

    manifest = strict_json_loads(manifest_bytes)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema_id")
        != "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_FILES_V2"
        or manifest.get("schema_version") != 2
        or manifest.get("snapshot_sha256")
        != expected_snapshot_sha256
    ):
        raise ValueError("snapshot V2 files manifest invalid")
    if canonical_json_bytes(manifest) != manifest_bytes:
        raise ValueError("snapshot V2 files manifest not canonical")

    registered = {
        "snapshot_files.json",
        "snapshot_files.sha256",
    }
    rows = manifest.get("files")
    if not isinstance(rows, list):
        raise TypeError("snapshot V2 files must be array")

    for row in rows:
        if not isinstance(row, dict) or set(row) != {
            "relative_path",
            "sha256",
            "size",
        }:
            raise ValueError("snapshot V2 file row invalid")
        relative = Path(row["relative_path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("snapshot V2 relative path invalid")
        path = _regular(
            root / relative,
            "snapshot V2 registered file",
        )
        require_lower_sha256(
            "snapshot V2 file sha",
            row["sha256"],
        )
        if sha256_file(path) != row["sha256"]:
            raise ValueError("snapshot V2 file SHA mismatch")
        if path.stat().st_size != row["size"]:
            raise ValueError("snapshot V2 file size mismatch")
        registered.add(relative.as_posix())

    observed = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if observed != registered:
        raise ValueError("snapshot V2 file census mismatch")

    if any(
        path.name.startswith("fm3")
        for path in root.rglob("*")
        if path.is_file()
    ):
        raise ValueError("snapshot V2 must not contain FM3")

    for member in snapshot.members:
        member_root = _dir(
            root / member.relative_directory,
            "snapshot V2 member",
        )
        expected_files = {
            "governed_record.json",
            "retrieval_key.json",
            "fm1.json",
            "fm2.json",
        }
        observed_files = {
            path.name
            for path in member_root.iterdir()
            if path.is_file()
        }
        if observed_files != expected_files:
            raise ValueError("snapshot V2 member file census mismatch")

        checks = {
            "governed_record.json": member.governed_record_sha256,
            "retrieval_key.json": member.retrieval_key_sha256,
            "fm1.json": member.fm1_sha256,
            "fm2.json": member.fm2_sha256,
        }
        for name, expected in checks.items():
            if sha256_file(member_root / name) != expected:
                raise ValueError(
                    "snapshot V2 member hash mismatch:"
                    + name
                )

        fm1 = FM1MatchedRawEpisodicViewV1.from_json(
            (member_root / "fm1.json").read_bytes()
        )
        fm2 = FailureMemoryPolicyProjectionV1.from_json(
            (member_root / "fm2.json").read_bytes()
        )
        if fm1.build_disposition.value != member.fm1_build_disposition:
            raise ValueError("snapshot V2 FM1 disposition mismatch")
        if fm2.build_disposition.value != member.fm2_build_disposition:
            raise ValueError("snapshot V2 FM2 disposition mismatch")

    return snapshot
