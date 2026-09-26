"""Emit the non-self-certifying P1-B code-level evidence inventory."""

from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.evaluation.evidence_completeness import (
    audit_current_evidence_contract,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)

    report = audit_current_evidence_contract()
    text = report.to_json() + "\n"

    if args.output is None:
        print(text, end="")
    else:
        if args.output.exists():
            raise FileExistsError(args.output)
        args.output.write_text(
            text,
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
