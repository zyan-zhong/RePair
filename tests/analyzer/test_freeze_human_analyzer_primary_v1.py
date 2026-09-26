from __future__ import annotations

import importlib.util
import json
from pathlib import Path


def _load(repo: Path):
    path = repo / "scripts/analyzer/freeze_human_analyzer_primary_v1.py"
    spec = importlib.util.spec_from_file_location("freeze_human_analyzer_primary_v1", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_human_freeze_delegates_to_existing_stage_validator_and_keeps_shadow_blind(tmp_path: Path, monkeypatch) -> None:
    repo = Path(__file__).resolve().parents[2]
    module = _load(repo)
    projection = tmp_path / "projection.json"
    draft = tmp_path / "draft.json"
    result = tmp_path / "result.json"
    receipt = tmp_path / "receipt.json"
    projection.write_text(json.dumps({"evidence_pack": {"evidence_pack_sha256": "a" * 64}}), encoding="utf-8")
    draft.write_text(json.dumps({"human": "draft"}), encoding="utf-8")

    observed = {}

    def fake_validate_stage_output(*, stage_id, text, raw_response_sha256, projection):
        observed.update(
            stage_id=stage_id,
            text=text,
            raw_response_sha256=raw_response_sha256,
            projection=projection,
        )
        return {
            "schema_id": "ANALYZER_LOCAL_RESULT_V2",
            "schema_version": 2,
            "local_result_sha256": "b" * 64,
        }

    monkeypatch.setattr(module, "validate_stage_output", fake_validate_stage_output)
    finalized, frozen = module.freeze_human_analyzer_primary(
        stage_id="L-A0",
        round_id="CLEAN-HUMAN-REFERENCE-R1-PI0",
        policy_version="PI0_CLEAN",
        unit_identity_sha256="c" * 64,
        projection_path=projection,
        human_draft_path=draft,
        output_result_path=result,
        output_receipt_path=receipt,
    )

    assert finalized["local_result_sha256"] == "b" * 64
    assert observed["stage_id"] == "L-A0"
    assert observed["projection"]["evidence_pack"]["evidence_pack_sha256"] == "a" * 64
    assert len(observed["raw_response_sha256"]) == 64
    assert frozen["actor"] == "HUMAN"
    assert frozen["authority"] == "PRIMARY"
    assert frozen["strong_shadow_human_content_visible"] is False
    assert frozen["strong_shadow_human_hash_visible"] is False
    assert frozen["benchmark_result_values_consumed"] is False
    assert frozen["historical_semantic_artifact_consumed"] is False
    assert result.is_file() and receipt.is_file()
