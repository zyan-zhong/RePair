from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import shutil

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.candidate_materialization import (
    audit_candidate_directory_v1,
)
from pchsi.memory.lifecycle_relations import (
    EffectEvidenceScopeV1,
    EffectStatusV1,
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


def _regular(
    path: Path,
    label: str,
) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"{label} invalid")
    return path


def _dir(
    path: Path,
    label: str,
) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_dir():
        raise ValueError(f"{label} invalid")
    return path


def _write_all(
    fd: int,
    data: bytes,
) -> None:
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise OSError(
                "os.write made no progress"
            )
        view = view[count:]


def _write_once(
    path: Path,
    data: bytes,
) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    fd = os.open(
        path,
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL,
        0o600,
    )
    try:
        _write_all(fd, data)
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


def _exact(
    value: object,
    expected: set[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = set(value)
    if observed != expected:
        raise ValueError(
            f"{label} fields mismatch: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


@dataclass(frozen=True, slots=True)
class MemoryDevDescriptiveSnapshotMemberV1:
    memory_lineage_id: str
    record_version: int
    governed_record_sha256: str
    retrieval_key_sha256: str
    fm1_sha256: str
    fm2_sha256: str
    relative_directory: str

    def __post_init__(self) -> None:
        for name in (
            "memory_lineage_id",
            "governed_record_sha256",
            "retrieval_key_sha256",
            "fm1_sha256",
            "fm2_sha256",
        ):
            require_lower_sha256(
                name,
                getattr(self, name),
            )
        if (
            type(self.record_version) is not int
            or self.record_version < 1
        ):
            raise ValueError(
                "record_version invalid"
            )
        relative = Path(
            self.relative_directory
        )
        if (
            relative.is_absolute()
            or ".." in relative.parts
        ):
            raise ValueError(
                "relative_directory invalid"
            )

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            "memory_lineage_id": (
                self.memory_lineage_id
            ),
            "record_version": (
                self.record_version
            ),
            "governed_record_sha256": (
                self.governed_record_sha256
            ),
            "retrieval_key_sha256": (
                self.retrieval_key_sha256
            ),
            "fm1_sha256": self.fm1_sha256,
            "fm2_sha256": self.fm2_sha256,
            "relative_directory": (
                self.relative_directory
            ),
        }

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryDevDescriptiveSnapshotMemberV1":
        payload = _exact(
            value,
            {
                "memory_lineage_id",
                "record_version",
                "governed_record_sha256",
                "retrieval_key_sha256",
                "fm1_sha256",
                "fm2_sha256",
                "relative_directory",
            },
            "snapshot member",
        )
        return cls(**payload)


@dataclass(frozen=True, slots=True)
class MemoryDevDescriptiveSnapshotV1:
    source_materialization_manifest_sha256: str
    tokenizer_id: str
    tokenizer_revision: str
    members: tuple[
        MemoryDevDescriptiveSnapshotMemberV1,
        ...,
    ]
    snapshot_sha256: str | None = None

    def __post_init__(self) -> None:
        require_lower_sha256(
            "source_materialization_manifest_sha256",
            self.source_materialization_manifest_sha256,
        )
        if (
            not isinstance(self.tokenizer_id, str)
            or not self.tokenizer_id
        ):
            raise ValueError(
                "tokenizer_id invalid"
            )
        if (
            not isinstance(
                self.tokenizer_revision,
                str,
            )
            or not self.tokenizer_revision
        ):
            raise ValueError(
                "tokenizer_revision invalid"
            )
        if (
            type(self.members) is not tuple
            or not self.members
        ):
            raise ValueError(
                "snapshot requires members"
            )
        order = tuple(
            (
                item.memory_lineage_id,
                item.record_version,
            )
            for item in self.members
        )
        if (
            order != tuple(sorted(order))
            or len(order) != len(set(order))
        ):
            raise ValueError(
                "snapshot member order/uniqueness invalid"
            )
        expected = sha256_bytes(
            b"MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1"
            + b"\0"
            + canonical_json_bytes(
                self._payload()
            )
        )
        if self.snapshot_sha256 is None:
            object.__setattr__(
                self,
                "snapshot_sha256",
                expected,
            )
        elif self.snapshot_sha256 != expected:
            raise ValueError(
                "snapshot_sha256 mismatch"
            )

    def _payload(
        self,
    ) -> dict[str, object]:
        return {
            "schema_id": (
                "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1"
            ),
            "schema_version": 1,
            "source_materialization_manifest_sha256": (
                self.source_materialization_manifest_sha256
            ),
            "access_policy": (
                "SAME_TASK_DEV_ALLOWED"
            ),
            "effect_authority": "UNTESTED",
            "tokenizer_id": self.tokenizer_id,
            "tokenizer_revision": (
                self.tokenizer_revision
            ),
            "members": [
                item.to_dict()
                for item in self.members
            ],
        }

    def to_dict(
        self,
    ) -> dict[str, object]:
        return {
            **self._payload(),
            "snapshot_sha256": (
                self.snapshot_sha256
            ),
        }

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(
            self.to_dict()
        )

    @classmethod
    def from_dict(
        cls,
        value: object,
    ) -> "MemoryDevDescriptiveSnapshotV1":
        payload = _exact(
            value,
            {
                "schema_id",
                "schema_version",
                "source_materialization_manifest_sha256",
                "access_policy",
                "effect_authority",
                "tokenizer_id",
                "tokenizer_revision",
                "members",
                "snapshot_sha256",
            },
            "DEV descriptive snapshot",
        )
        if (
            payload["schema_id"]
            != "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_V1"
            or payload["schema_version"] != 1
        ):
            raise ValueError(
                "snapshot schema mismatch"
            )
        if (
            payload["access_policy"]
            != "SAME_TASK_DEV_ALLOWED"
        ):
            raise ValueError(
                "snapshot access policy mismatch"
            )
        if (
            payload["effect_authority"]
            != "UNTESTED"
        ):
            raise ValueError(
                "snapshot effect authority mismatch"
            )
        raw_members = payload["members"]
        if not isinstance(raw_members, list):
            raise TypeError(
                "snapshot members must be array"
            )
        return cls(
            source_materialization_manifest_sha256=payload[
                "source_materialization_manifest_sha256"
            ],
            tokenizer_id=payload[
                "tokenizer_id"
            ],
            tokenizer_revision=payload[
                "tokenizer_revision"
            ],
            members=tuple(
                MemoryDevDescriptiveSnapshotMemberV1.from_dict(
                    item
                )
                for item in raw_members
            ),
            snapshot_sha256=payload[
                "snapshot_sha256"
            ],
        )

    @classmethod
    def from_json(
        cls,
        value: str | bytes,
    ) -> "MemoryDevDescriptiveSnapshotV1":
        return cls.from_dict(
            strict_json_loads(value)
        )


def _load_member(
    candidate_dir: Path,
):
    audit_candidate_directory_v1(
        candidate_dir
    )

    record_bytes = _regular(
        candidate_dir / "governed_record.json",
        "governed record",
    ).read_bytes()
    record = (
        ProceduralFailureMemoryRecordV1
        .from_json(record_bytes)
    )

    if (
        record.governance_state.effect_status
        is not EffectStatusV1.UNTESTED
        or record.governance_state
        .effect_evidence_scope
        is not EffectEvidenceScopeV1.UNTESTED
    ):
        raise ValueError(
            "Package A snapshot member "
            "has effect authority"
        )

    key_bytes = _regular(
        candidate_dir / "retrieval_key.json",
        "retrieval key",
    ).read_bytes()
    key = MemoryRetrievalKeyV1.from_json(
        key_bytes
    )

    fm1_bytes = _regular(
        candidate_dir / "fm1.json",
        "fm1",
    ).read_bytes()
    fm1 = FM1MatchedRawEpisodicViewV1.from_json(
        fm1_bytes
    )

    fm2_bytes = _regular(
        candidate_dir / "fm2.json",
        "fm2",
    ).read_bytes()
    fm2 = (
        FailureMemoryPolicyProjectionV1
        .from_json(fm2_bytes)
    )

    allowed_fm1_dispositions = {
        ProjectionBuildDispositionV1.ELIGIBLE,
        (
            ProjectionBuildDispositionV1
            .PROJECTION_INELIGIBLE_TOKEN_BUDGET
        ),
    }
    if (
        fm1.build_disposition
        not in allowed_fm1_dispositions
    ):
        raise ValueError(
            "FM1 disposition blocks Package A snapshot"
        )
    if (
        fm2.build_disposition
        is not ProjectionBuildDispositionV1.ELIGIBLE
    ):
        raise ValueError("FM2 not eligible")
    if (
        fm2.projection_class
        is not ProjectionClassV1.FM2
    ):
        raise ValueError(
            "structured snapshot projection "
            "must be FM2"
        )

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
            raise ValueError(
                "snapshot member record binding mismatch"
            )

    relative_directory = (
        f"members/{record.memory_lineage_id}"
        f".v{record.record_version}"
    )

    member = (
        MemoryDevDescriptiveSnapshotMemberV1(
            memory_lineage_id=(
                record.memory_lineage_id
            ),
            record_version=(
                record.record_version
            ),
            governed_record_sha256=(
                sha256_bytes(record_bytes)
            ),
            retrieval_key_sha256=(
                sha256_bytes(key_bytes)
            ),
            fm1_sha256=(
                sha256_bytes(fm1_bytes)
            ),
            fm2_sha256=(
                sha256_bytes(fm2_bytes)
            ),
            relative_directory=(
                relative_directory
            ),
        )
    )

    files = {
        "governed_record.json": record_bytes,
        "retrieval_key.json": key_bytes,
        "fm1.json": fm1_bytes,
        "fm2.json": fm2_bytes,
    }
    return member, files


def build_memory_dev_descriptive_snapshot_v1(
    *,
    candidate_directories: tuple[Path, ...],
    source_materialization_manifest_sha256: str,
    tokenizer_id: str,
    tokenizer_revision: str,
):
    if (
        type(candidate_directories)
        is not tuple
        or not candidate_directories
    ):
        raise ValueError(
            "candidate_directories "
            "must be nonempty tuple"
        )

    values = tuple(
        _load_member(Path(path))
        for path in candidate_directories
    )
    values = tuple(
        sorted(
            values,
            key=lambda item: (
                item[0].memory_lineage_id,
                item[0].record_version,
            ),
        )
    )
    snapshot = (
        MemoryDevDescriptiveSnapshotV1(
            source_materialization_manifest_sha256=(
                source_materialization_manifest_sha256
            ),
            tokenizer_id=tokenizer_id,
            tokenizer_revision=(
                tokenizer_revision
            ),
            members=tuple(
                item[0]
                for item in values
            ),
        )
    )
    return snapshot, {
        item[0].relative_directory: item[1]
        for item in values
    }


def _snapshot_files_manifest(
    *,
    snapshot_root: Path,
    snapshot_sha256: str,
) -> bytes:
    files = []
    for path in sorted(
        item
        for item in snapshot_root.rglob("*")
        if item.is_file()
        and item.name
        not in {
            "snapshot_files.json",
            "snapshot_files.sha256",
        }
    ):
        relative = path.relative_to(
            snapshot_root
        ).as_posix()
        files.append(
            {
                "relative_path": relative,
                "sha256": sha256_file(path),
                "size": path.stat().st_size,
            }
        )

    return canonical_json_bytes(
        {
            "schema_id": (
                "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_FILES_V1"
            ),
            "schema_version": 1,
            "snapshot_sha256": (
                snapshot_sha256
            ),
            "files": files,
        }
    )


def publish_memory_dev_descriptive_snapshot_v1(
    *,
    output_root: Path,
    snapshot: MemoryDevDescriptiveSnapshotV1,
    member_files: dict[
        str,
        dict[str, bytes],
    ],
):
    root = _dir(
        output_root,
        "snapshot output root",
    )
    final = root / snapshot.snapshot_sha256
    temp = root / (
        f".{snapshot.snapshot_sha256}.tmp"
    )

    if final.exists() or final.is_symlink():
        raise FileExistsError(str(final))
    if temp.exists() or temp.is_symlink():
        raise FileExistsError(str(temp))

    temp.mkdir(mode=0o700)
    try:
        for member in snapshot.members:
            target = (
                temp
                / member.relative_directory
            )
            target.mkdir(
                parents=True,
                mode=0o700,
            )
            files = member_files.get(
                member.relative_directory
            )
            if files is None:
                raise ValueError(
                    "member_files missing "
                    + member.relative_directory
                )
            for name, data in sorted(
                files.items()
            ):
                _write_once(
                    target / name,
                    data,
                )
            _fsync_directory(target)
            _fsync_directory(target.parent)

        _write_once(
            temp / "snapshot.json",
            snapshot.canonical_bytes(),
        )

        manifest = _snapshot_files_manifest(
            snapshot_root=temp,
            snapshot_sha256=(
                snapshot.snapshot_sha256
            ),
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

    audit_memory_dev_descriptive_snapshot_v1(
        snapshot_directory=final,
        expected_snapshot_sha256=(
            snapshot.snapshot_sha256
        ),
    )
    return final


def audit_memory_dev_descriptive_snapshot_v1(
    *,
    snapshot_directory: Path,
    expected_snapshot_sha256: str,
) -> MemoryDevDescriptiveSnapshotV1:
    require_lower_sha256(
        "expected_snapshot_sha256",
        expected_snapshot_sha256,
    )
    root = _dir(
        snapshot_directory,
        "snapshot directory",
    )
    if root.name != expected_snapshot_sha256:
        raise ValueError(
            "snapshot directory identity mismatch"
        )

    snapshot_path = _regular(
        root / "snapshot.json",
        "snapshot JSON",
    )
    snapshot_bytes = (
        snapshot_path.read_bytes()
    )
    snapshot = (
        MemoryDevDescriptiveSnapshotV1
        .from_json(snapshot_bytes)
    )
    if (
        snapshot.canonical_bytes()
        != snapshot_bytes
    ):
        raise ValueError(
            "snapshot JSON is not canonical"
        )
    if (
        snapshot.snapshot_sha256
        != expected_snapshot_sha256
    ):
        raise ValueError(
            "snapshot SHA identity mismatch"
        )

    manifest_path = _regular(
        root / "snapshot_files.json",
        "snapshot files manifest",
    )
    sidecar_path = _regular(
        root / "snapshot_files.sha256",
        "snapshot files SHA sidecar",
    )

    manifest_bytes = (
        manifest_path.read_bytes()
    )
    sidecar = sidecar_path.read_text(
        encoding="ascii"
    ).strip()
    require_lower_sha256(
        "snapshot files sidecar",
        sidecar,
    )
    if (
        sha256_bytes(manifest_bytes)
        != sidecar
    ):
        raise ValueError(
            "snapshot files manifest "
            "sidecar mismatch"
        )

    manifest = strict_json_loads(
        manifest_bytes
    )
    manifest = _exact(
        manifest,
        {
            "schema_id",
            "schema_version",
            "snapshot_sha256",
            "files",
        },
        "snapshot files manifest",
    )
    if (
        manifest["schema_id"]
        != "MEMORY_DEV_DESCRIPTIVE_SNAPSHOT_FILES_V1"
        or manifest["schema_version"] != 1
    ):
        raise ValueError(
            "snapshot files schema mismatch"
        )
    if (
        manifest["snapshot_sha256"]
        != expected_snapshot_sha256
    ):
        raise ValueError(
            "snapshot files identity mismatch"
        )
    if (
        canonical_json_bytes(manifest)
        != manifest_bytes
    ):
        raise ValueError(
            "snapshot files manifest "
            "is not canonical"
        )

    raw_files = manifest["files"]
    if not isinstance(raw_files, list):
        raise TypeError(
            "snapshot files must be array"
        )

    registered = {
        "snapshot_files.json",
        "snapshot_files.sha256",
    }

    for item in raw_files:
        entry = _exact(
            item,
            {
                "relative_path",
                "sha256",
                "size",
            },
            "snapshot file entry",
        )
        relative = Path(
            entry["relative_path"]
        )
        if (
            relative.is_absolute()
            or ".." in relative.parts
        ):
            raise ValueError(
                "snapshot relative path invalid"
            )
        require_lower_sha256(
            "snapshot file sha",
            entry["sha256"],
        )
        if (
            type(entry["size"]) is not int
            or entry["size"] < 0
        ):
            raise ValueError(
                "snapshot file size invalid"
            )
        relative_text = relative.as_posix()
        if relative_text in registered:
            raise ValueError(
                "duplicate snapshot file"
            )
        registered.add(relative_text)

        path = _regular(
            root / relative,
            "snapshot registered file",
        )
        if (
            sha256_file(path)
            != entry["sha256"]
        ):
            raise ValueError(
                "snapshot file SHA mismatch: "
                + relative_text
            )
        if (
            path.stat().st_size
            != entry["size"]
        ):
            raise ValueError(
                "snapshot file size mismatch: "
                + relative_text
            )

    observed = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
    }
    if observed != registered:
        raise ValueError(
            "snapshot file census mismatch"
        )

    if any(
        path.name.startswith("fm3")
        for path in root.rglob("*")
        if path.is_file()
    ):
        raise ValueError(
            "Package A snapshot must not "
            "contain FM3"
        )

    for member in snapshot.members:
        member_root = _dir(
            root / member.relative_directory,
            "snapshot member directory",
        )
        expected_member_files = {
            "governed_record.json",
            "retrieval_key.json",
            "fm1.json",
            "fm2.json",
        }
        member_files = {
            path.name
            for path in member_root.iterdir()
            if path.is_file()
        }
        if (
            member_files
            != expected_member_files
        ):
            raise ValueError(
                "snapshot member file census mismatch"
            )

        checks = {
            "governed_record.json": (
                member.governed_record_sha256
            ),
            "retrieval_key.json": (
                member.retrieval_key_sha256
            ),
            "fm1.json": member.fm1_sha256,
            "fm2.json": member.fm2_sha256,
        }
        for name, expected_sha in (
            checks.items()
        ):
            if (
                sha256_file(
                    member_root / name
                )
                != expected_sha
            ):
                raise ValueError(
                    "snapshot member binding "
                    f"mismatch: {name}"
                )

    return snapshot
