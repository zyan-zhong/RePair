from __future__ import annotations

from pathlib import Path
import re
from typing import Any

from .common import Stage0Error
from .receipts import load_receipts


_ATTEMPT_SUFFIX = re.compile(r"-a([0-9]{3})$")


def _attempt_ordinal(
    *,
    scheduled_cell_id: str,
    execution_attempt_id: str,
) -> int:
    prefix = scheduled_cell_id + "-a"
    if not execution_attempt_id.startswith(prefix):
        raise Stage0Error(
            "ATTEMPT_ID_CELL_PREFIX_MISMATCH:"
            + execution_attempt_id
        )
    match = _ATTEMPT_SUFFIX.search(
        execution_attempt_id
    )
    if match is None:
        raise Stage0Error(
            "ATTEMPT_ID_ORDINAL_INVALID:"
            + execution_attempt_id
        )
    return int(match.group(1))


def _matching_attempt_ids(
    directory: Path,
    *,
    scheduled_cell_id: str,
) -> set[str]:
    if not directory.exists():
        return set()
    if directory.is_symlink() or not directory.is_dir():
        raise Stage0Error(
            "ATTEMPT_STATE_DIRECTORY_INVALID:"
            + str(directory)
        )
    prefix = scheduled_cell_id + "-a"
    return {
        child.name
        for child in directory.iterdir()
        if (
            child.name.startswith(prefix)
            and not child.is_symlink()
            and child.is_dir()
        )
    }


def _ledger_attempt_ids(
    ledger: Path,
    *,
    scheduled_cell_id: str,
    suffix: str,
) -> set[str]:
    if not ledger.exists():
        return set()
    if ledger.is_symlink() or not ledger.is_dir():
        raise Stage0Error(
            "ATTEMPT_LEDGER_DIRECTORY_INVALID:"
            + str(ledger)
        )
    prefix = scheduled_cell_id + "-a"
    trailer = "." + suffix + ".json"
    result: set[str] = set()
    for path in ledger.iterdir():
        if (
            path.is_symlink()
            or not path.is_file()
            or not path.name.startswith(prefix)
            or not path.name.endswith(trailer)
        ):
            continue
        result.add(
            path.name[
                : -len(trailer)
            ]
        )
    return result


def audit_cell_attempt_state(
    *,
    evaluator_root: Path,
    scheduled_cell_id: str,
) -> dict[str, Any]:
    evaluator_root = Path(
        evaluator_root
    )
    ledger = (
        evaluator_root
        / "attempt_ledger"
    )
    attempts = (
        evaluator_root
        / "attempts"
    )
    staging = (
        attempts
        / ".staging"
    )

    started = _ledger_attempt_ids(
        ledger,
        scheduled_cell_id=scheduled_cell_id,
        suffix="started",
    )
    terminal = _ledger_attempt_ids(
        ledger,
        scheduled_cell_id=scheduled_cell_id,
        suffix="terminal",
    )
    published = _matching_attempt_ids(
        attempts,
        scheduled_cell_id=scheduled_cell_id,
    )
    staged = _matching_attempt_ids(
        staging,
        scheduled_cell_id=scheduled_cell_id,
    )

    if len(published) > 1:
        raise Stage0Error(
            "MULTIPLE_PUBLISHED_ATTEMPTS_FOR_CELL:"
            + scheduled_cell_id
            + ":"
            + repr(sorted(published))
        )

    if published - started:
        raise Stage0Error(
            "PUBLISHED_ATTEMPT_WITHOUT_STARTED_RECEIPT:"
            + scheduled_cell_id
        )

    all_attempts = (
        started
        | terminal
        | published
        | staged
    )

    ordinals = [
        _attempt_ordinal(
            scheduled_cell_id=scheduled_cell_id,
            execution_attempt_id=attempt_id,
        )
        for attempt_id in sorted(
            all_attempts
        )
    ]

    published_ids = sorted(
        published
    )
    started_only = sorted(
        started
        - terminal
        - published
    )
    terminal_without_publish = sorted(
        terminal
        - published
    )
    staged_without_publish = sorted(
        staged
        - published
    )

    if published_ids:
        next_ordinal = None
        next_attempt_id = None
    else:
        next_ordinal = (
            max(ordinals) + 1
            if ordinals
            else 0
        )
        if next_ordinal > 999:
            raise Stage0Error(
                "ATTEMPT_ORDINAL_EXHAUSTED:"
                + scheduled_cell_id
            )
        next_attempt_id = (
            scheduled_cell_id
            + "-a"
            + f"{next_ordinal:03d}"
        )

    return {
        "scheduled_cell_id":
            scheduled_cell_id,
        "started_attempt_ids":
            sorted(started),
        "terminal_attempt_ids":
            sorted(terminal),
        "published_attempt_ids":
            published_ids,
        "staging_attempt_ids":
            sorted(staged),
        "started_only_attempt_ids":
            started_only,
        "terminal_without_publish_attempt_ids":
            terminal_without_publish,
        "staged_without_publish_attempt_ids":
            staged_without_publish,
        "next_attempt_ordinal":
            next_ordinal,
        "next_execution_attempt_id":
            next_attempt_id,
    }


