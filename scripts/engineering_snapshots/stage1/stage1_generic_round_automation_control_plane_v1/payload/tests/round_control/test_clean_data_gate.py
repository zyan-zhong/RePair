from pchsi.round_control.clean_data_gate import (
    CleanConsumerV1,
    CleanSplitV1,
    TrainPoolV1,
    authorize_clean_access,
)


def test_train_update_can_feed_adaptive_pipeline() -> None:
    grant = authorize_clean_access(
        split=CleanSplitV1.ALFWORLD_TRAIN,
        train_pool=TrainPoolV1.TRAIN_UPDATE,
        consumer=CleanConsumerV1.POLICY_TRAINING,
    )
    assert grant.allowed is True
    assert grant.benchmark_feedback_forbidden is True


def test_valid_unseen_cannot_feed_analyzer_or_training() -> None:
    for consumer in (
        CleanConsumerV1.HIERARCHICAL_ANALYZER,
        CleanConsumerV1.POLICY_TRAINING,
        CleanConsumerV1.RESEARCH_PLANNER,
    ):
        try:
            authorize_clean_access(
                split=CleanSplitV1.VALID_UNSEEN,
                train_pool=TrainPoolV1.NONE,
                consumer=consumer,
            )
        except ValueError as exc:
            assert "benchmark" in str(exc).lower()
        else:
            raise AssertionError("benchmark leakage was accepted")


def test_train_select_can_drive_promotion_but_not_training() -> None:
    grant = authorize_clean_access(
        split=CleanSplitV1.ALFWORLD_TRAIN,
        train_pool=TrainPoolV1.TRAIN_SELECT,
        consumer=CleanConsumerV1.PROMOTION_GATE,
    )
    assert grant.allowed is True

    try:
        authorize_clean_access(
            split=CleanSplitV1.ALFWORLD_TRAIN,
            train_pool=TrainPoolV1.TRAIN_SELECT,
            consumer=CleanConsumerV1.POLICY_TRAINING,
        )
    except ValueError:
        pass
    else:
        raise AssertionError("TRAIN_SELECT entered policy training")
