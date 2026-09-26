from __future__ import annotations

import importlib.util
from pathlib import Path

from pchsi.memory.dev_descriptive_snapshot_v2 import (
    build_calibrated_snapshot_v2,
    publish_calibrated_snapshot_v2,
)
from pchsi.memory.matched_raw_view import (
    build_fm1_matched_raw_episodic_view_v1,
)
from pchsi.memory.policy_projection import (
    build_failure_memory_policy_projection_v1,
)
from pchsi.memory.projection_common import (
    ProjectionClassV1,
)
from pchsi.memory.retrieval_key import (
    build_memory_retrieval_key_v1,
)
from pchsi.memory.semantic_recovery import (
    SemanticAnnotationTypeV1,
)
from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
    FM1_LLM_COMPRESSION_POLICY,
    FM1_POSTHOC_EXCERPT_POLICY,
    FM1_TRUNCATION_POLICY,
    LIBRARY_TOTAL_CANDIDATES_V1,
    SINGLE_RECORD_CANDIDATES_V1,
    TOKEN_BUDGET_SCHEMA_V1,
)


class TinyTokenizer:
    tokenizer_id = "PACKAGE_B_TEST_TOKENIZER"
    tokenizer_revision = "f" * 64

    def count_tokens(self, text: str) -> int:
        return max(1, len(text) // 100)


def load_policy_projection_helpers():
    path = Path(
        "tests/memory/test_failure_memory_policy_projection.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_package_b_policy_projection_helpers",
        path,
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def record_experience_fm1_fm2():
    helpers = load_policy_projection_helpers()

    record = helpers._record(
        semantic=(
            helpers._annotation(
                SemanticAnnotationTypeV1.CANDIDATE_MECHANISM,
                "visible failure mechanism",
                "ANN-PB-1",
            ),
        )
    )
    experience = helpers._helpers()._experience()

    tokenizer = TinyTokenizer()

    fm1 = build_fm1_matched_raw_episodic_view_v1(
        record=record,
        experience=experience,
        tokenizer=tokenizer,
        hard_ceiling=640,
    )
    fm2 = build_failure_memory_policy_projection_v1(
        record=record,
        projection_class=ProjectionClassV1.FM2,
        tokenizer=tokenizer,
        hard_ceiling=640,
    )
    key = build_memory_retrieval_key_v1(record)
    return record, experience, key, fm1, fm2, tokenizer


def token_budget_contract():
    return FailureMemoryTokenBudgetContractV1(
        schema_id=TOKEN_BUDGET_SCHEMA_V1,
        schema_version=1,
        source_panel_manifest_sha256="1" * 64,
        calibration_failure_panel_sha256="2" * 64,
        analyzer_prompt_sha256="3" * 64,
        analyzer_model="gpt-5.6-sol",
        tokenizer_id=TinyTokenizer.tokenizer_id,
        tokenizer_revision=TinyTokenizer.tokenizer_revision,
        calibration_failure_count=30,
        valid_calibration_record_count=20,
        fm1_token_counts=(600,) * 20,
        fm2_token_counts=(180,) * 20,
        library_pack_token_counts=(700,) * 6,
        single_record_candidates=SINGLE_RECORD_CANDIDATES_V1,
        library_total_candidates=LIBRARY_TOTAL_CANDIDATES_V1,
        coverage_target=0.90,
        single_record_hard_ceiling=640,
        library_total_hard_ceiling=768,
        max_record_count=3,
        fm1_truncation_policy=FM1_TRUNCATION_POLICY,
        fm1_llm_compression_policy=FM1_LLM_COMPRESSION_POLICY,
        fm1_posthoc_excerpt_policy=FM1_POSTHOC_EXCERPT_POLICY,
        performance_estimand="NO_PERFORMANCE_ESTIMAND",
        memory_on_execution_used=False,
        contract_sha256=None,
    )


def published_snapshot(tmp_path):
    record, experience, key, fm1, fm2, tokenizer = (
        record_experience_fm1_fm2()
    )
    contract = token_budget_contract()

    snapshot, files = build_calibrated_snapshot_v2(
        package_a_sealed_head="d" * 40,
        historical_package_a_snapshot_sha256="e" * 64,
        token_budget_contract=contract,
        source_materialization_manifest_sha256="a" * 64,
        member_artifacts=(
            (
                record.canonical_bytes(),
                key.canonical_bytes(),
                fm1.canonical_bytes(),
                fm2.canonical_bytes(),
            ),
        ),
    )

    root = tmp_path / "snapshot-root"
    root.mkdir()
    final = publish_calibrated_snapshot_v2(
        output_root=root,
        snapshot=snapshot,
        member_files=files,
    )
    contract_path = tmp_path / "token-budget.json"
    contract_path.write_bytes(contract.canonical_bytes())

    return final, snapshot, contract, contract_path, tokenizer
