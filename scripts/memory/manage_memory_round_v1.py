#!/usr/bin/env python3
"""Create/finalize append-only Memory round stores."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.memory.round_maintenance import (
    MemoryRoundStateV1,
    MemoryShadowEventV1,
    append_shadow_event_v1,
    finalize_round_store_v1,
    initialize_round_store_v1,
)


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init")
    init.add_argument("--state", required=True)
    init.add_argument("--root", required=True)

    append = sub.add_parser("append")
    append.add_argument("--state", required=True)
    append.add_argument("--event", required=True)
    append.add_argument("--root", required=True)

    close = sub.add_parser("close")
    close.add_argument("--state", required=True)
    close.add_argument("--root", required=True)

    args = parser.parse_args()
    state = MemoryRoundStateV1.from_json(
        Path(args.state).read_bytes()
    )
    root = Path(args.root)

    if args.command == "init":
        initialize_round_store_v1(root=root, state=state)
        print("MEMORY_ROUND_STORE_INITIALIZED")
        print("STATE_SHA256=" + state.state_sha256)
    elif args.command == "append":
        raw = json.loads(
            Path(args.event).read_text(encoding="utf-8")
        )
        event = MemoryShadowEventV1.from_dict(raw)
        path = append_shadow_event_v1(
            root=root,
            state=state,
            event=event,
        )
        print("MEMORY_SHADOW_EVENT_APPENDED")
        print("EVENT_ID=" + event.event_id)
        print("EVENT_PATH=" + str(path))
    else:
        closure = finalize_round_store_v1(
            root=root,
            state=state,
        )
        print("MEMORY_ROUND_STORE_FINALIZED")
        print(
            "CLOSURE_SHA256="
            + closure.closure_sha256
        )
        print(
            "NEXT_SNAPSHOT_PLAN_SHA256="
            + closure.next_snapshot_plan_sha256
        )


if __name__ == "__main__":
    main()
