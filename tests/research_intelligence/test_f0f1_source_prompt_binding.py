from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

from pchsi.evaluation.budget import BudgetState
from pchsi.memory.memory_runtime_bridge import prepare_memory_policy_attempt_v1

ROOT = Path(__file__).resolve().parents[2]
RUNNER = ROOT / "scripts/research_intelligence/run_human_reference_f0f1_branch_v2.py"

spec = importlib.util.spec_from_file_location("_f0f1_source_prompt_runner", RUNNER)
runner = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(runner)


def _prepared():
    return prepare_memory_policy_attempt_v1(
        public_task_goal="put the object away",
        observation="You are in a room.",
        executed_transitions=(),
        memory_payloads=(),
        policy_visible_commands=("look",),
        harness_visible_commands=("look",),
        environment_commands=("look",),
        interface_feedback=None,
        budget_state=BudgetState(
            policy_attempt_count=0,
            environment_step_count=0,
            protocol_failure_count=0,
            inadmissible_action_count=0,
            consecutive_nonexecuted_attempt_count=0,
        ),
        snapshot_sha256="1" * 64,
        token_budget_contract_sha256="2" * 64,
        retrieval_mode="NO_RETRIEVAL",
        branch_role="HUMAN_REFERENCE_F0F1_F0",
        representation_class="M0",
        memory_lineage_id=None,
        record_version=None,
        projection_artifact_sha256=None,
        packed_token_count=0,
    )


def test_source_raw_prompt_binder_api_exists():
    assert hasattr(runner, "_bind_source_raw_m0_prompt_v1"), "MISSING_SOURCE_RAW_PROMPT_BINDER"


def test_source_raw_prompt_binder_removes_memory_wrapper_and_rehashes_exposure():
    prepared = _prepared()
    rebound = runner._bind_source_raw_m0_prompt_v1(
        prepared,
        public_task_goal="put the object away",
        observation="You are in a room.",
        executed_transitions=(),
        admissible_commands=("look",),
        interface_feedback=None,
    )
    assert rebound.precondition == prepared.precondition
    assert rebound.prompt.startswith("RAW_POLICY_PROMPT_V1\n")
    assert "MEMORY_AUGMENTED_RAW_POLICY_PROMPT_V1" not in rebound.prompt
    assert "RETRIEVED_FAILURE_EXPERIENCES_JSON=" not in rebound.prompt
    assert rebound.exposure is not None
    assert rebound.exposure.representation_class == "M0"
    assert rebound.exposure.memory_lineage_id is None
    assert rebound.exposure.final_prompt_sha256 == hashlib.sha256(
        rebound.prompt.encode("utf-8")
    ).hexdigest()
    assert rebound.exposure.exposure_sha256 != prepared.exposure.exposure_sha256


def test_runner_keeps_existing_runtime_processing_and_no_action_repair():
    text = RUNNER.read_text(encoding="utf-8")
    assert "process_memory_policy_generation_v1(" in text
    assert "parse_raw_policy_response" not in text
    helper = text[text.index("def _bind_source_raw_m0_prompt_v1"):text.index("def _failure_payload")]
    assert ".strip(" not in helper
    assert ".replace(" not in helper


def test_first_f0_call_binds_registered_base_policy_input_hash():
    text = RUNNER.read_text(encoding="utf-8")
    assert "source.base_policy_input_sha256" in text
    assert "F0 source prompt differs from registered base policy input" in text
