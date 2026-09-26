from __future__ import annotations
from collections.abc import Mapping


def _sha(name: str, value: object) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise ValueError(name + '_INVALID_SHA256')
    return value


def _counts(gate: Mapping[str, object]) -> dict[str, int]:
    raw = gate.get('stable_effect_counts')
    if not isinstance(raw, Mapping):
        raise ValueError('VERIFIER_STABLE_EFFECT_COUNTS_REQUIRED')
    out: dict[str, int] = {}
    for key in ('BENEFIT', 'HARM', 'NEUTRAL', 'UNCERTAIN'):
        value = raw.get(key)
        if type(value) is not int or value < 0:
            raise ValueError('VERIFIER_EFFECT_COUNT_INVALID:' + key)
        out[key] = value
    return out


def validate_primary_post_and_route(*, post: Mapping[str, object], verifier_gate: Mapping[str, object]) -> dict[str, object]:
    """Validate the current fixed-head POST envelope and derive routing only from verifier authority.

    `researcher_training_recommendation` and `researcher_promotion_recommendation` are
    research interpretation fields. They are intentionally *not* effect/training/promotion
    authority. This repairs the V1.10 adapter's expectation of fields that do not exist in
    API_RESEARCHER_POST_PRIMARY_V1 while preserving the fixed-head schema semantics.
    """
    if post.get('schema_id') != 'API_RESEARCHER_POST_PRIMARY_V1' or post.get('schema_version') != 1:
        raise ValueError('PRIMARY_POST_SCHEMA_MISMATCH')
    round_id = post.get('round_id')
    if not isinstance(round_id, str) or not round_id or round_id != verifier_gate.get('round_id'):
        raise ValueError('PRIMARY_POST_ROUND_MISMATCH')
    env_sha = _sha('POST_ENVIRONMENT_RESULT', post.get('environment_result_package_sha256'))
    gate_sha = _sha('VERIFIER_RESULT', verifier_gate.get('result_package_sha256'))
    if env_sha != gate_sha:
        raise ValueError('PRIMARY_POST_VERIFIER_RESULT_MISMATCH')
    _sha('PRIMARY_PRE_RECORD', post.get('primary_pre_record_sha256'))
    _sha('PRIMARY_POST_RECORD', post.get('primary_record_sha256'))
    training_text = post.get('researcher_training_recommendation')
    if not isinstance(training_text, str) or not training_text.strip():
        raise ValueError('RESEARCHER_TRAINING_RECOMMENDATION_REQUIRED')
    promotion_text = post.get('researcher_promotion_recommendation')
    if promotion_text not in {'PROMOTE', 'ROLLBACK', 'HOLD'}:
        raise ValueError('RESEARCHER_PROMOTION_RECOMMENDATION_INVALID')
    counts = _counts(verifier_gate)
    benefits = counts['BENEFIT']
    return {
        'round_id': round_id,
        'post_schema_id': 'API_RESEARCHER_POST_PRIMARY_V1',
        'route': 'VERIFIED_BENEFIT_TRAINING' if benefits > 0 else 'NO_TRAINING_UPDATE',
        'verified_benefit_count': benefits,
        'stable_effect_counts': counts,
        'post_effect_authority_used': False,
        'post_training_authority_used': False,
        'post_promotion_authority_used': False,
        'effect_authority': 'INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY',
        'training_route_authority': 'DETERMINISTIC_VERIFIER_BENEFIT_COUNT_GATE',
        'promotion_authority': 'DETERMINISTIC_TRAIN_SELECT_GATE_ONLY',
    }
