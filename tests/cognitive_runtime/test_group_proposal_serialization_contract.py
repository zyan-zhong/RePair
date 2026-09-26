from __future__ import annotations

import hashlib
import json
from pathlib import Path

from pchsi.cognitive_runtime.manifest import load_runtime_manifest


ROOT = Path(__file__).resolve().parents[2]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_g_v4_prompts_freeze_mutually_exclusive_proposal_encoding() -> None:
    for stage in ("A2", "A3"):
        path = ROOT / f"prompts/cognitive_runtime/ANALYZER_G_{stage}_PROMPT_V4.txt"
        text = path.read_text(encoding="utf-8")
        assert "Proposal serialization is mutually exclusive" in text
        assert "option_actions MUST be []" in text
        assert "termination_condition MUST be null" in text
        assert "exact_action MUST be null" in text
        assert "option_actions MUST contain 1-4 action strings" in text


def test_provider_group_schema_documents_same_semantic_contract() -> None:
    path = ROOT / "configs/analyzer/schemas/analyzer_group_result_v2.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    props = schema["properties"]["source_conditioned_proposals"]["items"]["properties"]
    assert "exact-action proposal" in props["exact_action"]["description"]
    assert "empty array" in props["option_actions"]["description"]
    assert "MUST be null" in props["termination_condition"]["description"]


def test_canonical_proposal_schema_documents_same_semantic_contract() -> None:
    path = ROOT / "configs/analyzer/schemas/analyzer_source_conditioned_proposal_v1.json"
    schema = json.loads(path.read_text(encoding="utf-8"))
    props = schema["properties"]
    assert "exact-action proposal" in props["exact_action"]["description"]
    assert "empty array" in props["option_actions"]["description"]
    assert "short-option proposal" in props["termination_condition"]["description"]


def test_runtime_manifest_pins_v4_prompts_and_updated_group_schema() -> None:
    manifest = load_runtime_manifest()
    rows = {row["stage_id"]: row for row in manifest["stage_rows"]}
    schema_path = ROOT / "configs/analyzer/schemas/analyzer_group_result_v2.json"
    schema_sha = _sha(schema_path)
    for stage in ("G-A2", "G-A3"):
        row = rows[stage]
        assert row["prompt_template_id"].endswith("_V4")
        prompt_path = ROOT / row["prompt_relative_path"]
        assert prompt_path.is_file()
        assert row["prompt_sha256"] == _sha(prompt_path)
        assert row["output_schema_sha256"] == schema_sha
