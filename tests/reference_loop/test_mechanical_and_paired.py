from __future__ import annotations

from pathlib import Path

from pchsi.reference_loop.mechanical import (
    extract_mechanical_episode_evidence,
)
from pchsi.reference_loop.paired import (
    extract_mechanical_paired_evidence,
)
from pchsi.reference_loop.types import (
    BudgetCounters,
    NormalizedPolicyCall,
    NormalizedTrace,
    NormalizedTransition,
    ValidatedAttemptBundle,
)


def _bundle(
    *,
    actions=("go to shelf 1", "go to shelf 2", "go to shelf 1", "go to shelf 2"),
    results=("at shelf 1", "at shelf 2", "at shelf 1", "Nothing happens."),
    menu_commands=None,
    checkpoint="P4-R1-Q2-BAD-TRAIN17",
):
    transitions = []
    traces = []
    calls = []
    history = []
    observation = "start"
    menu = tuple(actions if menu_commands is None else menu_commands)
    for index, (action, result) in enumerate(zip(actions, results)):
        before = BudgetCounters(index, index, 0, 0, 0)
        after = BudgetCounters(index + 1, index + 1, 0, 0, 0)
        calls.append(
            NormalizedPolicyCall(
                index,
                index,
                f"p{index}",
                "put a mug in cabinet",
                f"prompt-{index}",
                observation,
                menu,
                f'{{"action":"{action}"}}',
                tuple(history),
                before,
            )
        )
        traces.append(
            NormalizedTrace(
                index,
                index,
                "executed",
                "put a mug in cabinet",
                observation,
                f"prompt-{index}",
                menu,
                f'{{"action":"{action}"}}',
                action,
                action,
                "success",
                None,
                "ACTION_EXECUTED",
                None,
                None,
                action,
                action,
                result,
                None,
                before,
                after,
                {
                    "logical_condition_id": "P4-R1-Q2-BAD",
                    "checkpoint_instance_id": checkpoint,
                },
            )
        )
        transitions.append(
            NormalizedTransition(
                "cell",
                "attempt",
                index,
                index,
                action,
                observation,
                menu,
                result,
                menu,
                False,
                False,
                0,
            )
        )
        history.append((action, result))
        observation = result

    return ValidatedAttemptBundle(
        bundle_root=Path("/tmp/bundle"),
        episode={
            "task_id": "task",
            "gamefile_sha256": "a" * 64,
            "task_type": "pick_and_place_simple",
            "seed": 17,
            "success": False,
            "final_done": False,
            "final_won": False,
            "termination_reason": "ENVIRONMENT_STEP_BUDGET_EXHAUSTED",
            "logical_condition_id": "P4-R1-Q2-BAD",
            "checkpoint_instance_id": checkpoint,
            "access_class": "TRAIN_MEMORY_SOURCE",
        },
        policy_calls=tuple(calls),
        traces=tuple(traces),
        transitions=tuple(transitions),
        source_file_sha256s=(("attempt.json", "b" * 64),),
        episode_semantic_sha256="c" * 64,
        attempt_bundle_sha256=("d" if checkpoint.endswith("17") else "e") * 64,
        alignment_census={"status": "VALIDATED"},
    )


def test_mechanical_episode_counts_revisits_oscillation_and_no_effect() -> None:
    result = extract_mechanical_episode_evidence(_bundle())
    generic = result["generic_episode_facts"]
    alfworld = result["alfworld_event_facts"]

    assert generic["executed_environment_step_count"] == 4
    assert generic["abab_action_oscillation_count"] == 1
    assert generic["nothing_happens_count"] == 1
    assert generic["no_effect_transition_count"] >= 1
    assert generic["budget_exhaustion"] is True
    assert alfworld["destination_revisit_count"] == 2
    assert alfworld["source_family_revisit_count"] == 3
    assert result["authority"] == "DETERMINISTIC_FACTS_ONLY"


def test_pair_detects_divergence_before_registered_intervention() -> None:
    right = _bundle(
        actions=("go to shelf 9", "go to shelf 2", "go to shelf 1", "go to shelf 2"),
        checkpoint="P4-R1-Q2-BAD-TRAIN31",
    )
    result = extract_mechanical_paired_evidence(
        left=_bundle(),
        right=right,
        pair_id="pair-1",
        pair_kind="F0F1",
        registered_intervention_model_call_index=2,
        repair_registration_sha256="f" * 64,
    )

    assert result["first_action_divergence"] == 0
    assert result["pair_alignment_status"] == (
        "INVALID_DIVERGENCE_BEFORE_REGISTERED_INTERVENTION"
    )
    assert result["outcome_authority_absent"] is True


def test_pair_accepts_difference_at_registered_intervention() -> None:
    right = _bundle(
        actions=("go to shelf 1", "go to shelf 2", "take mug 1 from shelf 1", "go to shelf 2"),
        menu_commands=("go to shelf 1", "go to shelf 2", "go to shelf 1", "go to shelf 2"),
        checkpoint="P4-R1-Q2-BAD-TRAIN31",
    )
    result = extract_mechanical_paired_evidence(
        left=_bundle(),
        right=right,
        pair_id="pair-2",
        pair_kind="F0F1",
        registered_intervention_model_call_index=2,
        repair_registration_sha256="f" * 64,
    )

    assert result["first_action_divergence"] == 2
    assert result["pair_alignment_status"] == (
        "VALID_REGISTERED_INTERVENTION_ALIGNMENT"
    )
