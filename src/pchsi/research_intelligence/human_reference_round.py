from __future__ import annotations
from collections.abc import Mapping
from pathlib import Path
import os

from pchsi.reference_loop.canonical import canonical_json_bytes, domain_hash
from pchsi.research_intelligence.records import freeze_human_pre, freeze_human_post
from pchsi.research_intelligence.reference_round import freeze_reference_round_manifest
from pchsi.research_intelligence.repair_portfolio import ResearchRepairPortfolioV1
from .product_isolation import HUMAN, assert_artifact_domain


def _require_sha(value: object, name: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(
        ch not in "0123456789abcdef" for ch in value
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest")
    return value


def _write_new(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        os.write(fd, canonical_json_bytes(dict(value)))
        os.fsync(fd)
    finally:
        os.close(fd)


def validate_evidence_binding(binding: Mapping[str, object]) -> None:
    required = {
        "schema_id",
        "round_id",
        "parent_policy_id",
        "evidence_cutoff_sha256",
        "round_evidence_package_sha256",
        "researcher_memory_pack_file_sha256",
        "evidence_binding_sha256",
    }
    if set(binding) != required:
        raise ValueError("Human evidence binding keyset mismatch")
    if binding["schema_id"] != "HUMAN_REFERENCE_EVIDENCE_BINDING_V1":
        raise ValueError("Human evidence binding schema mismatch")
    for field in (
        "evidence_cutoff_sha256",
        "round_evidence_package_sha256",
        "researcher_memory_pack_file_sha256",
        "evidence_binding_sha256",
    ):
        _require_sha(binding[field], field)
    expected = domain_hash(
        "HUMAN_REFERENCE_EVIDENCE_BINDING_V1",
        dict(binding),
        excluded_field="evidence_binding_sha256",
    )
    if binding["evidence_binding_sha256"] != expected:
        raise ValueError("Human evidence binding hash mismatch")


def validate_pre_against_binding(
    human_pre: Mapping[str, object],
    binding: Mapping[str, object],
) -> None:
    validate_evidence_binding(binding)
    checks = {
        "round_id": binding["round_id"],
        "policy_version": binding["parent_policy_id"],
        "evidence_cutoff": binding["evidence_cutoff_sha256"],
        "round_evidence_package_sha256": binding[
            "round_evidence_package_sha256"
        ],
    }
    for field, expected in checks.items():
        if human_pre.get(field) != expected:
            raise ValueError(
                f"Human PRE {field} differs from frozen evidence binding"
            )


def freeze_pre(
    input_payload: Mapping[str, object],
    output_dir: Path,
    *,
    evidence_binding: Mapping[str, object],
) -> dict[str, object]:
    assert_artifact_domain(input_payload, HUMAN)
    validate_pre_against_binding(input_payload, evidence_binding)
    output_dir.mkdir(parents=True, exist_ok=False)
    pre_path = output_dir / "HUMAN_RESEARCHER_PRE_V1.json"
    result = freeze_human_pre(input_payload, pre_path)
    receipt = {
        "schema_id": "HUMAN_RESEARCHER_PRE_FREEZE_RECEIPT_V1",
        "round_id": result["round_id"],
        "human_pre_record_sha256": result["pre_record_sha256"],
        "evidence_cutoff": result["evidence_cutoff"],
        "round_evidence_package_sha256": result[
            "round_evidence_package_sha256"
        ],
        "researcher_memory_pack_file_sha256": evidence_binding[
            "researcher_memory_pack_file_sha256"
        ],
        "evidence_binding_sha256": evidence_binding[
            "evidence_binding_sha256"
        ],
        "human_pre_content_hidden_from_strong_pre_shadow": True,
    }
    receipt["receipt_sha256"] = domain_hash(
        "HUMAN_RESEARCHER_PRE_FREEZE_RECEIPT_V1", receipt
    )
    _write_new(
        output_dir / "HUMAN_RESEARCHER_PRE_FREEZE_RECEIPT_V1.json",
        receipt,
    )
    return result


def build_pre_shadow_projection(
    *,
    round_evidence: Mapping[str, object],
    memory_pack: Mapping[str, object],
    expected_round_evidence_package_sha256: str,
    expected_memory_pack_file_sha256: str,
    observed_memory_pack_file_sha256: str,
) -> dict[str, object]:
    assert_artifact_domain(round_evidence, HUMAN)
    assert_artifact_domain(memory_pack, HUMAN)
    observed_round = domain_hash(
        "ROUND_EVIDENCE_PACKAGE_V1",
        round_evidence,
        excluded_field="round_evidence_package_sha256",
    )
    if observed_round != expected_round_evidence_package_sha256:
        raise ValueError("Round Evidence Package differs from Human PRE binding")
    if observed_memory_pack_file_sha256 != expected_memory_pack_file_sha256:
        raise ValueError("Researcher Memory pack differs from Human PRE binding")
    return {
        "round_evidence_package_sha256": observed_round,
        "round_evidence_package": dict(round_evidence),
        "researcher_memory_pack_file_sha256": observed_memory_pack_file_sha256,
        "researcher_memory_pack": dict(memory_pack),
    }


def build_f0f1_handoff(
    *, human_pre: Mapping[str, object], portfolio_payload: Mapping[str, object]
) -> dict[str, object]:
    assert_artifact_domain(human_pre, HUMAN)
    assert_artifact_domain(portfolio_payload, HUMAN)
    portfolio = ResearchRepairPortfolioV1.from_dict(portfolio_payload)
    portfolio.validate()
    if portfolio.round_id != human_pre["round_id"]:
        raise ValueError("repair portfolio round differs from Human PRE")
    if portfolio.parent_policy_id != human_pre["policy_version"]:
        raise ValueError("repair portfolio parent policy differs from Human PRE")
    if portfolio.evidence_cutoff_sha256 != human_pre["evidence_cutoff"]:
        raise ValueError("repair portfolio evidence cutoff differs from Human PRE")
    if portfolio.decision.value != "SELECT_ONE_PROGRAM":
        raise ValueError("Human reference round cannot execute F0/F1 after ABSTAIN")
    if portfolio.principal_change_id != human_pre["single_principal_change"]:
        raise ValueError("repair portfolio principal change differs from Human PRE")
    selected = next(
        program
        for program in portfolio.programs
        if program.program_id == portfolio.selected_program_id
    )
    return {
        "schema_id": "HUMAN_REFERENCE_F0F1_HANDOFF_V1",
        "round_id": human_pre["round_id"],
        "human_pre_record_sha256": human_pre["pre_record_sha256"],
        "evidence_cutoff": human_pre["evidence_cutoff"],
        "round_evidence_package_sha256": human_pre[
            "round_evidence_package_sha256"
        ],
        "parent_policy_id": human_pre["policy_version"],
        "principal_change_id": portfolio.principal_change_id,
        "selected_program": selected.to_dict(),
        "verification_call_budget": portfolio.verification_call_budget,
        "protocol_id": "F0F1_REPAIR_VERIFICATION_V2",
        "reuse_existing_runner": True,
        "new_branch_runner_allowed": False,
        "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
    }


def freeze_post(
    input_payload: Mapping[str, object], output_dir: Path
) -> dict[str, object]:
    assert_artifact_domain(input_payload, HUMAN)
    output_dir.mkdir(parents=True, exist_ok=False)
    return freeze_human_post(
        input_payload, output_dir / "HUMAN_RESEARCHER_POST_V1.json"
    )


def freeze_round_manifest(
    input_payload: Mapping[str, object], output: Path
) -> dict[str, object]:
    assert_artifact_domain(input_payload, HUMAN)
    return freeze_reference_round_manifest(input_payload, output)
