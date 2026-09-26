#!/usr/bin/env python3
"""Closed, non-executing CLI for the E1 evaluator implementation candidate."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys


_DESCRIPTION = {
    "calls_model": False,
    "design_id": "E1_ALFWORLD_EVALUATOR_V1",
    "executes_environment": False,
    "execution_exit_code": 77,
    "modes": [
        "describe",
        "validate-config",
        "execute-closed",
    ],
    "status": "CANDIDATE_EXECUTION_NOT_APPROVED",
    "writes_run_artifacts": False,
}

_CONFIG_FIELDS = {
    "schema_id",
    "task_manifest",
    "gamefile_identity_manifest",
    "environment_runtime_manifest",
    "policy_runtime_manifest",
}
_PATH_FIELDS = tuple(sorted(_CONFIG_FIELDS - {"schema_id"}))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Describe or purely validate the closed E1 evaluator candidate."
        )
    )
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--describe", action="store_true")
    modes.add_argument(
        "--validate-config",
        type=Path,
        metavar="PATH",
    )
    modes.add_argument("--execute", action="store_true")
    return parser


def _emit(value: object, *, stream) -> None:
    stream.write(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


def _validate_config(path: Path) -> tuple[bool, str]:
    if path.is_symlink() or not path.is_file():
        return False, "CONFIG_NOT_REGULAR_FILE"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return False, "CONFIG_INVALID_JSON"
    if not isinstance(value, dict):
        return False, "CONFIG_TOP_LEVEL_NOT_OBJECT"
    observed = set(value)
    unknown = sorted(observed - _CONFIG_FIELDS)
    missing = sorted(_CONFIG_FIELDS - observed)
    if unknown:
        return False, "UNKNOWN_CONFIG_FIELD:" + ",".join(unknown)
    if missing:
        return False, "MISSING_CONFIG_FIELD:" + ",".join(missing)
    if value["schema_id"] != "E1_EVALUATOR_CANDIDATE_CONFIG_V1":
        return False, "CONFIG_SCHEMA_ID_MISMATCH"
    for name in _PATH_FIELDS:
        raw = value[name]
        if not isinstance(raw, str) or not raw:
            return False, "CONFIG_PATH_INVALID:" + name
        artifact = Path(raw)
        if (
            not artifact.is_absolute()
            or artifact.is_symlink()
            or not artifact.is_file()
        ):
            return False, "MISSING_READINESS_ARTIFACT:" + name
    return True, "E1_EVALUATOR_CONFIG_VALID"


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.describe:
        _emit(_DESCRIPTION, stream=sys.stdout)
        return 0
    if args.execute:
        sys.stdout.write(
            "E1_EVALUATOR_EXECUTION_NOT_APPROVED\n"
        )
        return 77
    valid, status = _validate_config(args.validate_config)
    if valid:
        _emit(
            {
                "status": status,
                "executes_environment": False,
                "calls_model": False,
                "writes_run_artifacts": False,
            },
            stream=sys.stdout,
        )
        return 0
    sys.stderr.write(status + "\n")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
