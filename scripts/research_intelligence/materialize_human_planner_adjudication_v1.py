#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from pchsi.research_intelligence.human_planner_adjudication import (
    compile_human_planner_artifacts_v1,
)


def load(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular JSON file required: {path}")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"JSON object required: {path}")
    return value


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def write_new_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(path)
    data = canonical_bytes(value)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(data)
        while view:
            written = os.write(fd, view)
            if written <= 0:
                raise OSError("short write")
            view = view[written:]
        os.fsync(fd)
    finally:
        os.close(fd)


def selected_review_markdown(
    adjudication: dict[str, object],
) -> str:
    selected = [
        row
        for row in adjudication["state_reviews"]
        if row["selected_for_verification"]
    ]
    lines = [
        "# Human Research Planner Scientific Adjudication V1",
        "",
        "Status: **requires user scientific approval; not frozen**.",
        "",
        "## Frozen current-round boundary",
        "",
        "- principal bottleneck: unverified source-conditioned repair quality;",
        "- principal change: verify one balanced, nonduplicative 12-state portfolio;",
        "- budget: 12 states × 5 paired repetitions × 2 arms = 120 branch runs;",
        "- success-trajectory optimization: inactive;",
        "- training recipe/mixture: HOLD until sealed F0/F1 eligibility audit;",
        "- Analyzer/X/Memory/Researcher effect-label authority: false.",
        "",
        "## Selected 12-state candidate",
        "",
        "|#|task family|condition|repair|value|Harm risk|state|candidate|",
        "|---:|---|---|---|---|---|---|---|",
    ]
    for number, row in enumerate(selected, start=1):
        action = row["preferred_exact_action"]
        if not action:
            action = " ; ".join(row["preferred_option_actions"])
        lines.append(
            "|"
            + str(number)
            + "|"
            + str(row["task_family"])
            + "|"
            + str(row["preferred_condition"])
            + "|`"
            + str(action).replace("|", "\\|")
            + "`|"
            + str(row["expected_value_class"])
            + "|"
            + str(row["expected_harm_risk_class"])
            + "|`"
            + str(row["source_state_sha256"])[:16]
            + "…`|`"
            + str(row["preferred_candidate_sha256"])[:16]
            + "…`|"
        )
    lines.extend(
        [
            "",
            "## Scientific interpretation",
            "",
            "The portfolio is balanced across six task families (two states each), "
            "uses twelve unique Analyzer groups, and contains only one-action "
            "repairs accepted by Formal X. Eleven selected lineages are A2. One "
            "is A3 because X accepted its history-bounded scope while the "
            "corresponding A2 artifact was DOWNGRADE_SCOPE; this does not claim "
            "a causal Memory benefit because the environment action is identical.",
            "",
            "The Human PRE predicts research value and Harm risk but does not "
            "assign Benefit/Harm/Neutral/Uncertain. Those labels remain owned by "
            "the independent same-state environment verifier.",
            "",
            "## Next gate",
            "",
            "Review the full 30-state adjudication, code diff, portfolio, Human "
            "PRE candidate, and blind Strong-Researcher input. Approval is needed "
            "before branch push or Human PRE freeze.",
        ]
    )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adjudication", required=True)
    parser.add_argument("--dossier", required=True)
    parser.add_argument("--shared-input", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()

    adjudication_path = Path(args.adjudication).resolve()
    dossier_path = Path(args.dossier).resolve()
    shared_path = Path(args.shared_input).resolve()
    output = Path(args.output_dir).resolve()
    output.mkdir(parents=True, exist_ok=False)

    adjudication = load(adjudication_path)
    dossier = load(dossier_path)
    shared = load(shared_path)

    artifacts = compile_human_planner_artifacts_v1(
        adjudication=adjudication,
        dossier=dossier,
        shared_input=shared,
    )

    names = {
        "adjudication": (
            "HUMAN_PLANNER_SCIENTIFIC_ADJUDICATION_CANDIDATE_V1.json"
        ),
        "repair_portfolio": (
            "RESEARCH_REPAIR_PORTFOLIO_V1_CANDIDATE.json"
        ),
        "human_pre_input": (
            "HUMAN_RESEARCHER_PRE_INPUT_CANDIDATE_V1.json"
        ),
        "strong_blind_input": (
            "STRONG_RESEARCHER_BLIND_PRE_INPUT_V1.json"
        ),
        "reference_trace": (
            "RESEARCH_PLANNER_REFERENCE_TRACE_V2.json"
        ),
        "role_neutral_pre_decision": (
            "RESEARCHER_PRE_DECISION_V1_CANDIDATE.json"
        ),
        "build_report": (
            "HUMAN_PLANNER_ADJUDICATION_BUILD_REPORT_V1.json"
        ),
    }
    for key, filename in names.items():
        write_new_json(output / filename, artifacts[key])

    (output / "HUMAN_PLANNER_SCIENTIFIC_REVIEW_V1.md").write_text(
        selected_review_markdown(artifacts["adjudication"]),
        encoding="utf-8",
    )

    selected = [
        row
        for row in artifacts["adjudication"]["state_reviews"]
        if row["selected_for_verification"]
    ]
    print("HUMAN_PLANNER_REVIEWED_STATE_COUNT=30")
    print("HUMAN_PLANNER_SELECTED_STATE_COUNT=12")
    print(
        "HUMAN_PLANNER_SELECTED_CONDITION_COUNTS="
        + repr(
            artifacts["build_report"]["selected_condition_counts"]
        )
    )
    print(
        "HUMAN_PLANNER_SELECTED_TASK_FAMILY_COUNTS="
        + repr(
            artifacts["build_report"][
                "selected_task_family_counts"
            ]
        )
    )
    print(
        "HUMAN_PLANNER_SELECTED_UNIQUE_GROUP_COUNT="
        + str(
            artifacts["build_report"][
                "selected_unique_group_count"
            ]
        )
    )
    print(
        "HUMAN_PLANNER_SELECTED_X_DISPOSITION_COUNTS="
        + repr(
            artifacts["build_report"][
                "selected_x_disposition_counts"
            ]
        )
    )
    print(
        "HUMAN_PLANNER_SELECTED_REPAIR_KIND_COUNTS="
        + repr(
            artifacts["build_report"][
                "selected_repair_kind_counts"
            ]
        )
    )
    print(
        "STRONG_RESEARCHER_BLIND_INPUT_SHA256="
        + str(
            artifacts["strong_blind_input"][
                "blind_input_sha256"
            ]
        )
    )
    print(
        "HUMAN_APPROVAL_STATUS="
        + str(
            artifacts["build_report"][
                "human_approval_status"
            ]
        )
    )
    print("HUMAN_PRE_FROZEN=false")
    print("STRONG_RESEARCHER_SHADOW_EXECUTED=false")
    print("SUCCESS_TRAJECTORY_OPTIMIZATION_ACTIVE=false")
    print(
        "NEXT_GATE="
        "USER_APPROVAL_OF_HUMAN_PLANNER_SCIENTIFIC_ADJUDICATION"
    )


if __name__ == "__main__":
    main()
