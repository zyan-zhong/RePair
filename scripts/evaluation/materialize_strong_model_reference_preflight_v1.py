#!/usr/bin/env python3
"""Read-only strong-model shared-protocol integration preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess


REQUIRED_ASSETS = (
    "configs/evaluation/strong_model_reference_shared_protocol_v1.json",
    "docs/evaluation/STRONG_MODEL_REFERENCE_SHARED_PROTOCOL_V1.md",
    "docs/plans/STRONG_MODEL_REFERENCE_LIVE_EXECUTOR_IMPLEMENTATION_PLAN_V1.md",
    "src/pchsi/evaluation/openai_responses_policy.py",
    "src/pchsi/evaluation/raw_policy_prompt.py",
    "src/pchsi/evaluation/raw_policy_parser.py",
    "src/pchsi/evaluation/runtime_core.py",
    "src/pchsi/evaluation/episode_evaluator.py",
    "src/pchsi/evaluation/alfworld_adapter.py",
    "src/pchsi/evaluation/artifact_publisher.py",
    "configs/cognitive_runtime/p2_asset_binding_v1.json",
    "data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-head", required=True)
    args = parser.parse_args()

    repo = args.repo.resolve()
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if head != args.expected_head:
        raise SystemExit(
            f"HEAD_MISMATCH expected={args.expected_head} observed={head}"
        )
    status = subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain"],
        text=True,
    )
    if status:
        raise SystemExit("WORKTREE_NOT_CLEAN")

    assets: dict[str, dict[str, object]] = {}
    for relative in REQUIRED_ASSETS:
        path = repo / relative
        if path.is_symlink() or not path.is_file():
            raise SystemExit(f"MISSING_OR_UNSAFE={relative}")
        assets[relative] = {
            "sha256": sha256(path),
            "size_bytes": path.stat().st_size,
        }

    config = json.loads(
        (repo / REQUIRED_ASSETS[0]).read_text(encoding="utf-8")
    )
    arms = config["registered_model_arms"]
    assert arms[0]["requested_model"] == "gpt-5.6-sol"
    assert arms[0]["reasoning_effort"] == "high"
    assert arms[0]["structured_output"] is False
    assert arms[0]["tools"] == []
    assert arms[0]["automatic_retry_count"] == 0
    assert config["transport_reuse"]["reuse_existing_p2_transport"] is True
    assert config["transport_reuse"]["new_http_client_allowed"] is False

    payload = {
        "schema_id": "STRONG_MODEL_REFERENCE_PARALLEL_PREFLIGHT_V1",
        "repository_head": head,
        "assets": assets,
        "code_review_status": "REQUIRED",
        "live_executor_integration_status": (
            "PLANNED_NOT_YET_CODE_APPROVED"
        ),
        "model_call_count": 0,
        "environment_execution_count": 0,
        "human_pre_result_visibility": "FORBIDDEN",
        "parallel_collection_allowed_after_approval": True,
        "batch_api_full_episode_allowed": False,
        "next_gate": "STRONG_MODEL_REFERENCE_LIVE_EXECUTOR_CODE_REVIEW",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.output.exists():
        raise SystemExit(f"REFUSING_TO_OVERWRITE={args.output}")
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        encoding="utf-8",
    )
    print("STRONG_MODEL_REFERENCE_PARALLEL_PREFLIGHT_PASS")
    print(f"OUTPUT={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