def _schedule_cell_ids(
    schedule: dict[str, Any],
) -> tuple[str, ...]:
    cells = schedule.get("cells")
    if not isinstance(cells, list):
        raise Stage0Error(
            "RESUME_SCHEDULE_CELLS_INVALID"
        )
    result = []
    for cell in cells:
        if not isinstance(cell, dict):
            raise Stage0Error(
                "RESUME_SCHEDULE_CELL_INVALID"
            )
        cell_id = cell.get(
            "condition_cell_id"
        )
        if not isinstance(
            cell_id,
            str,
        ) or not cell_id:
            raise Stage0Error(
                "RESUME_SCHEDULE_CELL_ID_INVALID"
            )
        result.append(cell_id)
    return tuple(result)


def audit_stage0_resume_state(
    *,
    twin_values: dict[str, dict[str, Any]],
    execution_root: Path,
) -> dict[str, Any]:
    execution_root = Path(
        execution_root
    )
    result: dict[str, Any] = {
        "status": "PASS",
        "model_execution_count": 0,
        "environment_execution_count": 0,
        "conditions": {},
    }

    for prefix, label in (
        ("PARENT", "parent"),
        ("CANDIDATE", "candidate"),
    ):
        schedule = twin_values[
            "bindings/"
            + prefix
            + "_CONDITION_RUN_SCHEDULE_V1.json"
        ]
        cell_ids = _schedule_cell_ids(
            schedule
        )
        condition_root = (
            execution_root
            / label
        )
        evaluator_root = (
            condition_root
            / "evaluator_run"
        )
        receipt_ledger = (
            condition_root
            / "cell_receipts.jsonl"
        )
        receipts = load_receipts(
            receipt_ledger
        )
        receipt_by_cell = {
            row["condition_cell_id"]:
                row
            for row in receipts
        }

        states = [
            audit_cell_attempt_state(
                evaluator_root=evaluator_root,
                scheduled_cell_id=cell_id,
            )
            for cell_id in cell_ids
        ]

        for state in states:
            cell_id = state[
                "scheduled_cell_id"
            ]
            has_receipt = (
                cell_id
                in receipt_by_cell
            )
            has_published = bool(
                state[
                    "published_attempt_ids"
                ]
            )
            if (
                has_receipt
                and not has_published
            ):
                raise Stage0Error(
                    "CELL_RECEIPT_WITHOUT_PUBLISHED_ATTEMPT:"
                    + cell_id
                )

        result["conditions"][label] = {
            "scheduled_cell_count":
                len(cell_ids),
            "cell_receipt_count":
                len(receipts),
            "published_attempt_count":
                sum(
                    bool(
                        state[
                            "published_attempt_ids"
                        ]
                    )
                    for state in states
                ),
            "started_only_attempt_count":
                sum(
                    len(
                        state[
                            "started_only_attempt_ids"
                        ]
                    )
                    for state in states
                ),
            "terminal_without_publish_attempt_count":
                sum(
                    len(
                        state[
                            "terminal_without_publish_attempt_ids"
                        ]
                    )
                    for state in states
                ),
            "staged_without_publish_attempt_count":
                sum(
                    len(
                        state[
                            "staged_without_publish_attempt_ids"
                        ]
                    )
                    for state in states
                ),
            "nonempty_cell_states": [
                state
                for state in states
                if (
                    state[
                        "started_attempt_ids"
                    ]
                    or state[
                        "terminal_attempt_ids"
                    ]
                    or state[
                        "published_attempt_ids"
                    ]
                    or state[
                        "staging_attempt_ids"
                    ]
                )
            ],
        }

    return result
