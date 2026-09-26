#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.cognitive_runtime.registry_runner import run_registry
from pchsi.reference_loop.canonical import strict_json_loads
from pchsi.round_control.campaign_authority import (
    CampaignStartupAuthorityV1,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--campaign-authority")
    args = parser.parse_args()

    authority = None
    if args.campaign_authority:
        raw = strict_json_loads(
            Path(args.campaign_authority).read_bytes()
        )
        authority = CampaignStartupAuthorityV1.from_dict(raw)

    manifest, rc = run_registry(
        registry_path=Path(args.registry),
        output_root=Path(args.output_root),
        limit=args.limit,
        campaign_authority=authority,
    )
    print(
        "COGNITIVE_RUNTIME_REGISTRY_EXECUTION_PASS "
        f"units={len(manifest['rows'])} "
        f"quarantined={len(manifest['quarantined_source_ids'])} "
        f"terminal_route={manifest['terminal_route']}"
    )
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
