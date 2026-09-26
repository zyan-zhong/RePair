#!/usr/bin/env python3
"""Build a canonical Analyzer route census from validated evidence packs."""

from __future__ import annotations
import argparse
from pathlib import Path

from pchsi.analyzer.outcome_router import build_mechanical_census, route_episode
from pchsi.reference_loop.canonical import strict_json_loads, write_new_json


def _object(path: Path) -> dict[str, object]:
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise ValueError(f"input must be object: {path}")
    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-pack", action="append", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    routes = [route_episode(_object(Path(x))) for x in args.evidence_pack]
    write_new_json(Path(args.output), build_mechanical_census(routes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
