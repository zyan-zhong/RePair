from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import ClassVar

from pchsi.memory.applicability import (
    ApplicabilityBoundarySetV1,
    NonApplicabilityDispositionV1,
    RevalidationRequirementV1,
)
from pchsi.memory.lifecycle_relations import (
    MemoryGovernanceStateV1,
    validate_unit3_initial_governance_state_v1,
)
from pchsi.memory.procedural_record import FactualSequenceBindingV1
from pchsi.memory.sequence_failure_experience import (
    SequenceFailureEventV1,
    SequenceFailureExperienceV1,
)


class ProceduralCompletenessDispositionV1(str, Enum):
    ESTABLISHED = "PROCEDURAL_COMPLETENESS_ESTABLISHED"
    NOT_ESTABLISHED = "PROCEDURAL_COMPLETENESS_NOT_ESTABLISHED"


class ProcessEvidenceModeV1(str, Enum):
    NONE = "NONE"
    MULTI_EVENT_POLICY_PROCESS = "MULTI_EVENT_POLICY_PROCESS"
    SINGLE_EVENT_CONSEQUENTIAL_POLICY_PROCESS = (
        "SINGLE_EVENT_CONSEQUENTIAL_POLICY_PROCESS"
    )


class ProceduralCompletenessFailureCodeV1(str, Enum):
    NO_SOURCE_EXPERIENCE = "NO_SOURCE_EXPERIENCE"
    SOURCE_BINDING_MISMATCH = "SOURCE_BINDING_MISMATCH"
    EMPTY_OBSERVED_SEQUENCE = "EMPTY_OBSERVED_SEQUENCE"
    FAILURE_RANGE_NOT_PRESENT = "FAILURE_RANGE_NOT_PRESENT"
    NO_PROCESS_EVIDENCE = "NO_PROCESS_EVIDENCE"
    INFRASTRUCTURE_ERROR_ONLY = "INFRASTRUCTURE_ERROR_ONLY"
    NO_OBSERVED_CONSEQUENCE_OR_REGISTERED_UNRESOLVED_OUTCOME = (
        "NO_OBSERVED_CONSEQUENCE_OR_REGISTERED_UNRESOLVED_OUTCOME"
    )
    NO_ACTIVATION_BOUNDARY = "NO_ACTIVATION_BOUNDARY"
    NO_RELEASE_OR_TERMINATION_BOUNDARY = (
        "NO_RELEASE_OR_TERMINATION_BOUNDARY"
    )
    REVALIDATION_REQUIRED_BUT_MISSING = (
        "REVALIDATION_REQUIRED_BUT_MISSING"
    )
    REVALIDATION_UNRESOLVED = "REVALIDATION_UNRESOLVED"
    NON_APPLICABILITY_DISPOSITION_MISSING = (
        "NON_APPLICABILITY_DISPOSITION_MISSING"
    )
    NON_APPLICABILITY_CONDITIONS_MISSING = (
        "NON_APPLICABILITY_CONDITIONS_MISSING"
    )


_FAILURE_ORDER = {
    code: index
    for index, code in enumerate(ProceduralCompletenessFailureCodeV1)
}


