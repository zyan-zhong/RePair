from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from common import ContractError
from renderer_adapter_core import (
    build_t2_source_adapter_row,
    canonical_action_json,
    mask_prompt_prefix,
    validate_historical_source_row,
)


class AdapterContractTests(unittest.TestCase):
    def test_historical_schema_input_target_contract(self):
        row = {
            "schema_id": "D_Q2_BAD_V1_TRAINING_EXAMPLE",
            "input": {
                "prompt_text": "RAW_POLICY_PROMPT_V1\nX",
                "prompt_sha256": "9b97f59ae12bf30b2df1d20d983c9b7d5b0315446e49b80b99fc34aba0b783e7",
            },
            "target": {
                "exact_action": "look",
                "action_json": '{"action":"look"}',
                "target_sha256": "69352e74c97d8901c41d277eff432d4e085584f51ef169287404866583bb518d",
            },
        }
        # hashes above are intentionally not trusted in this synthetic test.
        import hashlib
        row["input"]["prompt_sha256"] = hashlib.sha256(
            row["input"]["prompt_text"].encode()
        ).hexdigest()
        row["target"]["target_sha256"] = hashlib.sha256(
            row["target"]["action_json"].encode()
        ).hexdigest()
        prompt, target = validate_historical_source_row(row)
        self.assertEqual(prompt, "RAW_POLICY_PROMPT_V1\nX")
        self.assertEqual(target, '{"action":"look"}')

    def test_action_json_is_canonical(self):
        self.assertEqual(canonical_action_json("go to desk 1"), '{"action":"go to desk 1"}')

    def test_prompt_prefix_masking(self):
        self.assertEqual(
            mask_prompt_prefix([1,2,3,4,5], [1,2,3]),
            [-100,-100,-100,4,5],
        )

    def test_t2_adapter_keeps_hindsight_out_of_input_and_target(self):
        semantic = {
            "schema_id": "POLICY_SEMANTIC_TRAINING_ROW_V1",
            "row_sha256": "a"*64,
            "arm_id": "T2",
            "source_state_sha256": "b"*64,
            "diagnostic_only": True,
            "verified_positive": False,
            "promotion_eligible": False,
            "terminal_effect": "NEUTRAL",
            "mechanical_effect": "OBSERVABLE_LOCAL_TRANSITION_NO_TERMINAL_RESCUE",
            "primary_training_route": "PROCEDURAL_CONTINUATION_CANDIDATE",
            "policy_visible_context": {
                "source_prompt_text": "RAW_POLICY_PROMPT_V1\nHELLO",
                "source_prompt_bound": True,
                "admissible_commands": ["look", "go to desk 1"],
            },
            "target_action": "look",
        }
        out = build_t2_source_adapter_row(semantic, 0)
        visible = json.dumps(
            {"input": out["input"], "target": out["target"]},
            ensure_ascii=False,
        )
        self.assertNotIn("NEUTRAL", visible)
        self.assertNotIn("PROCEDURAL_CONTINUATION", visible)
        self.assertEqual(out["provenance"]["hindsight_visible_to_policy"], False)

    def test_strong_takeover_normative_bridge_is_inherited_not_recomputed(self):
        env = (ROOT / "PACKAGE_ENV.sh").read_text(encoding="utf-8")
        self.assertIn("EXPECTED_V16_NORMATIVE_BRIDGE_SHA256", env)
        mainline = (
            ROOT / "tools" / "build_chinese_mainline_and_preflight.py"
        ).read_text(encoding="utf-8")
        self.assertIn("继承规范与 teacher traces；重置 fresh-round 答案", mainline)
        self.assertIn("strong_takeover_execution_ready", mainline.lower())


if __name__ == "__main__":
    unittest.main()
