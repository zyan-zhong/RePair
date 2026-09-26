"""Conservative, versioned ALFWorld public-event extraction rules."""
from __future__ import annotations

import re

from .types import ValidatedAttemptBundle


PARSER_VERSION = "ALFWORLD_MECHANICAL_EVENT_RULES_V1"
_NOTHING_HAPPENS = "Nothing happens."

_GO_TO = re.compile(r"^go to (?P<destination>.+)$")
_TAKE = re.compile(
    r"^take (?P<object>.+?) from (?P<source>.+)$"
)
_TREAT = re.compile(
    r"^(?P<verb>clean|heat|cool) "
    r"(?P<object>.+?) with (?P<source>.+)$"
)
_PLACE = re.compile(
    r"^(?:put|move) (?P<object>.+?) "
    r"(?:in|on|into|onto|to) (?P<destination>.+)$"
)
_NUMBERED_SUFFIX = re.compile(r"\s+\d+$")


def _source_family(value: str) -> str:
    return _NUMBERED_SUFFIX.sub("", value)


def _effective(
    *,
    pre_observation: str,
    pre_menu: tuple[str, ...],
    resulting_observation: str,
    resulting_menu: tuple[str, ...],
) -> bool:
    return (
        resulting_observation != _NOTHING_HAPPENS
        and (
            resulting_observation != pre_observation
            or resulting_menu != pre_menu
        )
    )


def _goal_object(public_goal: str, task_type: str) -> str | None:
    goal = public_goal.strip().lower()
    # Conservative patterns for the six ALFWorld task families. The parser
    # returns UNKNOWN rather than guessing when none is unambiguous.
    patterns = [
        r"(?:put|place) (?:a |an |the )?(?P<object>[a-z][a-z ]*?) "
        r"(?:in|on|into|onto) ",
        r"(?:clean|heat|cool) (?:a |an |the )?"
        r"(?P<object>[a-z][a-z ]*?)(?: and|,|$)",
        r"(?:look at|examine) (?:a |an |the )?"
        r"(?P<object>[a-z][a-z ]*?)(?: under| with|$)",
        r"(?:take|pick up) (?:a |an |the )?"
        r"(?P<object>[a-z][a-z ]*?)(?: from| and|$)",
    ]
    for pattern in patterns:
        match = re.search(pattern, goal)
        if match:
            value = match.group("object").strip()
            if value and len(value.split()) <= 4:
                return value
    # Some task goals are terse; task_type alone is not enough to infer object.
    return None


def _object_matches(candidate: str, goal_object: str | None) -> bool:
    if goal_object is None:
        return False
    candidate_text = _NUMBERED_SUFFIX.sub("", candidate.lower()).strip()
    return (
        candidate_text == goal_object
        or candidate_text.endswith(" " + goal_object)
        or goal_object.endswith(" " + candidate_text)
    )


def extract_alfworld_event_facts(
    bundle: ValidatedAttemptBundle,
) -> dict[str, object]:
    transitions = bundle.transitions
    public_goal = (
        bundle.traces[0].public_task_goal if bundle.traces else ""
    )
    task_type = str(bundle.episode.get("task_type", ""))
    goal_object = _goal_object(public_goal, task_type)

    destinations: list[str] = []
    sources: list[str] = []
    source_families: list[str] = []
    inventory_change_events: list[int] = []
    goal_visible_events: list[int] = []
    goal_take_available_events: list[int] = []
    acquired_events: list[int] = []
    treatment_events: list[int] = []
    placement_events: list[int] = []

    prior_inventory_observation: str | None = None

    for step, transition in enumerate(transitions):
        action = transition.submitted_action
        effective = _effective(
            pre_observation=transition.pre_observation,
            pre_menu=transition.pre_menu,
            resulting_observation=transition.resulting_observation,
            resulting_menu=transition.resulting_menu,
        )

        match = _GO_TO.fullmatch(action)
        if match:
            destination = match.group("destination")
            destinations.append(destination)
            sources.append(destination)
            source_families.append(_source_family(destination))

        take_match = _TAKE.fullmatch(action)
        if take_match and effective:
            if _object_matches(take_match.group("object"), goal_object):
                acquired_events.append(step)

        treatment_match = _TREAT.fullmatch(action)
        if treatment_match and effective:
            if _object_matches(
                treatment_match.group("object"),
                goal_object,
            ):
                treatment_events.append(step)

        placement_match = _PLACE.fullmatch(action)
        if placement_match and effective:
            if _object_matches(
                placement_match.group("object"),
                goal_object,
            ):
                placement_events.append(step)

        result_lower = transition.resulting_observation.lower()
        if goal_object is not None and goal_object in result_lower:
            goal_visible_events.append(step)
        if goal_object is not None and any(
            command.lower().startswith("take ")
            and goal_object in command.lower()
            for command in transition.resulting_menu
        ):
            goal_take_available_events.append(step)

        if action == "inventory":
            if (
                prior_inventory_observation is not None
                and prior_inventory_observation
                != transition.resulting_observation
            ):
                inventory_change_events.append(step)
            prior_inventory_observation = transition.resulting_observation

    def revisit_count(values: list[str]) -> int:
        seen: set[str] = set()
        repeats = 0
        for value in values:
            if value in seen:
                repeats += 1
            else:
                seen.add(value)
        return repeats

    progress_positions = sorted(
        set(
            acquired_events
            + treatment_events
            + placement_events
        )
    )
    remaining_budget = bundle.traces[-1].budget_after.to_dict()

    return {
        "parser_version": PARSER_VERSION,
        "goal_object_parse_status": (
            "KNOWN" if goal_object is not None else "UNKNOWN"
        ),
        "goal_object": goal_object,
        "destination_revisit_count": revisit_count(destinations),
        "source_revisit_count": revisit_count(sources),
        "source_family_revisit_count": revisit_count(source_families),
        "inventory_change_events": inventory_change_events,
        "goal_object_visible_events": (
            goal_visible_events
            if goal_object is not None
            else "UNKNOWN"
        ),
        "goal_take_available_events": (
            goal_take_available_events
            if goal_object is not None
            else "UNKNOWN"
        ),
        "goal_object_acquired_events": (
            acquired_events if goal_object is not None else "UNKNOWN"
        ),
        "required_treatment_completed_events": (
            treatment_events if goal_object is not None else "UNKNOWN"
        ),
        "placement_completed_events": (
            placement_events if goal_object is not None else "UNKNOWN"
        ),
        "time_to_first_registered_progress": (
            None
            if not progress_positions
            else progress_positions[0] + 1
        ),
        "time_since_last_registered_progress": (
            None
            if not progress_positions
            else len(transitions) - progress_positions[-1] - 1
        ),
        "remaining_environment_budget": (
            30 - remaining_budget["environment_step_count"]
        ),
        "unsupported_or_ambiguous_fields_use_unknown": True,
    }
