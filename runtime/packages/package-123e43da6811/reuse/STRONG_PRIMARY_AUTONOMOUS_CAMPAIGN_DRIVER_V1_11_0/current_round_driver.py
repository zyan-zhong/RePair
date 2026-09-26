from __future__ import annotations

from pathlib import Path
from typing import Callable

from safe_io import load_obj, write_once
from v110_boundary import decide_takeover_action
from v110_runtime_bridge import verifier_files_ready, load_verifier_gate, run_v110_post_once
from v110_post_adoption import adopt_accepted_v110_post
from no_training_recovery import build_no_training_update

ADOPT='V111_ADOPTED_PLANNER_POST_V1.json'
ROUTE='V111_CURRENT_ROUND_ROUTE_V1.json'
NO_TRAIN='V111_NO_TRAINING_UPDATE_V1.json'
BLOCKED='V111_AUTONOMY_RELEASE_GATE_V1.json'


def _write_route(state_root: Path, adopted: dict[str, object]) -> dict[str, object]:
    out={
        'schema_id':'V111_CURRENT_ROUND_ROUTE_V1','schema_version':1,
        'round_id':adopted['round_id'],'route':adopted['route'],
        'verified_benefit_count':adopted['verified_benefit_count'],
        'stable_effect_counts':adopted['stable_effect_counts'],
        'result_package_sha256':adopted['result_package_sha256'],
        'post_plan_sha256':adopted['post_plan_sha256'],
        'effect_authority':'INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY',
        'training_route_authority':'DETERMINISTIC_VERIFIER_BENEFIT_COUNT_GATE',
        'human_scientific_decision_count':0,
    }
    write_once(Path(state_root)/ROUTE,out)
    return out


def _release_gate(*, state_root: Path, route: str, current_round_action: str) -> dict[str, object]:
    # This is deliberately a truth gate, not a synthetic authority.  The fixed-head
    # repo currently contains next-round receipt construction but no proven generic
    # executable that launches a new policy+Memory TRAIN_UPDATE upstream round.
    blockers=[]
    if route=='VERIFIED_BENEFIT_TRAINING':
        blockers.extend([
            'CURRENT_ROUND_DUAL_VIEW_TO_SEALED_GENERIC_TRAINING_CONTRACT_NOT_LIVE_BOUND',
            'CURRENT_ROUND_TRAINER_TO_MEMORY_OFF_HARNESS_OFF_ACCEPTANCE_NOT_LIVE_BOUND',
        ])
    blockers.extend([
        'CURRENT_ROUND_MEMORY_SHADOW_EVENT_TO_ROUND_CLOSURE_NOT_LIVE_BOUND',
        'PROMOTION_ROLLBACK_TO_ACTUAL_NEXT_ROUND_UPSTREAM_LAUNCH_NOT_LIVE_BOUND',
    ])
    out={
        'schema_id':'V111_AUTONOMY_RELEASE_GATE_V1','schema_version':1,
        'route':route,'current_round_action':current_round_action,
        'current_round_v110_recovery_automatic':True,
        'planner_post_provider_resend_required':False,
        'routine_human_scientific_decision_required':False,
        'max_valid_scientific_rounds':10,
        'no_promotion_patience':3,
        'action_only_training_fallback_allowed':False,
        'full_max10_autonomous_campaign_released':False,
        'blockers':blockers,
        'blocker_count':len(blockers),
        'fail_closed_no_fabricated_authority':True,
    }
    write_once(Path(state_root)/BLOCKED,out)
    return out


def advance_current_round(
    *,
    repo: Path,
    state_root: Path,
    closure_root: Path,
    prepared_root: Path,
    upstream_root: Path,
    v110_package_root: Path,
    run_post: Callable[..., int] = run_v110_post_once,
) -> dict[str, object]:
    """Advance safely across the known V1.10 boundary without blind resend.

    Normal states are intentionally idempotent.  V1.10 owns its tail lock until it
    exits.  Only then may V1.11 validate verifier authority and either adopt an
    already accepted POST or make the single first POST send when no logical call
    exists at all.
    """
    state_root=Path(state_root); closure_root=Path(closure_root)
    prepared_root=Path(prepared_root); upstream_root=Path(upstream_root)
    v110_package_root=Path(v110_package_root); repo=Path(repo)

    if (state_root/ADOPT).is_file():
        adopted=load_obj(state_root/ADOPT)
        route=_write_route(state_root,adopted)
    else:
        ready=verifier_files_ready(upstream_root)
        decision=decide_takeover_action(closure_root=closure_root,verifier_ready=ready)
        action=str(decision['action'])
        if action in {'WAIT_V110_WRITER','WAIT_VERIFIER'}:
            return {'phase':action,'terminal':False,'side_effect':False}
        if action.startswith('FAIL_CLOSED_'):
            return {'phase':action,'terminal':False,'side_effect':False,'fail_closed':True}

        gate=load_verifier_gate(v110_package_root=v110_package_root,upstream_root=upstream_root)
        if action=='RUN_V110_POST_ONCE':
            # An expected V1.10 adapter failure after execute_one is acceptable only
            # insofar as the runtime subsequently contains exactly one ACCEPTED call.
            # The return code itself never authorizes a resend.
            run_post(v110_package_root=v110_package_root,upstream_root=upstream_root,
                     closure_root=closure_root,prepared_root=prepared_root,repo=repo)
            decision=decide_takeover_action(closure_root=closure_root,verifier_ready=True)
            action=str(decision['action'])
        if action!='ADOPT_ACCEPTED_V110_POST':
            if action.startswith('FAIL_CLOSED_'):
                return {'phase':action,'terminal':False,'side_effect':False,'fail_closed':True}
            return {'phase':'POST_NOT_YET_ADOPTABLE:'+action,'terminal':False,'side_effect':False}

        adopted=adopt_accepted_v110_post(closure_root=closure_root,verifier_gate=gate)
        write_once(state_root/ADOPT,adopted)
        route=_write_route(state_root,adopted)

    if route['route']=='NO_TRAINING_UPDATE':
        gate=load_verifier_gate(v110_package_root=v110_package_root,upstream_root=upstream_root)
        no_train=build_no_training_update(repo=repo,post_receipt=adopted,verifier_gate=gate)
        write_once(state_root/NO_TRAIN,no_train)
        rel=_release_gate(state_root=state_root,route='NO_TRAINING_UPDATE',current_round_action='NATIVE_NO_TRAINING_UPDATE_APPLIED')
        return {'phase':'NO_TRAINING_UPDATE_APPLIED','terminal':False,'side_effect':True,'release_gate':rel}

    rel=_release_gate(state_root=state_root,route='VERIFIED_BENEFIT_TRAINING',current_round_action='VERIFIED_BENEFIT_ROUTE_BOUND')
    return {'phase':'VERIFIED_BENEFIT_ROUTE_BOUND','terminal':False,'side_effect':True,'release_gate':rel}
