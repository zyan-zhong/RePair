#!/usr/bin/env python3
"""Materialize the frozen A0 12-cell scientific manifest from explicit inputs.

This CLI is offline-only. It does not select sources, start a model, start an
environment, run retrieval, or authorize scientific execution.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import NoReturn

from pchsi.memory.scientific_validation import (
    A0SourceBindingV1,
    build_a0_scientific_manifest_v1,
)


ENGINEERING_BASE_HEAD = "112ba5d3ccc0a3f3c3a9fdd143ec4c69fa525229"


def _reject_constant(value: str) -> NoReturn:
    raise ValueError(f"non-finite JSON constant rejected: {value}")


def _reject_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
    out: dict[str, object] = {}
    for key, value in pairs:
        if key in out:
            raise ValueError(f"duplicate JSON member: {key}")
        out[key] = value
    return out


def _strict_json(path: Path) -> object:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"input must be regular non-symlink file: {path}")
    return json.loads(
        path.read_text(encoding="utf-8"),
        object_pairs_hook=_reject_duplicates,
        parse_constant=_reject_constant,
    )


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    parent = path.parent
    if not parent.is_dir() or parent.is_symlink():
        raise ValueError("output parent must be existing non-symlink directory")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("os.write made no progress")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def materialize(
    *,
    source_binding_paths: tuple[Path, ...],
    output_path: Path,
    engineering_base_head: str = ENGINEERING_BASE_HEAD,
) -> str:
    if len(source_binding_paths) != 3:
        raise ValueError("exactly three explicit source bindings are required")
    sources = tuple(
        A0SourceBindingV1.from_dict(_strict_json(path))
        for path in source_binding_paths
    )
    manifest = build_a0_scientific_manifest_v1(
        engineering_base_head=engineering_base_head,
        sources=sources,
    )
    _write_once(output_path, manifest.canonical_bytes())
    return manifest.manifest_sha256


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-binding",
        action="append",
        required=True,
        help="repeat exactly three times; no directory discovery is performed",
    )
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--engineering-base-head",
        default=ENGINEERING_BASE_HEAD,
    )
    args = parser.parse_args()

    paths = tuple(Path(value) for value in args.source_binding)
    digest = materialize(
        source_binding_paths=paths,
        output_path=Path(args.output),
        engineering_base_head=args.engineering_base_head,
    )
    print("A0_SCIENTIFIC_MANIFEST_SHA256=" + str(digest))
    print("A0_SCIENTIFIC_CELL_COUNT=12")
    print("SCIENTIFIC_EXECUTION_AUTHORIZED=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
