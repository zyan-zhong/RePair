from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import zipfile
from typing import Any


class Stage1PackageError(RuntimeError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def strict_json_loads(raw: bytes | str) -> Any:
    text = raw.decode("utf-8") if isinstance(raw, bytes) else raw
    def reject_pairs(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise Stage1PackageError(f"duplicate JSON key: {key}")
            out[key] = value
        return out
    return json.loads(
        text,
        object_pairs_hook=reject_pairs,
        parse_constant=lambda value: (_ for _ in ()).throw(
            Stage1PackageError(f"non-finite JSON constant: {value}")
        ),
    )


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise Stage1PackageError(f"JSON authority invalid: {path}")
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise Stage1PackageError(f"JSON object required: {path}")
    return value


def write_new_json(path: Path, value: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_json_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("write made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_zip_directory(source_root: Path, destination: Path) -> dict[str, Any]:
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    files = [
        path for path in sorted(source_root.rglob("*"))
        if path.is_file() and not path.is_symlink()
    ]
    if not files:
        raise Stage1PackageError("review root is empty")
    temp = destination.parent / f".{destination.name}.{os.getpid()}.tmp"
    if temp.exists():
        temp.unlink()
    with zipfile.ZipFile(
        temp,
        "x",
        compression=zipfile.ZIP_DEFLATED,
        compresslevel=9,
    ) as archive:
        for path in files:
            archive.write(path, path.relative_to(source_root).as_posix())
    if not zipfile.is_zipfile(temp):
        raise Stage1PackageError("temporary review ZIP invalid")
    with zipfile.ZipFile(temp) as archive:
        bad = archive.testzip()
        if bad is not None:
            raise Stage1PackageError(f"review ZIP bad member: {bad}")
    os.replace(temp, destination)
    return {
        "path": str(destination),
        "sha256": sha256_file(destination),
        "size_bytes": destination.stat().st_size,
        "member_count": len(files),
    }
