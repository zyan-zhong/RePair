from __future__ import annotations

from pathlib import Path
import hashlib
import json
import os
import zipfile


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
        + b"\n"
    )


def write_new_bytes(path: Path, payload: bytes, mode: int = 0o600) -> None:
    path = Path(path)
    if path.exists() or path.is_symlink():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        view = memoryview(payload)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def write_new_json(path: Path, value: object) -> None:
    write_new_bytes(path, canonical_bytes(value))


def load_json(path: Path) -> dict[str, object]:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise ValueError("JSON_NOT_REGULAR:" + str(path))
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def safe_extract_zip(source: Path, destination: Path) -> None:
    source = Path(source)
    destination = Path(destination)
    if destination.exists() or destination.is_symlink():
        raise FileExistsError(destination)
    destination.mkdir(parents=True, mode=0o700)
    root = destination.resolve()

    with zipfile.ZipFile(source, "r") as archive:
        bad = archive.testzip()
        if bad is not None:
            raise ValueError("ZIP_CRC_FAILURE:" + bad)
        for info in archive.infolist():
            member = Path(info.filename)
            if member.is_absolute() or ".." in member.parts:
                raise ValueError("ZIP_MEMBER_PATH_ESCAPE:" + info.filename)
            mode = (info.external_attr >> 16) & 0o170000
            if mode == 0o120000:
                raise ValueError("ZIP_SYMLINK_MEMBER_FORBIDDEN:" + info.filename)
            target = (root / member).resolve()
            try:
                target.relative_to(root)
            except ValueError as error:
                raise ValueError("ZIP_MEMBER_ESCAPES_ROOT:" + info.filename) from error
        archive.extractall(root)
