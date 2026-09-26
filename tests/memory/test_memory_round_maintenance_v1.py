from __future__ import annotations

from pathlib import Path

import pytest

from pchsi.memory.round_maintenance import (
    MemoryRecordBindingV1,
    MemoryRoundPhaseV1,
    MemoryRoundStateV1,
    MemoryShadowEventV1,
    MemorySourcePartitionV1,
    ShadowDispositionV1,
    VerifierEffectV1,
    active_bindings_for_current_round_v1,
    append_shadow_event_v1,
    close_memory_round_v1,
    finalize_round_store_v1,
    initialize_round_store_v1,
)


def _binding(char: str, version: int):
    return MemoryRecordBindingV1(
        memory_lineage_id=char * 64,
        record_version=version,
        canonical_record_sha256=char.upper().casefold() * 64,
    )


def _state():
    return MemoryRoundStateV1(
        round_id="round-0001",
        policy_identity_sha256="a" * 64,
        active_snapshot_sha256="b" * 64,
        active_record_bindings=(_binding("1", 1),),
    )


def _event(
    *,
    char: str,
    version: int,
    effect: VerifierEffectV1,
    partition: MemorySourcePartitionV1 = (
        MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE
    ),
    complete: bool = True,
    clean: bool = True,
):
    return MemoryShadowEventV1(
        round_id="round-0001",
        record_binding=_binding(char, version),
        source_partition=partition,
        analyzer_finding_sha256="c" * 64,
        candidate_repair_sha256="d" * 64,
        verifier_effect=effect,
        f0_evidence_sha256=(
            None
            if effect
            is VerifierEffectV1.INFRASTRUCTURE_NO_OUTCOME
            else "e" * 64
        ),
        f1_evidence_sha256=(
            None
            if effect
            is VerifierEffectV1.INFRASTRUCTURE_NO_OUTCOME
            else "f" * 64
        ),
        evidence_complete=complete,
        evaluation_contamination_clean=clean,
    )


def test_active_snapshot_is_immutable_within_round_and_promotes_between_rounds():
    state = _state()
    before = active_bindings_for_current_round_v1(state)
    benefit = _event(
        char="2",
        version=1,
        effect=VerifierEffectV1.BENEFIT,
    )
    harm = _event(
        char="3",
        version=1,
        effect=VerifierEffectV1.HARM,
    )
    closure = close_memory_round_v1(
        state=state,
        shadow_events=(benefit, harm),
    )
    assert active_bindings_for_current_round_v1(state) == before
    assert {x.memory_lineage_id for x in closure.next_active_record_bindings} == {
        "1" * 64,
        "2" * 64,
    }
    dispositions = {
        row.record_binding.memory_lineage_id: row.disposition
        for row in closure.dispositions
    }
    assert dispositions["2" * 64] is (
        ShadowDispositionV1.PROMOTE_NEXT_ROUND
    )
    assert dispositions["3" * 64] is ShadowDispositionV1.QUARANTINE


def test_retrieval_dev_and_evaluation_never_write_back():
    state = _state()
    retrieval = _event(
        char="4",
        version=1,
        effect=VerifierEffectV1.BENEFIT,
        partition=MemorySourcePartitionV1.TRAIN_RETRIEVAL_DEV,
    )
    heldout = _event(
        char="5",
        version=1,
        effect=VerifierEffectV1.BENEFIT,
        partition=MemorySourcePartitionV1.VALID_UNSEEN,
    )
    closure = close_memory_round_v1(
        state=state,
        shadow_events=(retrieval, heldout),
    )
    dispositions = {row.disposition for row in closure.dispositions}
    assert (
        ShadowDispositionV1.SHADOW_ONLY_NO_ACTIVE_WRITEBACK
        in dispositions
    )
    assert (
        ShadowDispositionV1.FORBIDDEN_EVALUATION_WRITEBACK
        in dispositions
    )
    assert closure.next_active_record_bindings == state.active_record_bindings


def test_neutral_uncertain_and_infrastructure_never_become_positive_active():
    state = _state()
    events = (
        _event(
            char="6",
            version=1,
            effect=VerifierEffectV1.NEUTRAL,
        ),
        _event(
            char="7",
            version=1,
            effect=VerifierEffectV1.UNCERTAIN,
        ),
        _event(
            char="8",
            version=1,
            effect=VerifierEffectV1.INFRASTRUCTURE_NO_OUTCOME,
            complete=False,
        ),
    )
    closure = close_memory_round_v1(
        state=state,
        shadow_events=events,
    )
    assert closure.next_active_record_bindings == state.active_record_bindings
    assert {row.disposition for row in closure.dispositions} == {
        ShadowDispositionV1.DESCRIPTIVE_ONLY,
        ShadowDispositionV1.STAGING_UNRESOLVED,
        ShadowDispositionV1.REJECT_INFRASTRUCTURE_ONLY,
    }


def test_round_store_is_append_only_and_no_clobber(tmp_path: Path):
    state = _state()
    root = tmp_path / "round"
    initialize_round_store_v1(root=root, state=state)
    event = _event(
        char="2",
        version=1,
        effect=VerifierEffectV1.BENEFIT,
    )
    append_shadow_event_v1(root=root, state=state, event=event)
    with pytest.raises(FileExistsError):
        append_shadow_event_v1(root=root, state=state, event=event)
    closure = finalize_round_store_v1(root=root, state=state)
    assert (root / "ROUND_CLOSURE_V1.json").is_file()
    assert closure.next_snapshot_plan_sha256