def _expect_exact_keys(
    value: object,
    expected: frozenset[str],
    label: str,
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be object")
    observed = frozenset(value)
    if observed != expected:
        raise ValueError(
            f"{label} fields do not match contract: "
            f"missing={sorted(expected - observed)}, "
            f"unknown={sorted(observed - expected)}"
        )
    return value


@dataclass(frozen=True, slots=True)
class ProceduralCompletenessReportV1:
    schema_id: str
    schema_version: int
    disposition: ProceduralCompletenessDispositionV1
    failure_codes: tuple[ProceduralCompletenessFailureCodeV1, ...]
    process_evidence_mode: ProcessEvidenceModeV1
    registered_unresolved_end_present: bool

    _KEYS: ClassVar[frozenset[str]] = frozenset(
        {
            "schema_id",
            "schema_version",
            "disposition",
            "failure_codes",
            "process_evidence_mode",
            "registered_unresolved_end_present",
        }
    )

    def __post_init__(self) -> None:
        if self.schema_id != "PROCEDURAL_COMPLETENESS_REPORT_V1":
            raise ValueError("completeness report schema_id mismatch")
        if self.schema_version != 1:
            raise ValueError("completeness report schema_version mismatch")
        if type(self.failure_codes) is not tuple:
            raise TypeError("failure_codes must be tuple")
        if any(
            not isinstance(code, ProceduralCompletenessFailureCodeV1)
            for code in self.failure_codes
        ):
            raise TypeError("failure_codes contain invalid item")
        if len(self.failure_codes) != len(set(self.failure_codes)):
            raise ValueError("failure_codes must be unique")
        if tuple(
            sorted(
                self.failure_codes,
                key=lambda code: _FAILURE_ORDER[code],
            )
        ) != self.failure_codes:
            raise ValueError("failure_codes are not in frozen order")
        if type(self.registered_unresolved_end_present) is not bool:
            raise TypeError(
                "registered_unresolved_end_present must be bool"
            )
        if (
            self.disposition is ProceduralCompletenessDispositionV1.ESTABLISHED
        ):
            if self.failure_codes:
                raise ValueError("established report must not have failures")
            if self.process_evidence_mode is ProcessEvidenceModeV1.NONE:
                raise ValueError("established report requires process evidence")
        else:
            if not self.failure_codes:
                raise ValueError("not-established report needs failure code")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "disposition": self.disposition.value,
            "failure_codes": [code.value for code in self.failure_codes],
            "process_evidence_mode": self.process_evidence_mode.value,
            "registered_unresolved_end_present": (
                self.registered_unresolved_end_present
            ),
        }

    @classmethod
    def from_dict(cls, value: object) -> "ProceduralCompletenessReportV1":
        payload = _expect_exact_keys(
            value,
            cls._KEYS,
            "procedural completeness report",
        )
        raw_codes = payload["failure_codes"]
        if not isinstance(raw_codes, list):
            raise TypeError("failure_codes must be JSON array")
        return cls(
            schema_id=payload["schema_id"],
            schema_version=payload["schema_version"],
            disposition=ProceduralCompletenessDispositionV1(
                payload["disposition"]
            ),
            failure_codes=tuple(
                ProceduralCompletenessFailureCodeV1(item)
                for item in raw_codes
            ),
            process_evidence_mode=ProcessEvidenceModeV1(
                payload["process_evidence_mode"]
            ),
            registered_unresolved_end_present=payload[
                "registered_unresolved_end_present"
            ],
        )


def _registered_unresolved_end_v1(
    experience: SequenceFailureExperienceV1,
) -> bool:
    return (
        experience.observed_end.episode_terminal_disposition
        == "OUTSIDE_REGISTERED_WINDOW"
    )


def _included_terminal_outcome_v1(
    experience: SequenceFailureExperienceV1,
) -> bool:
    return (
        experience.observed_end.episode_terminal_disposition
        == "INCLUDED_REGISTERED_WINDOW"
    )


def _infrastructure_error_event_v1(
    event: SequenceFailureEventV1,
) -> bool:
    return event.execution_status == "environment_error"


def _ordered_codes(
    values: set[ProceduralCompletenessFailureCodeV1],
) -> tuple[ProceduralCompletenessFailureCodeV1, ...]:
    return tuple(
        sorted(values, key=lambda code: _FAILURE_ORDER[code])
    )


