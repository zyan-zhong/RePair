#!/usr/bin/env python3
"""Validate one external component artifact against a Memory V1 port."""

from __future__ import annotations

import argparse
from pathlib import Path

from pchsi.evaluation.canonical_evidence import strict_json_loads
from pchsi.memory.component_ports import (
    AnalyzerProposalIngressV1,
    AnalyzerRepairProposalV1,
    MemoryEvidenceRefV1,
    MemoryPortAuthorityV1,
    ResearcherMemoryEvidenceExportV1,
    SameStateVerifierIngressV1,
    VerifierEffectV1,
)


def _object(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError("artifact must be regular non-symlink file")
    value = strict_json_loads(path.read_bytes())
    if not isinstance(value, dict):
        raise TypeError("artifact must be object")
    return value


def _analyzer(value: dict[str, object]) -> AnalyzerProposalIngressV1:
    expected = {
        "schema_id", "schema_version", "failure_instance_sha256",
        "source_state_sha256", "analyzer_condition",
        "factual_evidence_refs", "semantic_hypothesis_refs",
        "counterevidence_refs", "historical_memory_view_sha256",
        "repair_proposals", "abstained", "authority_boundary",
        "ingress_sha256",
    }
    if set(value) != expected:
        raise ValueError("Analyzer ingress fields mismatch")
    if value["schema_id"] != "ANALYZER_PROPOSAL_INGRESS_V1" or value[
        "schema_version"
    ] != 1:
        raise ValueError("Analyzer ingress schema mismatch")
    return AnalyzerProposalIngressV1(
        failure_instance_sha256=value["failure_instance_sha256"],
        source_state_sha256=value["source_state_sha256"],
        analyzer_condition=value["analyzer_condition"],
        factual_evidence_refs=tuple(
            MemoryEvidenceRefV1.from_dict(item)
            for item in value["factual_evidence_refs"]
        ),
        semantic_hypothesis_refs=tuple(
            MemoryEvidenceRefV1.from_dict(item)
            for item in value["semantic_hypothesis_refs"]
        ),
        counterevidence_refs=tuple(
            MemoryEvidenceRefV1.from_dict(item)
            for item in value["counterevidence_refs"]
        ),
        historical_memory_view_sha256=value[
            "historical_memory_view_sha256"
        ],
        repair_proposals=tuple(
            AnalyzerRepairProposalV1.from_dict(item)
            for item in value["repair_proposals"]
        ),
        abstained=value["abstained"],
        ingress_sha256=value["ingress_sha256"],
    )


def _verifier(value: dict[str, object]) -> SameStateVerifierIngressV1:
    expected = {
        "schema_id", "schema_version", "failure_instance_sha256",
        "candidate_sha256", "source_state_sha256",
        "f0_evidence_sha256", "f1_evidence_sha256",
        "policy_identity_sha256", "environment_identity_sha256",
        "effect", "f0_terminal_success", "f1_terminal_success",
        "scientific_execution_complete", "effect_authority",
        "ingress_sha256",
    }
    if set(value) != expected:
        raise ValueError("Verifier ingress fields mismatch")
    if value["schema_id"] != "SAME_STATE_VERIFIER_INGRESS_V1" or value[
        "schema_version"
    ] != 1:
        raise ValueError("Verifier ingress schema mismatch")
    return SameStateVerifierIngressV1(
        failure_instance_sha256=value["failure_instance_sha256"],
        candidate_sha256=value["candidate_sha256"],
        source_state_sha256=value["source_state_sha256"],
        f0_evidence_sha256=value["f0_evidence_sha256"],
        f1_evidence_sha256=value["f1_evidence_sha256"],
        policy_identity_sha256=value["policy_identity_sha256"],
        environment_identity_sha256=value["environment_identity_sha256"],
        effect=VerifierEffectV1(value["effect"]),
        f0_terminal_success=value["f0_terminal_success"],
        f1_terminal_success=value["f1_terminal_success"],
        scientific_execution_complete=value["scientific_execution_complete"],
        ingress_sha256=value["ingress_sha256"],
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kind",
        choices=("analyzer", "verifier"),
        required=True,
    )
    parser.add_argument("--artifact", required=True)
    args = parser.parse_args()
    value = _object(Path(args.artifact))
    parsed = _analyzer(value) if args.kind == "analyzer" else _verifier(value)
    print("MEMORY_COMPONENT_PORT_VALIDATION_PASS")
    print("KIND=" + args.kind.upper())
    print(
        "ARTIFACT_SHA256="
        + (
            parsed.ingress_sha256
            if hasattr(parsed, "ingress_sha256")
            else ""
        )
    )


if __name__ == "__main__":
    main()
