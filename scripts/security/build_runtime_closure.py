#!/usr/bin/env python3
"""Build a deterministic readelf-based candidate runtime manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
from typing import Sequence

from pchsi.security.manifests import RuntimeManifest


CANDIDATE_STATUS = "candidate_pending_static_and_semantic_review"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _readelf(path: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["/usr/bin/readelf", *arguments, str(path)],
        check=False,
        text=True,
        capture_output=True,
        env={
            "LC_ALL": "C",
            "LANG": "C",
            "TZ": "UTC",
        },
    )
    if result.returncode != 0:
        raise ValueError(result.stderr.strip() or "readelf failed")
    return result.stdout


def _interpreter(program_headers: str) -> str:
    match = re.search(
        r"Requesting program interpreter:\s*([^\]]+)\]",
        program_headers,
    )
    if match is None:
        raise ValueError("ELF interpreter is missing")
    return match.group(1).strip()


def _needed(dynamic: str) -> tuple[str, ...]:
    values = {
        match.group(1)
        for match in re.finditer(
            r"Shared library:\s*\[([^\]]+)\]",
            dynamic,
        )
    }
    return tuple(sorted(values))


def build_runtime_manifest(
    *,
    python_binary: Path,
    bootstrap_source: Path,
    output_root: Path,
) -> RuntimeManifest:
    for name, path in (
        ("python_binary", python_binary),
        ("bootstrap_source", bootstrap_source),
    ):
        if path.is_symlink():
            raise ValueError(f"{name} must not be a symlink")
        if not path.is_file():
            raise ValueError(f"{name} must identify a regular file")

    output_root.mkdir(parents=True, exist_ok=True)

    program_headers = _readelf(
        python_binary,
        "--program-headers",
        "--wide",
    )
    dynamic = _readelf(
        python_binary,
        "--dynamic",
        "--wide",
    )

    source_date_epoch = int(
        os.environ.get("SOURCE_DATE_EPOCH", "0")
    )
    if source_date_epoch < 0:
        raise ValueError("SOURCE_DATE_EPOCH must be non-negative")

    manifest = RuntimeManifest(
        schema_version=1,
        status=CANDIDATE_STATUS,
        python_sha256=_sha256(python_binary),
        bootstrap_sha256=_sha256(bootstrap_source),
        interpreter_path=_interpreter(program_headers),
        needed_libraries=_needed(dynamic),
        source_date_epoch=source_date_epoch,
        toolchain="GNU readelf",
    )

    output = output_root / "runtime_manifest.json"
    output.write_bytes(manifest.canonical_bytes())

    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--python-binary", type=Path, required=True)
    parser.add_argument("--bootstrap-source", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    manifest = build_runtime_manifest(
        python_binary=arguments.python_binary,
        bootstrap_source=arguments.bootstrap_source,
        output_root=arguments.output_root,
    )
    print(
        json.dumps(
            manifest.to_dict(),
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
