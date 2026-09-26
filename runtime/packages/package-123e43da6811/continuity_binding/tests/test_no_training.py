import pytest


def kwargs():
    return dict(round_id='fixture-r1', parent_policy_id='fixture-parent',
                post_plan_sha256='a' * 64, verifier_result_sha256='b' * 64,
                verified_benefit_count=2, verified_harm_count=1,
                verified_neutral_count=3, verified_uncertain_count=4,
                scientifically_valid_round=True)


def test_positive_benefit_explicit_post_choice_preserves_native_counts():
    from continuity_binding.no_training_update import freeze_no_training_update
    value = freeze_no_training_update(**kwargs(), reason='PLANNER_SELECTED_NO_TRAIN',
        planner_no_train_primary_record_sha256='a' * 64).to_dict()
    assert value['verified_benefit_count'] == 2
    assert value['verified_harm_count'] == 1
    assert value['training_execution_count'] == 0
    assert value['parent_policy_retained'] is True
    assert value['candidate_policy_created'] is False


def test_historical_zero_benefit_bytes_unchanged():
    from pchsi.round_control.no_training_update import freeze_no_training_update as original
    from continuity_binding.no_training_update import freeze_no_training_update
    params = dict(kwargs(), verified_benefit_count=0)
    assert original(**params).to_dict() == freeze_no_training_update(**params).to_dict()


@pytest.mark.parametrize('extra', [
    {},
    {'reason': 'PLANNER_SELECTED_NO_TRAIN'},
    {'reason': 'PLANNER_SELECTED_NO_TRAIN', 'planner_no_train_primary_record_sha256': 'c' * 64},
    {'planner_no_train_primary_record_sha256': 'a' * 64},
])
def test_positive_count_never_allowed_without_matching_post_choice(extra):
    from continuity_binding.no_training_update import freeze_no_training_update
    with pytest.raises(ValueError):
        freeze_no_training_update(**kwargs(), **extra)
