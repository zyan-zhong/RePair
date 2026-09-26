#!/usr/bin/env python3
from __future__ import annotations
import argparse, hashlib, json, subprocess
from pathlib import Path

from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.product_isolation import (
    HUMAN,
    assert_artifact_domain,
    assert_separate_roots,
)

REQUIRED = (
    "docs/research/HUMAN_TRAINING_RESEARCHER_TEMPLATE_V2.md",
    "src/pchsi/cognitive_runtime/researcher.py",
    "configs/cognitive_runtime/schemas/human_researcher_pre_v1.json",
    "configs/cognitive_runtime/schemas/human_researcher_post_v1.json",
    "configs/cognitive_runtime/schemas/api_researcher_pre_shadow_v1.json",
    "configs/cognitive_runtime/schemas/api_researcher_post_shadow_v1.json",
    "experiments/formal_analyzer/pi1_reference_v1/EXPERIMENT_MANIFEST.json",
    "experiments/formal_analyzer/pi1_reference_v1/RESULT_MANIFEST.json",
    "docs/protocol/F0F1_REPAIR_VERIFICATION_V2.md",
    "docs/project/REFERENCE_LOOP_WORKFLOW_COORDINATION_V1.md",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canon(value: object) -> bytes:
    return (
        json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        )
        + "\n"
    ).encode()


def write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    path.write_bytes(
        canon(value) if not isinstance(value, str) else value.encode()
    )


