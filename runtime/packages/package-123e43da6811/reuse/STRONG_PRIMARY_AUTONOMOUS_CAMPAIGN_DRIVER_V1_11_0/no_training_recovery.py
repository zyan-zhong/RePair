from __future__ import annotations
import json
import sys
from pathlib import Path
from typing import Mapping


def _sha(name: str, value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(name + '_INVALID_SHA256')
    return value


def _counts(gate: Mapping[str, object]) -> dict[str, int]:
    raw = gate.get('stable_effect_counts')
    if not isinstance(raw, Mapping):
        raise ValueError('VERIFIER_STABLE_EFFECT_COUNTS_REQUIRED')
    out = {}
    for key in ('BENEFIT','HARM','NEUTRAL','UNCERTAIN'):
        value = raw.get(key)
        if type(value) is not int or value < 0:
            raise ValueError('VERIFIER_EFFECT_COUNT_INVALID:' + key)
        out[key] = value
    return out


def _post_artifact(post_receipt: Mapping[str, object]) -> dict[str, object]:
    call_dir = post_receipt.get('call_dir')
    if not isinstance(call_dir, str) or not call_dir:
        raise ValueError('HYDRATED_POST_CALL_DIR_REQUIRED')
    path = Path(call_dir).resolve() / 'validated_artifact.json'
    if not path.is_file() or path.is_symlink():
        raise ValueError('HYDRATED_POST_VALIDATED_ARTIFACT_MISSING')
    value = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(value, dict) or value.get('schema_id') != 'API_RESEARCHER_POST_PRIMARY_V1':
        raise ValueError('HYDRATED_POST_VALIDATED_ARTIFACT_SCHEMA_MISMATCH')
    _sha('POST_PLAN', value.get('primary_record_sha256'))
    return value


def recoverable_v110_post_without_gap(*, post_receipt: Mapping[str, object], verifier_gate: Mapping[str, object], gap_present: bool) -> dict[str, object]:
    if gap_present:
        return {'recoverable': False, 'route': post_receipt.get('route'), 'reason': 'V110_GAP_ALREADY_PRESENT'}
    if post_receipt.get('schema_id') not in {'STRONG_PRIMARY_R1_HYDRATED_PLANNER_POST_ACCEPTED_V1','STRONG_PRIMARY_V1_11_ADOPTED_V110_PLANNER_POST_V1'}:
        raise ValueError('V110_OR_V111_POST_SCHEMA_REQUIRED')
    if post_receipt.get('round_id') != verifier_gate.get('round_id'):
        raise ValueError('V110_POST_VERIFIER_ROUND_MISMATCH')
    if post_receipt.get('result_package_sha256') != verifier_gate.get('result_package_sha256'):
        raise ValueError('V110_POST_VERIFIER_RESULT_SHA_MISMATCH')
    counts = _counts(verifier_gate)
    route = post_receipt.get('route')
    if route == 'NO_TRAINING_UPDATE' and counts['BENEFIT'] == 0 and post_receipt.get('verified_benefit_count') == 0:
        if verifier_gate.get('scientific_attempt_consumed') is not True:
            raise ValueError('NO_TRAIN_POST_ONLY_REQUIRES_SCIENTIFICALLY_VALID_VERIFIER')
        return {'recoverable': True, 'route': route, 'reason': 'V110_NO_TRAIN_SIGNATURE_COMPATIBILITY_RECOVERY'}
    if route == 'VERIFIED_BENEFIT_TRAINING' or counts['BENEFIT'] > 0:
        raise ValueError('POSITIVE_BENEFIT_REQUIRES_V110_GAP_NO_FABRICATION')
    raise ValueError('V110_POST_ONLY_ROUTE_INCONSISTENT')


def build_no_training_update(*, repo: Path, post_receipt: Mapping[str, object], verifier_gate: Mapping[str, object]) -> dict[str, object]:
    recoverable_v110_post_without_gap(post_receipt=post_receipt, verifier_gate=verifier_gate, gap_present=False)
    artifact = _post_artifact(post_receipt)
    counts = _counts(verifier_gate)
    post_plan_sha = _sha('POST_PLAN', artifact['primary_record_sha256'])
    verifier_sha = _sha('VERIFIER_RESULT', verifier_gate.get('result_package_sha256'))
    parent = verifier_gate.get('parent_policy_id')
    if not isinstance(parent, str) or not parent:
        raise ValueError('PARENT_POLICY_ID_REQUIRED')
    src = str((Path(repo).resolve() / 'src'))
    if src not in sys.path:
        sys.path.insert(0, src)
    # Import the frozen production authority rather than copying its science semantics.
    from pchsi.round_control.no_training_update import freeze_no_training_update
    value = freeze_no_training_update(
        round_id=str(verifier_gate['round_id']),
        parent_policy_id=parent,
        post_plan_sha256=post_plan_sha,
        verifier_result_sha256=verifier_sha,
        verified_benefit_count=counts['BENEFIT'],
        verified_harm_count=counts['HARM'],
        verified_neutral_count=counts['NEUTRAL'],
        verified_uncertain_count=counts['UNCERTAIN'],
        scientifically_valid_round=True,
    )
    out = value.to_dict() if hasattr(value, 'to_dict') else dict(value)
    required = {
        'schema_id': 'NO_TRAINING_UPDATE_V1',
        'round_id': str(verifier_gate['round_id']),
        'parent_policy_id': parent,
        'post_plan_sha256': post_plan_sha,
        'verifier_result_sha256': verifier_sha,
        'verified_benefit_count': 0,
        'scientifically_valid_round': True,
        'candidate_policy_created': False,
        'training_execution_count': 0,
        'parent_policy_retained': True,
    }
    for key, expected in required.items():
        if out.get(key) != expected:
            raise ValueError('NO_TRAINING_PRODUCTION_OUTPUT_MISMATCH:' + key)
    return out
