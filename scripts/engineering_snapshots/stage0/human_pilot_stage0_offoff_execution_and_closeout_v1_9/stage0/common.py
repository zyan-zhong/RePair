from __future__ import annotations

import fcntl
import hashlib
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable
import zipfile


class Stage0Error(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise Stage0Error(f"DUPLICATE_JSON_KEY:{key}")
        result[key] = value
    return result


def strict_json_loads(data: str | bytes) -> Any:
    text = data.decode("utf-8") if isinstance(data, bytes) else data
    return json.loads(
        text,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            Stage0Error(f"NONSTANDARD_JSON_CONSTANT:{value}")
        ),
    )


def load_json_object(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise Stage0Error(f"JSON_FILE_INVALID:{path}")
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise Stage0Error(f"JSON_OBJECT_REQUIRED:{path}")
    return value


def domain_sha256(
    schema_id: str,
    value: dict[str, Any],
    *,
    sha_field: str,
) -> str:
    payload = {
        key: child
        for key, child in value.items()
        if key != sha_field
    }
    return hashlib.sha256(
        schema_id.encode("utf-8")
        + b"\0"
        + canonical_json_bytes(payload)
    ).hexdigest()


def require_lower_sha256(name: str, value: Any) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise Stage0Error(f"{name}_INVALID_SHA256:{value!r}")
    return value


def require_file_sha(path: Path, expected: str, label: str) -> None:
    if not path.is_file() or path.is_symlink():
        raise Stage0Error(f"{label}_INVALID_FILE:{path}")
    observed = sha256_file(path)
    if observed != expected:
        raise Stage0Error(
            f"{label}_SHA256_MISMATCH:{observed}:{expected}"
        )


def fsync_directory(path: Path) -> None:
    descriptor = os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
    )
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_new(path: Path, data: bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    temporary = path.parent / (
        f".{path.name}.{sha256_bytes(data)}.tmp"
    )
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(str(temporary))
    descriptor = os.open(
        temporary,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        mode,
    )
    try:
        view = memoryview(data)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("atomic write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(temporary, path)
    fsync_directory(path.parent)


def write_json_new(path: Path, value: dict[str, Any]) -> None:
    atomic_write_new(path, canonical_json_bytes(value))


def write_or_reuse_exact(path: Path, value: dict[str, Any]) -> dict[str, Any]:
    expected = canonical_json_bytes(value)
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise Stage0Error(f"EXISTING_OUTPUT_INVALID:{path}")
        observed = path.read_bytes()
        if observed != expected:
            raise Stage0Error(f"EXISTING_OUTPUT_CHANGED:{path}")
        return value
    atomic_write_new(path, expected)
    return value


def append_canonical_json_line(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = canonical_json_bytes(value) + b"\n"
    descriptor = os.open(
        path,
        os.O_WRONLY | os.O_APPEND | os.O_CREAT,
        0o600,
    )
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        view = memoryview(line)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("append made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)
    fsync_directory(path.parent)


def read_json_lines(path: Path) -> tuple[dict[str, Any], ...]:
    if not path.exists():
        return ()
    if not path.is_file() or path.is_symlink():
        raise Stage0Error(f"JSONL_FILE_INVALID:{path}")
    rows: list[dict[str, Any]] = []
    for index, line in enumerate(path.read_bytes().splitlines()):
        if not line.strip():
            continue
        value = strict_json_loads(line)
        if not isinstance(value, dict):
            raise Stage0Error(f"JSONL_OBJECT_REQUIRED:{path}:{index}")
        rows.append(value)
    return tuple(rows)


def atomic_publish_zip(
    *,
    source_root: Path,
    destination: Path,
) -> dict[str, Any]:
    if not source_root.is_dir() or source_root.is_symlink():
        raise Stage0Error(f"ZIP_SOURCE_ROOT_INVALID:{source_root}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(str(destination))

    file_paths = tuple(
        path
        for path in sorted(source_root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    )
    if not file_paths:
        raise Stage0Error("ZIP_SOURCE_ROOT_EMPTY")

    temporary = destination.parent / (
        f".{destination.name}.{os.getpid()}.tmp"
    )
    if temporary.exists() or temporary.is_symlink():
        raise FileExistsError(str(temporary))

    try:
        with zipfile.ZipFile(
            temporary,
            "x",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=9,
        ) as archive:
            for path in file_paths:
                relative = path.relative_to(source_root).as_posix()
                archive.write(path, relative)

        if temporary.stat().st_size <= 0:
            raise Stage0Error("ZIP_TEMPORARY_IS_EMPTY")
        if not zipfile.is_zipfile(temporary):
            raise Stage0Error("ZIP_TEMPORARY_MAGIC_INVALID")
        with zipfile.ZipFile(temporary, "r") as archive:
            bad = archive.testzip()
            if bad is not None:
                raise Stage0Error(f"ZIP_TEMPORARY_CRC_FAILED:{bad}")
            observed = sorted(archive.namelist())
            expected = [
                path.relative_to(source_root).as_posix()
                for path in file_paths
            ]
            if observed != expected:
                raise Stage0Error("ZIP_MEMBER_SET_CHANGED")

        descriptor = os.open(temporary, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, destination)
        fsync_directory(destination.parent)
    except Exception:
        if temporary.exists():
            temporary.unlink()
        raise

    return {
        "path": str(destination),
        "sha256": sha256_file(destination),
        "size_bytes": destination.stat().st_size,
        "member_count": len(file_paths),
    }


def stable_file_index(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.is_symlink():
            continue
        rows.append({
            "path": path.relative_to(root).as_posix(),
            "sha256": sha256_file(path),
            "size_bytes": path.stat().st_size,
        })
    return rows
