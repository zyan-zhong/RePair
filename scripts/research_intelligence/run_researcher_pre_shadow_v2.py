#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json
from pathlib import Path
from pchsi.cognitive_runtime.orchestrator import execute_one
from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.human_reference_round import (
    build_pre_shadow_projection,
    validate_evidence_binding,
)


def load(path: str) -> dict[str, object]:
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("object required")
    return value


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--human-pre-freeze-receipt", required=True)
    p.add_argument("--evidence-binding", required=True)
    p.add_argument("--round-evidence-package", required=True)
    p.add_argument("--memory-pack", required=True)
    p.add_argument("--output-root", required=True)
    p.add_argument("--round-id", required=True)
    p.add_argument("--policy-version", required=True)
    a = p.parse_args()

    receipt = load(a.human_pre_freeze_receipt)
    binding = load(a.evidence_binding)
    validate_evidence_binding(binding)

    if receipt.get("human_pre_content_hidden_from_strong_pre_shadow") is not True:
        raise SystemExit("STOP=INVALID_FREEZE_RECEIPT")
    if receipt.get("evidence_binding_sha256") != binding["evidence_binding_sha256"]:
        raise SystemExit("STOP=EVIDENCE_BINDING_RECEIPT_MISMATCH")
    if receipt.get("round_id") != a.round_id:
        raise SystemExit("STOP=ROUND_ID_MISMATCH")
    if binding["parent_policy_id"] != a.policy_version:
        raise SystemExit("STOP=PARENT_POLICY_MISMATCH")

    evidence = load(a.round_evidence_package)
    memory = load(a.memory_pack)
    memory_sha = hashlib.sha256(Path(a.memory_pack).read_bytes()).hexdigest()

    projection = build_pre_shadow_projection(
        round_evidence=evidence,
        memory_pack=memory,
        expected_round_evidence_package_sha256=binding[
            "round_evidence_package_sha256"
        ],
        expected_memory_pack_file_sha256=binding[
            "researcher_memory_pack_file_sha256"
        ],
        observed_memory_pack_file_sha256=memory_sha,
    )
    serialized = json.dumps(projection, sort_keys=True)
    if receipt["human_pre_record_sha256"] in serialized:
        raise SystemExit("STOP=HUMAN_PRE_HASH_LEAKED_INTO_PRE_SHADOW")

    unit = {
        "round_id": a.round_id,
        "role": "TRAINING_RESEARCHER",
        "stage_id": "R-PRE-SHADOW",
    }
    unit["identity_sha256"] = domain_hash(
        "RESEARCHER_PRE_SHADOW_UNIT_V1", unit
    )
    access = {
        "task_id": a.round_id,
        "gamefile_sha256": projection["round_evidence_package_sha256"],
        "access_class": "TRAIN_REFERENCE_ROUND",
        "dataset_split": "TRAIN_RESEARCH_INTELLIGENCE",
        "training_permitted": True,
        "select_evaluation_permitted": False,
        "confirmatory_permitted": False,
        "teacher_call_permitted": True,
    }

    result = execute_one(
        output_root=Path(a.output_root),
        unit_identity=unit,
        stage_id="R-PRE-SHADOW",
        condition_id=None,
        round_id=a.round_id,
        policy_version=a.policy_version,
        projection=projection,
        task_access=access,
    )
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
