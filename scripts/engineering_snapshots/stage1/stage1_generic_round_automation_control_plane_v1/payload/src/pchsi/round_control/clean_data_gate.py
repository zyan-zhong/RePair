from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .common import hashed_payload


class CleanSplitV1(str, Enum):
    ALFWORLD_TRAIN = "ALFWORLD_TRAIN"
    VALID_SEEN = "VALID_SEEN"
    VALID_UNSEEN = "VALID_UNSEEN"


class TrainPoolV1(str, Enum):
    TRAIN_UPDATE = "TRAIN_UPDATE"
    TRAIN_SELECT = "TRAIN_SELECT"
    TRAIN_AUDIT = "TRAIN_AUDIT"
    NONE = "NONE"


class CleanConsumerV1(str, Enum):
    EVIDENCE_PACKAGE = "EVIDENCE_PACKAGE"
    HIERARCHICAL_ANALYZER = "HIERARCHICAL_ANALYZER"
    FAILURE_MEMORY = "FAILURE_MEMORY"
    RESEARCH_PLANNER = "RESEARCH_PLANNER"
    SAME_STATE_F0F1 = "SAME_STATE_F0F1"
    POLICY_TRAINING = "POLICY_TRAINING"
    LOCALIZATION_SUPERVISION = "LOCALIZATION_SUPERVISION"
    PROMOTION_GATE = "PROMOTION_GATE"
    ROLE_TAKEOVER_AUDIT = "ROLE_TAKEOVER_AUDIT"
    FINAL_BENCHMARK = "FINAL_BENCHMARK"


@dataclass(frozen=True)
class CleanAccessGrantV1:
    split: CleanSplitV1
    train_pool: TrainPoolV1
    consumer: CleanConsumerV1
    allowed: bool
    benchmark_feedback_forbidden: bool
    access_sha256: str

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": "CLEAN_DATA_ACCESS_GRANT_V1",
            "schema_version": 1,
            "split": self.split.value,
            "train_pool": self.train_pool.value,
            "consumer": self.consumer.value,
            "allowed": self.allowed,
            "benchmark_feedback_forbidden": self.benchmark_feedback_forbidden,
            "access_sha256": self.access_sha256,
        }


_UPDATE_CONSUMERS = {
    CleanConsumerV1.EVIDENCE_PACKAGE,
    CleanConsumerV1.HIERARCHICAL_ANALYZER,
    CleanConsumerV1.FAILURE_MEMORY,
    CleanConsumerV1.RESEARCH_PLANNER,
    CleanConsumerV1.SAME_STATE_F0F1,
    CleanConsumerV1.POLICY_TRAINING,
    CleanConsumerV1.LOCALIZATION_SUPERVISION,
}
_SELECT_CONSUMERS = {
    CleanConsumerV1.PROMOTION_GATE,
}
_AUDIT_CONSUMERS = {
    CleanConsumerV1.ROLE_TAKEOVER_AUDIT,
}
_BENCHMARK_CONSUMERS = {
    CleanConsumerV1.FINAL_BENCHMARK,
}


def authorize_clean_access(
    *,
    split: CleanSplitV1,
    train_pool: TrainPoolV1,
    consumer: CleanConsumerV1,
) -> CleanAccessGrantV1:
    if not isinstance(split, CleanSplitV1):
        raise TypeError("split must be CleanSplitV1")
    if not isinstance(train_pool, TrainPoolV1):
        raise TypeError("train_pool must be TrainPoolV1")
    if not isinstance(consumer, CleanConsumerV1):
        raise TypeError("consumer must be CleanConsumerV1")

    if split is CleanSplitV1.ALFWORLD_TRAIN:
        if train_pool is TrainPoolV1.TRAIN_UPDATE:
            allowed = consumer in _UPDATE_CONSUMERS
        elif train_pool is TrainPoolV1.TRAIN_SELECT:
            allowed = consumer in _SELECT_CONSUMERS
        elif train_pool is TrainPoolV1.TRAIN_AUDIT:
            allowed = consumer in _AUDIT_CONSUMERS
        else:
            allowed = False
        if not allowed:
            raise ValueError(
                f"train pool {train_pool.value} cannot feed {consumer.value}"
            )
    else:
        if train_pool is not TrainPoolV1.NONE:
            raise ValueError("benchmark split must not carry a train pool")
        if consumer not in _BENCHMARK_CONSUMERS:
            raise ValueError(
                "benchmark split cannot feed adaptive pipeline component "
                + consumer.value
            )

    payload = {
        "schema_id": "CLEAN_DATA_ACCESS_GRANT_V1",
        "schema_version": 1,
        "split": split.value,
        "train_pool": train_pool.value,
        "consumer": consumer.value,
        "allowed": True,
        "benchmark_feedback_forbidden": True,
    }
    hashed = hashed_payload(
        domain="CLEAN_DATA_ACCESS_GRANT_V1",
        hash_field="access_sha256",
        payload=payload,
    )
    return CleanAccessGrantV1(
        split=split,
        train_pool=train_pool,
        consumer=consumer,
        allowed=True,
        benchmark_feedback_forbidden=True,
        access_sha256=hashed["access_sha256"],
    )