def load_object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"not a regular JSON file: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--repo", required=True)
    p.add_argument("--output-dir", required=True)
    p.add_argument("--expected-head", required=True)
    p.add_argument("--round-id", required=True)
    p.add_argument("--parent-policy-id", required=True)
    p.add_argument("--human-scientific-root", required=True)
    p.add_argument("--benchmark-scientific-root", required=True)
    p.add_argument("--round-evidence-package", required=True)
    p.add_argument("--researcher-memory-pack", required=True)
    a = p.parse_args()

    repo = Path(a.repo).resolve()
    out = Path(a.output_dir).resolve()
    round_path = Path(a.round_evidence_package).resolve()
    memory_path = Path(a.researcher_memory_pack).resolve()
    assert_separate_roots(
        Path(a.human_scientific_root), Path(a.benchmark_scientific_root)
    )
    head = subprocess.check_output(
        ["git", "-C", str(repo), "rev-parse", "HEAD"], text=True
    ).strip()
    if head != a.expected_head:
        raise SystemExit("STOP=HEAD_MISMATCH")
    if subprocess.check_output(
        ["git", "-C", str(repo), "status", "--porcelain"], text=True
    ).strip():
        raise SystemExit("STOP=DIRTY")

    rows = []
    for rel in REQUIRED:
        path = repo / rel
        ok = path.is_file() and not path.is_symlink()
        rows.append(
            {
                "relative_path": rel,
                "status": "PRESENT" if ok else "MISSING",
                "sha256": sha(path) if ok else None,
            }
        )
    missing = [r["relative_path"] for r in rows if r["status"] != "PRESENT"]

    result_manifest = load_object(
        repo / "experiments/formal_analyzer/pi1_reference_v1/RESULT_MANIFEST.json"
    )
    expected_round_sha = result_manifest["round_evidence"][
        "round_evidence_package_sha256"
    ]
    round_evidence = load_object(round_path)
    if round_evidence.get("schema_id") != "ROUND_EVIDENCE_PACKAGE_V1":
        raise SystemExit("STOP=ROUND_EVIDENCE_SCHEMA_MISMATCH")
    assert_artifact_domain(round_evidence, HUMAN)
    observed_round_sha = domain_hash(
        "ROUND_EVIDENCE_PACKAGE_V1",
        round_evidence,
        excluded_field="round_evidence_package_sha256",
    )
    if observed_round_sha != expected_round_sha:
        raise SystemExit("STOP=ROUND_EVIDENCE_IDENTITY_MISMATCH")

    memory_pack = load_object(memory_path)
    if memory_pack.get("schema_id") != "RESEARCHER_MEMORY_PACK_V1":
        raise SystemExit("STOP=RESEARCHER_MEMORY_PACK_SCHEMA_MISMATCH")
    assert_artifact_domain(memory_pack, HUMAN)
    memory_sha = sha(memory_path)

    discovered = []
    for pattern in (
        "experiments/formal_analyzer/pi1_reference_v1/**/*.json",
        "artifacts/**/*RESEARCHER_MEMORY_PACK*.json",
        "experiments/round1/**/*.json",
    ):
        for path in repo.glob(pattern):
            if path.is_file() and not path.is_symlink():
                discovered.append(
                    {
                        "relative_path": path.relative_to(repo).as_posix(),
                        "sha256": sha(path),
                    }
                )
    discovered = sorted(
        {x["relative_path"]: x for x in discovered}.values(),
        key=lambda x: x["relative_path"],
    )

    cutoff_input = {
        "repository_head": head,
        "required_assets": rows,
        "discovered_human_round_assets": discovered,
        "round_evidence_package_sha256": observed_round_sha,
        "researcher_memory_pack_file_sha256": memory_sha,
    }
    cutoff = hashlib.sha256(canon(cutoff_input)).hexdigest()

    binding = {
        "schema_id": "HUMAN_REFERENCE_EVIDENCE_BINDING_V1",
        "round_id": a.round_id,
        "parent_policy_id": a.parent_policy_id,
        "evidence_cutoff_sha256": cutoff,
        "round_evidence_package_sha256": observed_round_sha,
        "researcher_memory_pack_file_sha256": memory_sha,
        "evidence_binding_sha256": "0" * 64,
    }
    binding["evidence_binding_sha256"] = domain_hash(
        "HUMAN_REFERENCE_EVIDENCE_BINDING_V1",
        binding,
        excluded_field="evidence_binding_sha256",
    )

    report = {
        "schema_id": "HUMAN_REFERENCE_ROUND_INPUT_PACKAGE_V4",
        "scientific_product_domain": "HUMAN_REFERENCE_ROUND",
        "status": (
            "READY_FOR_HUMAN_PRE_COMPLETION"
            if not missing
            else "QUERY_REQUIRED"
        ),
        "round_id": a.round_id,
        "parent_policy_id": a.parent_policy_id,
        "repository_head": head,
        "evidence_cutoff_sha256": cutoff,
        "round_evidence_package": {
            "path": str(round_path),
            "semantic_sha256": observed_round_sha,
        },
        "researcher_memory_pack": {
            "path": str(memory_path),
            "file_sha256": memory_sha,
        },
        "required_assets": rows,
        "missing_required_assets": missing,
        "discovered_human_round_assets": discovered,
        "benchmark_artifact_count": 0,
        "benchmark_results_visible": False,
        "model_call": False,
        "environment_execution": False,
        "training_execution": False,
        "next_gate": (
            "HUMAN_PRE_MANUAL_COMPLETION_AND_REVIEW"
            if not missing
            else "QUERY_REQUIRED"
        ),
    }

    out.mkdir(parents=True, exist_ok=False)
    write(out / "HUMAN_REFERENCE_ROUND_INPUT_PACKAGE_V4.json", report)
    write(out / "HUMAN_REFERENCE_EVIDENCE_BINDING_V1.json", binding)
    write(
        out / "HUMAN_RESEARCHER_PRE_WORKSHEET_V4.md",
        (
            "# Human Researcher PRE Worksheet V4\n\n"
            f"round_id: `{a.round_id}`\n"
            f"parent_policy: `{a.parent_policy_id}`\n"
            f"evidence_cutoff: `{cutoff}`\n"
            f"round_evidence_package_sha256: `{observed_round_sha}`\n"
            f"researcher_memory_pack_file_sha256: `{memory_sha}`\n\n"
            "Use exactly the bound Round Evidence Package and Researcher "
            "Memory pack. No per-task strong-model benchmark result is permitted.\n"
        ),
    )
    print("HUMAN_REFERENCE_ROUND_INPUTS_V4_PASS")
    print("EVIDENCE_CUTOFF_SHA256=" + cutoff)
    print("ROUND_EVIDENCE_PACKAGE_SHA256=" + observed_round_sha)
    print("RESEARCHER_MEMORY_PACK_FILE_SHA256=" + memory_sha)
    print("BENCHMARK_RESULT_COUNT=0")


if __name__ == "__main__":
    main()
