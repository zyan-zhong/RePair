from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path

from pchsi.memory.procedural_builder import (
    ProceduralFailureMemoryRecordV1,
    ProceduralMemoryAssemblyInputV1,
    build_procedural_failure_memory_record_v1,
)
from pchsi.memory.procedural_record import (
    AssemblyRegistrationBindingV1,
    MemoryEvidenceRefV1,
)
from pchsi.memory.sequence_failure_experience import SequenceFailureExperienceV1


def _require_regular_file(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"{label} must not be symlink")
    if not path.is_file():
        raise ValueError(f"{label} must be regular file")
    return path


def _load_source_experience(path: Path) -> SequenceFailureExperienceV1:
    data = _require_regular_file(path, "source experience").read_bytes()
    value = SequenceFailureExperienceV1.from_json(data)
    if data != value.canonical_bytes():
        raise ValueError("source experience input must be canonical bytes")
    return value


def _load_assembly_input(
    path: Path,
) -> tuple[ProceduralMemoryAssemblyInputV1, bytes]:
    data = _require_regular_file(path, "assembly registration").read_bytes()
    value = ProceduralMemoryAssemblyInputV1.from_json(data)
    if data != value.canonical_bytes():
        raise ValueError("assembly registration input must be canonical bytes")
    return value, data


def _load_previous_record(
    path: Path,
) -> ProceduralFailureMemoryRecordV1:
    data = _require_regular_file(path, "previous record").read_bytes()
    value = ProceduralFailureMemoryRecordV1.from_json(data)
    if data != value.canonical_bytes():
        raise ValueError("previous record input must be canonical bytes")
    return value


def _write_all(fd: int, data: bytes) -> None:
    view = memoryview(data)
    while view:
        count = os.write(fd, view)
        if count <= 0:
            raise OSError("os.write made no progress")
        view = view[count:]


def _write_once_durable(output_path: Path, data: bytes) -> None:
    output_path = Path(output_path)
    parent = output_path.parent

    if parent.is_symlink():
        raise ValueError("output parent must not be symlink")
    if not parent.is_dir():
        raise ValueError("output parent must already exist as directory")
    if output_path.is_symlink():
        raise ValueError("output path must not be symlink")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(output_path, flags, 0o600)
    wrote = False
    try:
        _write_all(fd, data)
        os.fsync(fd)
        wrote = True
    finally:
        os.close(fd)
        if not wrote:
            try:
                output_path.unlink()
            except FileNotFoundError:
                pass

    dir_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0)
    parent_fd = os.open(parent, dir_flags)
    try:
        os.fsync(parent_fd)
    finally:
        os.close(parent_fd)


def materialize_files_v1(
    *,
    source_experience_paths: tuple[Path, ...],
    assembly_registration_path: Path,
    previous_record_path: Path | None,
    output_path: Path,
) -> ProceduralFailureMemoryRecordV1:
    if type(source_experience_paths) is not tuple or not source_experience_paths:
        raise ValueError("source_experience_paths must be nonempty tuple")

    assembly_input, registration_bytes = _load_assembly_input(
        assembly_registration_path
    )
    registration_sha = hashlib.sha256(registration_bytes).hexdigest()

    registration_binding = AssemblyRegistrationBindingV1(
        schema_id="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
        registration_id=assembly_input.registration_id,
        assembly_registration_sha256=registration_sha,
        lineage_registration_ref=MemoryEvidenceRefV1(
            source_kind="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
            source_id=assembly_input.registration_id,
            source_sha256=registration_sha,
        ),
    )

    source_experiences = tuple(
        _load_source_experience(path)
        for path in source_experience_paths
    )

    if assembly_input.lineage.record_version == 1:
        if previous_record_path is not None:
            raise ValueError("version 1 rejects --previous-record")
        previous_record = None
    else:
        if previous_record_path is None:
            raise ValueError("version >1 requires --previous-record")
        previous_record = _load_previous_record(previous_record_path)

    record = build_procedural_failure_memory_record_v1(
        assembly_input=assembly_input,
        assembly_registration_binding=registration_binding,
        source_experiences=source_experiences,
        previous_record=previous_record,
    )

    expected_name = (
        f"{record.memory_lineage_id}.v{record.record_version}.json"
    )
    if Path(output_path).name != expected_name:
        raise ValueError("output basename does not match canonical record name")

    _write_once_durable(Path(output_path), record.canonical_bytes())
    return record


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Materialize one pre-registered procedural Failure Memory "
            "candidate from explicit canonical inputs."
        )
    )
    parser.add_argument(
        "--source-experience",
        action="append",
        required=True,
        dest="source_experiences",
    )
    parser.add_argument("--assembly-registration", required=True)
    parser.add_argument("--previous-record")
    parser.add_argument("--output", required=True)
    return parser


def main() -> int:
    args = _parser().parse_args()
    materialize_files_v1(
        source_experience_paths=tuple(
            Path(item) for item in args.source_experiences
        ),
        assembly_registration_path=Path(args.assembly_registration),
        previous_record_path=(
            None
            if args.previous_record is None
            else Path(args.previous_record)
        ),
        output_path=Path(args.output),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
