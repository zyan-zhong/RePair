from __future__ import annotations
import hashlib
import pytest

from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.human_reference_round import (
    build_pre_shadow_projection,
    validate_evidence_binding,
)


def _binding(round_payload: dict[str, object], memory_bytes: bytes):
    binding = {
        "schema_id": "HUMAN_REFERENCE_EVIDENCE_BINDING_V1",
        "round_id": "r",
        "parent_policy_id": "p",
        "evidence_cutoff_sha256": "a" * 64,
        "round_evidence_package_sha256": domain_hash(
            "ROUND_EVIDENCE_PACKAGE_V1", round_payload
        ),
        "researcher_memory_pack_file_sha256": hashlib.sha256(
            memory_bytes
        ).hexdigest(),
        "evidence_binding_sha256": "0" * 64,
    }
    binding["evidence_binding_sha256"] = domain_hash(
        "HUMAN_REFERENCE_EVIDENCE_BINDING_V1",
        binding,
        excluded_field="evidence_binding_sha256",
    )
    return binding


def test_shadow_projection_contains_actual_researcher_memory():
    round_payload = {"schema_id": "ROUND_EVIDENCE_PACKAGE_V1", "x": 1}
    memory = {"schema_id": "RESEARCHER_MEMORY_PACK_V1", "records": ["m"]}
    memory_bytes = b'{"records":["m"],"schema_id":"RESEARCHER_MEMORY_PACK_V1"}\n'
    binding = _binding(round_payload, memory_bytes)
    projection = build_pre_shadow_projection(
        round_evidence=round_payload,
        memory_pack=memory,
        expected_round_evidence_package_sha256=binding[
            "round_evidence_package_sha256"
        ],
        expected_memory_pack_file_sha256=binding[
            "researcher_memory_pack_file_sha256"
        ],
        observed_memory_pack_file_sha256=hashlib.sha256(
            memory_bytes
        ).hexdigest(),
    )
    assert projection["researcher_memory_pack"] == memory
    assert "human_pre" not in str(projection).lower()


def test_shadow_projection_rejects_wrong_round_evidence():
    round_payload = {"schema_id": "ROUND_EVIDENCE_PACKAGE_V1", "x": 1}
    memory = {"schema_id": "RESEARCHER_MEMORY_PACK_V1"}
    with pytest.raises(ValueError, match="Round Evidence"):
        build_pre_shadow_projection(
            round_evidence=round_payload,
            memory_pack=memory,
            expected_round_evidence_package_sha256="b" * 64,
            expected_memory_pack_file_sha256="c" * 64,
            observed_memory_pack_file_sha256="c" * 64,
        )


def test_evidence_binding_hash_is_fail_closed():
    round_payload = {"schema_id": "ROUND_EVIDENCE_PACKAGE_V1"}
    binding = _binding(round_payload, b"x")
    validate_evidence_binding(binding)
    broken = dict(binding)
    broken["evidence_cutoff_sha256"] = "d" * 64
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_evidence_binding(broken)