def evaluate_procedural_completeness_v1(
    *,
    source_experiences: tuple[SequenceFailureExperienceV1, ...],
    factual_bindings: tuple[FactualSequenceBindingV1, ...],
    applicability: ApplicabilityBoundarySetV1,
    governance_state: MemoryGovernanceStateV1,
) -> ProceduralCompletenessReportV1:
    if type(source_experiences) is not tuple:
        raise TypeError("source_experiences must be tuple")
    if type(factual_bindings) is not tuple:
        raise TypeError("factual_bindings must be tuple")
    if not isinstance(applicability, ApplicabilityBoundarySetV1):
        raise TypeError("applicability type mismatch")

    validate_unit3_initial_governance_state_v1(governance_state)

    failures: set[ProceduralCompletenessFailureCodeV1] = set()

    if not source_experiences:
        failures.add(
            ProceduralCompletenessFailureCodeV1.NO_SOURCE_EXPERIENCE
        )

    if any(
        not isinstance(item, SequenceFailureExperienceV1)
        for item in source_experiences
    ):
        raise TypeError("source_experiences contain invalid item")

    if any(
        not isinstance(item, FactualSequenceBindingV1)
        for item in factual_bindings
    ):
        raise TypeError("factual_bindings contain invalid item")

    if len(source_experiences) != len(factual_bindings):
        failures.add(
            ProceduralCompletenessFailureCodeV1.SOURCE_BINDING_MISMATCH
        )
    else:
        for experience, binding in zip(
            source_experiences,
            factual_bindings,
            strict=True,
        ):
            try:
                binding.validate_against(experience)
            except (TypeError, ValueError):
                failures.add(
                    ProceduralCompletenessFailureCodeV1
                    .SOURCE_BINDING_MISMATCH
                )

    unresolved = any(
        _registered_unresolved_end_v1(experience)
        for experience in source_experiences
    )

    process_modes: list[ProcessEvidenceModeV1] = []
    any_consequence = False
    all_failure_events: list[SequenceFailureEventV1] = []

    for experience in source_experiences:
        sequence = tuple(experience.observed_sequence)
        if not sequence:
            failures.add(
                ProceduralCompletenessFailureCodeV1.EMPTY_OBSERVED_SEQUENCE
            )
            continue

        onset_index = (
            experience.registration_binding
            .registered_failure_onset_model_call_index
        )
        final_index = experience.registration_binding.final_model_call_index

        failure_slice = tuple(
            event
            for event in sequence
            if onset_index <= event.model_call_index <= final_index
        )
        all_failure_events.extend(failure_slice)

        if (
            not failure_slice
            or failure_slice[0].model_call_index != onset_index
            or failure_slice[-1].model_call_index != final_index
        ):
            failures.add(
                ProceduralCompletenessFailureCodeV1.FAILURE_RANGE_NOT_PRESENT
            )
            continue

        for event in failure_slice:
            if _infrastructure_error_event_v1(event):
                if event.visible_state_change_disposition != "ENVIRONMENT_ERROR":
                    failures.add(
                        ProceduralCompletenessFailureCodeV1
                        .SOURCE_BINDING_MISMATCH
                    )

        infrastructure_only = (
            bool(failure_slice)
            and all(
                _infrastructure_error_event_v1(event)
                for event in failure_slice
            )
        )
        if infrastructure_only:
            continue

        onset_event = failure_slice[0]
        mode = ProcessEvidenceModeV1.NONE

        if (
            len(failure_slice) >= 2
            and onset_event.execution_status in {"executed", "not_executed"}
            and any(
                event.model_call_index > onset_event.model_call_index
                and event.execution_status
                in {"executed", "not_executed"}
                for event in failure_slice[1:]
            )
        ):
            mode = ProcessEvidenceModeV1.MULTI_EVENT_POLICY_PROCESS

        elif (
            len(failure_slice) == 1
            and onset_event.execution_status in {"executed", "not_executed"}
            and (
                onset_event.visible_state_change_disposition
                in {
                    "OBSERVATION_CHANGED",
                    "MENU_CHANGED",
                    "OBSERVATION_AND_MENU_CHANGED",
                }
                or _included_terminal_outcome_v1(experience)
            )
        ):
            mode = (
                ProcessEvidenceModeV1
                .SINGLE_EVENT_CONSEQUENTIAL_POLICY_PROCESS
            )

        if mode is not ProcessEvidenceModeV1.NONE:
            process_modes.append(mode)
            if (
                _included_terminal_outcome_v1(experience)
                or any(
                    event.visible_state_change_disposition
                    in {
                        "OBSERVATION_CHANGED",
                        "MENU_CHANGED",
                        "OBSERVATION_AND_MENU_CHANGED",
                    }
                    for event in failure_slice
                )
                or _registered_unresolved_end_v1(experience)
            ):
                any_consequence = True

    infrastructure_error_only = (
        bool(all_failure_events)
        and all(
            _infrastructure_error_event_v1(event)
            for event in all_failure_events
        )
    )

    if infrastructure_error_only:
        failures.add(
            ProceduralCompletenessFailureCodeV1.INFRASTRUCTURE_ERROR_ONLY
        )

    if not process_modes:
        failures.add(
            ProceduralCompletenessFailureCodeV1.NO_PROCESS_EVIDENCE
        )

    if process_modes and not any_consequence:
        failures.add(
            ProceduralCompletenessFailureCodeV1
            .NO_OBSERVED_CONSEQUENCE_OR_REGISTERED_UNRESOLVED_OUTCOME
        )

    if not applicability.activation:
        failures.add(
            ProceduralCompletenessFailureCodeV1.NO_ACTIVATION_BOUNDARY
        )
    if not applicability.release and not applicability.termination:
        failures.add(
            ProceduralCompletenessFailureCodeV1
            .NO_RELEASE_OR_TERMINATION_BOUNDARY
        )
    if (
        applicability.revalidation_requirement
        is RevalidationRequirementV1.REQUIRED
        and not applicability.revalidation
    ):
        failures.add(
            ProceduralCompletenessFailureCodeV1
            .REVALIDATION_REQUIRED_BUT_MISSING
        )
    if (
        applicability.revalidation_requirement
        is RevalidationRequirementV1.UNRESOLVED
    ):
        failures.add(
            ProceduralCompletenessFailureCodeV1.REVALIDATION_UNRESOLVED
        )

    disposition = getattr(
        applicability,
        "non_applicability_disposition",
        None,
    )
    if not isinstance(disposition, NonApplicabilityDispositionV1):
        failures.add(
            ProceduralCompletenessFailureCodeV1
            .NON_APPLICABILITY_DISPOSITION_MISSING
        )
    elif (
        disposition is NonApplicabilityDispositionV1.REGISTERED_CONDITIONS
        and not applicability.non_applicability
    ):
        failures.add(
            ProceduralCompletenessFailureCodeV1
            .NON_APPLICABILITY_CONDITIONS_MISSING
        )

    if (
        ProcessEvidenceModeV1.MULTI_EVENT_POLICY_PROCESS
        in process_modes
    ):
        process_mode = ProcessEvidenceModeV1.MULTI_EVENT_POLICY_PROCESS
    elif process_modes:
        process_mode = (
            ProcessEvidenceModeV1
            .SINGLE_EVENT_CONSEQUENTIAL_POLICY_PROCESS
        )
    else:
        process_mode = ProcessEvidenceModeV1.NONE

    ordered = _ordered_codes(failures)
    if ordered:
        disposition_value = (
            ProceduralCompletenessDispositionV1.NOT_ESTABLISHED
        )
    else:
        disposition_value = (
            ProceduralCompletenessDispositionV1.ESTABLISHED
        )

    return ProceduralCompletenessReportV1(
        schema_id="PROCEDURAL_COMPLETENESS_REPORT_V1",
        schema_version=1,
        disposition=disposition_value,
        failure_codes=ordered,
        process_evidence_mode=process_mode,
        registered_unresolved_end_present=unresolved,
    )
