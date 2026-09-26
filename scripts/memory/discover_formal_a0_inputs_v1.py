#!/usr/bin/env python3
"""Discover already-frozen Formal-A external inputs by content identity.

No model/environment/retrieval/scheduler execution. Byte-identical duplicate
copies are tolerated; more than one distinct qualifying content identity fails.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from pchsi.evaluation.canonical_evidence import strict_json_loads
from pchsi.memory.source_state_contracts import RegisteredReplaySourceV1


EXPECTED_POLICY = "P4-R1-Q2-BAD-TRAIN17"
EXPECTED_SNAPSHOT = (
    "8ebdf8feaa3f52874addcfc6541d1b29cbf5d124ea68fd0da0fc2ba037085189"
)
EXPECTED_TOKEN = (
    "613166c9f092795cb03c892ee0046f0af5bf7fc13ba44f7fccb950027c329262"
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _replay_candidate(path: Path) -> bool:
    try:
        payload = strict_json_loads(path.read_bytes())
        if (
            not isinstance(payload, dict)
            or set(payload) != {"authority_commit", "cases"}
        ):
            return False
        cases = payload["cases"]
        if not isinstance(cases, list) or len(cases) != 3:
            return False
        sources = []
        for case in cases:
            if not isinstance(case, dict):
                return False
            source_path = Path(case["replay_source_path"])
            if not source_path.is_file() or source_path.is_symlink():
                return False
            if _sha(source_path) != case["replay_source_sha256"]:
                return False
            source = RegisteredReplaySourceV1.from_json(
                source_path.read_bytes()
            )
            if source.source_policy_condition != EXPECTED_POLICY:
                return False
            sources.append(source)
        return (
            len({x.source_task_id for x in sources}) == 3
            and len({x.source_gamefile_sha256 for x in sources}) == 3
        )
    except Exception:
        return False


def _index_candidate(path: Path) -> bool:
    try:
        payload = strict_json_loads(path.read_bytes())
        return (
            isinstance(payload, dict)
            and payload.get("schema_id")
            == "PACKAGE_B_DIRECT_REPRESENTATION_INDEX_V1"
            and payload.get("snapshot_sha256") == EXPECTED_SNAPSHOT
            and payload.get("token_budget_contract_sha256")
            == EXPECTED_TOKEN
            and payload.get("record_count") == 3
            and payload.get("core_matched_record_count") == 3
            and payload.get(
                "pi1_matched_memory_representation_ablation_ready"
            )
            is True
            and payload.get("scientific_execution_authorized") is False
        )
    except Exception:
        return False


def _unique_content(paths, label):
    by_sha = {}
    for path in paths:
        by_sha.setdefault(_sha(path), []).append(path)
    if len(by_sha) != 1:
        raise SystemExit(
            f"STOP={label}_UNIQUE_CONTENT_COUNT_{len(by_sha)}"
        )
    digest, copies = next(iter(by_sha.items()))
    return digest, sorted(copies)[0], len(copies)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pchsi-scripts-root", required=True)
    args = parser.parse_args()

    root = Path(args.pchsi_scripts_root)
    if not root.is_dir() or root.is_symlink():
        raise SystemExit("STOP=PCHSI_SCRIPTS_ROOT_INVALID")

    replay = []
    indices = []
    for path in root.rglob("*.json"):
        if path.is_symlink() or not path.is_file():
            continue
        if path.name == "representation_index.json":
            if _index_candidate(path):
                indices.append(path)
        elif (
            "replay" in path.name.lower()
            or "qualification" in path.name.lower()
            or "manifest" in path.name.lower()
        ):
            if _replay_candidate(path):
                replay.append(path)

    if not replay:
        raise SystemExit("STOP=NO_FORMAL_A_REPLAY_MANIFEST_FOUND")
    if not indices:
        raise SystemExit("STOP=NO_B_DIRECT_REPRESENTATION_INDEX_FOUND")

    replay_sha, replay_path, replay_copies = _unique_content(
        replay,
        "REPLAY_MANIFEST",
    )
    index_sha, index_path, index_copies = _unique_content(
        indices,
        "REPRESENTATION_INDEX",
    )

    print("FORMAL_A_INPUT_DISCOVERY_PASS")
    print("REPLAY_MANIFEST=" + str(replay_path.resolve()))
    print("REPLAY_MANIFEST_SHA256=" + replay_sha)
    print("REPLAY_IDENTICAL_COPY_COUNT=" + str(replay_copies))
    print("REPRESENTATION_INDEX=" + str(index_path.resolve()))
    print("REPRESENTATION_INDEX_SHA256=" + index_sha)
    print("REPRESENTATION_INDEX_IDENTICAL_COPY_COUNT=" + str(index_copies))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
