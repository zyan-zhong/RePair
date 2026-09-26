"""Whole-record packing for Failure Memory Policy views."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pchsi.memory.token_budget_contract import (
    FailureMemoryTokenBudgetContractV1,
)


class ProjectionPackingModeV1(str, Enum):
    DIRECT_SINGLE_RECORD = "DIRECT_SINGLE_RECORD"
    LIBRARY = "LIBRARY"


@dataclass(frozen=True, slots=True)
class PackablePolicyViewV1:
    representation_id: str
    policy_visible_payload: dict[str, object]
    policy_visible_token_count: int
    build_disposition: str
    memory_lineage_id: str
    record_version: int

    def __post_init__(self) -> None:
        if (
            not isinstance(self.representation_id, str)
            or not self.representation_id
        ):
            raise ValueError("representation_id required")
        if not isinstance(self.policy_visible_payload, dict):
            raise TypeError("Policy-visible payload must be object")
        if (
            type(self.policy_visible_token_count) is not int
            or self.policy_visible_token_count < 0
        ):
            raise ValueError("policy_visible_token_count invalid")
        if self.build_disposition != "ELIGIBLE":
            raise ValueError("only ELIGIBLE Policy views are packable")
        if (
            not isinstance(self.memory_lineage_id, str)
            or not self.memory_lineage_id
        ):
            raise ValueError("memory_lineage_id required")
        if type(self.record_version) is not int or self.record_version < 1:
            raise ValueError("record_version must be positive int")


@dataclass(frozen=True, slots=True)
class ProjectionPackingResultV1:
    mode: ProjectionPackingModeV1
    packed_views: tuple[PackablePolicyViewV1, ...]
    policy_visible_payloads: tuple[dict[str, object], ...]
    packed_token_count: int
    hard_ceiling: int
    stopped_before_representation_id: str | None

    def __post_init__(self) -> None:
        if type(self.packed_views) is not tuple:
            raise TypeError("packed_views must be tuple")
        if type(self.policy_visible_payloads) is not tuple:
            raise TypeError("policy_visible_payloads must be tuple")
        if len(self.packed_views) != len(self.policy_visible_payloads):
            raise ValueError("packed view/payload count mismatch")
        if (
            type(self.packed_token_count) is not int
            or self.packed_token_count < 0
        ):
            raise ValueError("packed_token_count invalid")
        if (
            type(self.hard_ceiling) is not int
            or self.hard_ceiling <= 0
        ):
            raise ValueError("hard_ceiling invalid")
        if self.packed_token_count > self.hard_ceiling:
            raise ValueError("packed result exceeds hard ceiling")


def _count_payloads(
    *,
    payloads: tuple[dict[str, object], ...],
    tokenizer,
) -> int:
    text = json.dumps(
        list(payloads),
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    count = tokenizer.count_tokens(text)
    if type(count) is not int or count < 0:
        raise ValueError("tokenizer returned invalid count")
    return count


def pack_policy_views_v1(
    *,
    mode: ProjectionPackingModeV1,
    views: tuple[PackablePolicyViewV1, ...],
    tokenizer,
    token_budget_contract: FailureMemoryTokenBudgetContractV1,
) -> ProjectionPackingResultV1:
    if not isinstance(mode, ProjectionPackingModeV1):
        raise TypeError("mode must be ProjectionPackingModeV1")
    if type(views) is not tuple:
        raise TypeError("views must be tuple")

    if mode is ProjectionPackingModeV1.DIRECT_SINGLE_RECORD:
        if len(views) != 1:
            raise ValueError(
                "DIRECT_SINGLE_RECORD requires exactly one view"
            )
        ceiling = (
            token_budget_contract.single_record_hard_ceiling
        )
        count = views[0].policy_visible_token_count
        if count > ceiling:
            raise ValueError(
                "direct whole Policy view exceeds frozen budget"
            )
        return ProjectionPackingResultV1(
            mode=mode,
            packed_views=views,
            policy_visible_payloads=(
                views[0].policy_visible_payload,
            ),
            packed_token_count=count,
            hard_ceiling=ceiling,
            stopped_before_representation_id=None,
        )

    if len(views) > token_budget_contract.max_record_count:
        raise ValueError("library input exceeds max record count")

    ceiling = (
        token_budget_contract.library_total_hard_ceiling
    )
    selected: list[PackablePolicyViewV1] = []
    selected_payloads: list[dict[str, object]] = []
    current_count = _count_payloads(
        payloads=(),
        tokenizer=tokenizer,
    )
    stopped = None

    for view in views:
        proposed_payloads = tuple(
            (*selected_payloads, view.policy_visible_payload)
        )
        proposed_count = _count_payloads(
            payloads=proposed_payloads,
            tokenizer=tokenizer,
        )
        if proposed_count > ceiling:
            stopped = view.representation_id
            break
        selected.append(view)
        selected_payloads.append(
            view.policy_visible_payload
        )
        current_count = proposed_count

    return ProjectionPackingResultV1(
        mode=mode,
        packed_views=tuple(selected),
        policy_visible_payloads=tuple(
            selected_payloads
        ),
        packed_token_count=current_count,
        hard_ceiling=ceiling,
        stopped_before_representation_id=stopped,
    )
