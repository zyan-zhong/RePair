from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pytest

from pchsi.memory.scientific_program import (
    ScientificQuestionEvidenceRowV1,
    ScientificQuestionMatrixV1,
    ScientificQuestionStatusV1,
)

ROOT = Path(__file__).parents[2]


def _load(name: str, relative: str):
    path = ROOT / relative
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _matrix() -> dict[str, object]:
    statuses = (
        ScientificQuestionStatusV1.NOT_SUPPORTED,
        ScientificQuestionStatusV1.NOT_SUPPORTED,
        ScientificQuestionStatusV1.NOT_SUPPORTED,
        ScientificQuestionStatusV1.OPEN,
        ScientificQuestionStatusV1.DEFERRED_OPTIONAL_EXTENSION,
    )
    rows = tuple(
        ScientificQuestionEvidenceRowV1(
            question_id=f"Q{index}",
            status=status,
            authorized_summary=f"summary-{index}",
            evidence_sha256s=("a" * 64,),
            forbidden_claims=("NO_OVERCLAIM",),
            required_next_authorities=(),
        )
        for index, status in enumerate(statuses, 1)
    )
    return ScientificQuestionMatrixV1(rows=rows).to_dict()


def _consumers():
    return (
        _load(
            "_paper_matrix_consumer",
            "scripts/memory/export_memory_paper_evidence_v2.py",
        ),
        _load(
            "_handoff_matrix_consumer",
            "scripts/memory/build_memory_q4_q5_handoff_v1.py",
        ),
    )


def test_writer_matrix_is_accepted_by_all_closure_consumers() -> None:
    value = _matrix()
    for module in _consumers():
        module.validate_matrix(dict(value))


def test_closure_consumers_reject_unbound_matrix_fields() -> None:
    value = _matrix()
    value["unexpected_unbound_field"] = True

    for module in _consumers():
        with pytest.raises(
            SystemExit,
            match="Q1_Q5_MATRIX_FIELDS",
        ):
            module.validate_matrix(dict(value))


def test_closure_consumers_reject_wrong_completion_rule() -> None:
    value = _matrix()
    value["scientific_completion_rule"] = "WRONG"

    import hashlib
    from pchsi.evaluation.canonical_evidence import canonical_json_bytes

    payload = {
        "rows": value["rows"],
        "scientific_completion_rule": value["scientific_completion_rule"],
    }
    value["matrix_sha256"] = hashlib.sha256(
        b"FAILURE_MEMORY_Q1_Q5_MATRIX_V1\0"
        + canonical_json_bytes(payload)
    ).hexdigest()

    for module in _consumers():
        with pytest.raises(
            SystemExit,
            match="Q1_Q5_MATRIX_COMPLETION_RULE",
        ):
            module.validate_matrix(dict(value))
