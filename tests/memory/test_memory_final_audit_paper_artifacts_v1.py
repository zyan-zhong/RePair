from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import sys

import pytest

from pchsi.evaluation.canonical_evidence import canonical_json_bytes


SCRIPT = (
    Path(__file__).parents[2]
    / "scripts/memory/audit_memory_final_result_candidate_v1.py"
)


def _load():
    spec = importlib.util.spec_from_file_location(
        "_memory_final_audit_metadata_target",
        SCRIPT,
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _manifest(root: Path) -> Path:
    (root / "paper_tables").mkdir(parents=True)
    (root / "paper_narrative").mkdir(parents=True)
    first = root / "paper_tables/table.csv"
    second = root / "paper_narrative/note.md"
    first.write_text("a,b\\n1,2\\n", encoding="utf-8")
    second.write_text("# note\\n", encoding="utf-8")

    artifacts = []
    for path in (first, second):
        raw = path.read_bytes()
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": hashlib.sha256(raw).hexdigest(),
                "size_bytes": len(raw),
            }
        )

    value = {
        "schema_id": "FAILURE_MEMORY_PAPER_EVIDENCE_MANIFEST_V1",
        "schema_version": 1,
        "fixed_code_head": "f" * 40,
        "scientific_program_sha256": "a" * 64,
        "source_authorities": {},
        "generated_artifacts": artifacts,
        "claim_statuses": {
            "Q1": "NOT_SUPPORTED",
            "Q2": "NOT_SUPPORTED",
            "Q3": "NOT_SUPPORTED",
            "Q4": "OPEN",
            "Q5": "DEFERRED_OPTIONAL_EXTENSION",
        },
        "paper_evidence_manifest_sha256": "0" * 64,
    }
    value["paper_evidence_manifest_sha256"] = hashlib.sha256(
        b"FAILURE_MEMORY_PAPER_EVIDENCE_MANIFEST_V1\0"
        + canonical_json_bytes(
            {
                key: item
                for key, item in value.items()
                if key != "paper_evidence_manifest_sha256"
            }
        )
    ).hexdigest()

    manifest = root / "PAPER_EVIDENCE_MANIFEST_V1.json"
    manifest.write_bytes(canonical_json_bytes(value))
    return manifest


def test_paper_evidence_count_uses_generated_artifacts_and_verifies_files(
    tmp_path: Path,
) -> None:
    module = _load()
    manifest = _manifest(tmp_path)
    value = module.object_value(manifest)

    assert module.validate_paper_evidence_manifest_v1(
        paper_manifest_path=manifest,
        paper=value,
        expected_fixed_head="f" * 40,
        expected_scientific_program_sha256="a" * 64,
    ) == 2


def test_paper_evidence_validator_rejects_artifact_sha_mismatch(
    tmp_path: Path,
) -> None:
    module = _load()
    manifest = _manifest(tmp_path)
    value = module.object_value(manifest)

    target = tmp_path / "paper_tables/table.csv"
    target.write_text("changed\\n", encoding="utf-8")

    with pytest.raises(
        SystemExit,
        match="AUDIT_CANDIDATE_PAPER_ARTIFACT_SHA",
    ):
        module.validate_paper_evidence_manifest_v1(
            paper_manifest_path=manifest,
            paper=value,
            expected_fixed_head="f" * 40,
            expected_scientific_program_sha256="a" * 64,
        )
