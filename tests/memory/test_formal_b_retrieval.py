from __future__ import annotations

from dataclasses import replace
from fractions import Fraction
import importlib
import importlib.util

import pytest

from pchsi.evaluation.raw_policy_prompt import ExecutedTransition
from pchsi.memory.applicability import (
    ApplicabilityBoundarySetV1,
    BoundaryTypeV1,
)
from pchsi.memory.retrieval_key import (
    MemoryRetrievalKeyV1,
    MemoryRetrievalScoringPayloadV1,
)


TARGET = "pchsi.memory.formal_b_retrieval"


def _load_target():
    spec = importlib.util.find_spec(TARGET)
    if spec is None:
        pytest.fail("FORMAL_B_B1_RED_MISSING_RETRIEVAL_EVALUATOR")
    return importlib.import_module(TARGET)


def _helpers():
    path = "tests/memory/package_b_direct_test_helpers.py"
    spec = importlib.util.spec_from_file_location("_formal_b_helpers", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _candidate(text: str, *, lineage_char: str = "1"):
    target = _load_target()
    record, _, key, _, _, _ = _helpers().record_experience_fm1_fm2()

    scoring = MemoryRetrievalScoringPayloadV1(
        required_feedback_codes=(),
        forbidden_feedback_codes=(),
        recent_action_repetition_signature=(),
        recent_nonexecuted_attempt_signature=(),
        visible_state_change_signature=(),
        required_visible_markers=(),
        forbidden_visible_markers=(),
        semantic_retrieval_text=text,
    )
    from pchsi.evaluation.canonical_evidence import (
        canonical_json_bytes,
        sha256_bytes,
    )
    key2 = MemoryRetrievalKeyV1(
        schema_id="MEMORY_RETRIEVAL_KEY_V1",
        schema_version=1,
        record_binding=key.record_binding,
        hard_filter_metadata=key.hard_filter_metadata,
        scoring_payload=scoring,
        scoring_payload_sha256=sha256_bytes(
            canonical_json_bytes(scoring.to_dict())
        ),
    )
    return target.FormalBCandidateV1(record=record, retrieval_key=key2)


def _query(
    pool,
    *,
    group: str,
    observation: str,
    gold_lineage: str | None,
    gold_char: str,
):
    target = _load_target()
    if gold_lineage is None:
        gold = target.FormalBGoldTargetV1(
            target.FormalBGoldDispositionV1.ABSTAIN_NO_APPLICABLE_MEMORY,
            None,
        )
    else:
        gold = target.FormalBGoldTargetV1(
            target.FormalBGoldDispositionV1.EXPOSE_CORRECT_MEMORY,
            gold_lineage,
        )
    return target.FormalBQueryV1(
        pool=pool,
        task_gamefile_group_id=group,
        observation=observation,
        executed_transitions=(
            ExecutedTransition("look", "activation visible failure mechanism"),
        ),
        admissible_commands=("look", "inventory"),
        interface_feedback=None,
        gold_target=gold,
        independent_gold_artifact_sha256=gold_char * 64,
    )


def test_b1_casefold_word_jaccard_and_query_visibility():
    target = _load_target()
    assert target.casefold_word_tokens_v1("Straße FOO") == frozenset(
        {"strasse", "foo"}
    )
    assert target.jaccard_score_v1("A B", "a c") == Fraction(1, 3)

    candidate = _candidate("activation visible failure mechanism")
    query = _query(
        target.FormalBPoolV1.RETRIEVER_CALIBRATION_DEV,
        group="g-cal",
        observation="ACTIVATION visible",
        gold_lineage=candidate.record.memory_lineage_id,
        gold_char="a",
    )
    scoring_text = target.build_formal_b_query_scoring_text_v1(query)
    assert "ACTIVATION visible" in scoring_text
    assert "look" in scoring_text
    assert "inventory" not in scoring_text
    assert "g-cal" not in scoring_text


def test_b1_top_score_tie_abstains_without_record_order_tiebreak():
    target = _load_target()
    c1 = _candidate("same words")
    c2 = _candidate("same words")
    query = _query(
        target.FormalBPoolV1.RETRIEVER_CALIBRATION_DEV,
        group="g-tie",
        observation="same words",
        gold_lineage=c1.record.memory_lineage_id,
        gold_char="b",
    )
    result = target.evaluate_formal_b_query_v1(
        query=query,
        candidates=(c1, c2),
        config=target.FormalBRetrieverConfigV1(threshold_pct=0),
    )
    assert result.exposed_memory_lineage_id is None
    assert result.pre_gate_memory_lineage_id is None
    assert result.decision_reason is target.FormalBDecisionReasonV1.TOP_SCORE_TIE


def test_b1_applicability_gate_is_required_before_exposure():
    target = _load_target()
    candidate = _candidate("activation visible failure mechanism")

    query = _query(
        target.FormalBPoolV1.RETRIEVER_CALIBRATION_DEV,
        group="g-app",
        observation="activation visible failure mechanism",
        gold_lineage=candidate.record.memory_lineage_id,
        gold_char="c",
    )
    exposed = target.evaluate_formal_b_query_v1(
        query=query,
        candidates=(candidate,),
        config=target.FormalBRetrieverConfigV1(threshold_pct=0),
    )
    assert exposed.exposed_memory_lineage_id == candidate.record.memory_lineage_id
    assert exposed.applicability_disposition == "APPLICABLE"

    blocked = replace(
        query,
        observation="activation release visible failure mechanism",
        query_id=None,
    )
    blocked_result = target.evaluate_formal_b_query_v1(
        query=blocked,
        candidates=(candidate,),
        config=target.FormalBRetrieverConfigV1(threshold_pct=0),
    )
    assert blocked_result.exposed_memory_lineage_id is None
    assert blocked_result.applicability_disposition == "CONFLICTING"


def test_b1_pool_isolation_and_gold_are_frozen_before_scoring():
    target = _load_target()
    candidate = _candidate("activation visible failure mechanism")
    lineage = candidate.record.memory_lineage_id

    q1 = _query(
        target.FormalBPoolV1.RETRIEVER_CALIBRATION_DEV,
        group="shared-group",
        observation="activation visible failure mechanism",
        gold_lineage=lineage,
        gold_char="d",
    )
    q2 = _query(
        target.FormalBPoolV1.RETRIEVER_SELECTION_VALIDATION,
        group="shared-group",
        observation="activation visible failure mechanism",
        gold_lineage=lineage,
        gold_char="e",
    )
    with pytest.raises(ValueError, match="overlap"):
        target.FormalBGoldPanelV1(
            active_snapshot_sha256="f" * 64,
            independent_gold_authority_sha256="1" * 64,
            queries=(q1, q2),
        )

    with pytest.raises(ValueError, match="TRAIN_RETRIEVAL_DEV"):
        replace(q1, source_population="valid_seen", query_id=None)


def test_b1_three_stage_selection_is_safety_first_and_stress_is_frozen():
    target = _load_target()
    candidate = _candidate("activation visible failure mechanism")
    lineage = candidate.record.memory_lineage_id

    calibration = (
        _query(
            target.FormalBPoolV1.RETRIEVER_CALIBRATION_DEV,
            group="cal-1",
            observation="activation visible failure mechanism",
            gold_lineage=lineage,
            gold_char="1",
        ),
        _query(
            target.FormalBPoolV1.RETRIEVER_CALIBRATION_DEV,
            group="cal-2",
            observation="irrelevant state",
            gold_lineage=None,
            gold_char="2",
        ),
    )
    validation = (
        _query(
            target.FormalBPoolV1.RETRIEVER_SELECTION_VALIDATION,
            group="val-1",
            observation="activation visible failure mechanism",
            gold_lineage=lineage,
            gold_char="3",
        ),
        _query(
            target.FormalBPoolV1.RETRIEVER_SELECTION_VALIDATION,
            group="val-2",
            observation="irrelevant state",
            gold_lineage=None,
            gold_char="4",
        ),
    )
    stress = (
        _query(
            target.FormalBPoolV1.REGISTERED_SAFETY_STRESS,
            group="stress-1",
            observation="activation visible failure mechanism",
            gold_lineage=lineage,
            gold_char="5",
        ),
        _query(
            target.FormalBPoolV1.REGISTERED_SAFETY_STRESS,
            group="stress-2",
            observation="release unrelated",
            gold_lineage=None,
            gold_char="6",
        ),
    )
    panel = target.FormalBGoldPanelV1(
        active_snapshot_sha256="a" * 64,
        independent_gold_authority_sha256="b" * 64,
        queries=calibration + validation + stress,
    )
    result = target.run_formal_b_three_stage_protocol_v1(
        panel=panel,
        candidates=(candidate,),
    )
    assert len(result.calibration_reports) == 11
    assert len(result.calibration_candidate_threshold_pcts) == 3
    assert result.selected_config.threshold_pct in (
        result.calibration_candidate_threshold_pcts
    )
    assert result.stress_report.config == result.selected_config
    summary = result.to_summary_dict()
    assert summary["causal_benefit_harm_authority"] is False
    assert summary["applicability_gold_role"] == (
        "DIAGNOSTIC_SAFETY_AUTHORITY_ONLY"
    )
    assert summary["valid_seen_allowed"] is False
    assert summary["valid_unseen_allowed"] is False
