#!/usr/bin/env python3
"""Finalize approved source failures into exact Package-A A9 inputs.

This is still pre-A9: no ALFWorld execution and no Policy/model call occurs.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys

from pchsi.evaluation.budget import BudgetState
from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.memory.applicability import (
    ApplicabilityBoundarySetV1,
    BoundaryTypeV1,
    BoundaryVerificationStatusV1,
    MemoryBoundaryClauseV1,
    NonApplicabilityDispositionV1,
    RevalidationRequirementV1,
)
from pchsi.memory.candidate_materialization import (
    CandidateMaterializationItemV1,
    candidate_id_for_item_v1,
)
from pchsi.memory.lifecycle_relations import (
    EvaluationContaminationStatusV1,
)
from pchsi.memory.procedural_builder import (
    ProceduralMemoryAssemblyInputV1,
)
from pchsi.memory.procedural_record import (
    MemoryAuthorityTypeV1,
    MemoryEvidenceRefV1,
    ProceduralMemoryLineageV1,
)
from pchsi.memory.semantic_recovery import (
    ObservedRecoveryBindingV1,
    ProposedRecoveryV1,
    SemanticAnnotationTypeV1,
    SemanticConfidenceV1,
    SemanticHypothesisAnnotationV1,
)
from pchsi.memory.sequence_failure_experience import (
    RegisteredFailureSequenceWindowV1,
    SequenceSourceEvidenceV1,
    build_sequence_failure_experience_v1,
)
from pchsi.memory.source_collection import (
    NO_PERFORMANCE_ESTIMAND,
    SourcePanelManifestV1,
    read_source_collection_ledger_v1,
)
from pchsi.memory.source_state_contracts import (
    RegisteredReplaySourceV1,
    ReplayTransitionExpectationV1,
    build_source_decision_state_fingerprint_v1,
)


APPROVAL_SCHEMA = "FAILURE_MEMORY_HUMAN_REGISTRATION_APPROVAL_V1"
APPROVAL_VERSION = 1
APPROVAL_DECISION = "APPROVED"
APPROVAL_TOKEN = "HUMAN_FAILURE_MEMORY_REGISTRATION_APPROVED_V1"

SOURCE_CONDITION = "P4-R1-Q2-BAD-TRAIN17"
SOURCE_ROUND = "SOURCE_COLLECTION_V1"

PROTECTED_TASK_ACCESS_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)


def _load_script(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load script: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise ValueError("output parent invalid")
    fd = os.open(
        path,
        os.O_WRONLY | os.O_CREAT | os.O_EXCL,
        0o600,
    )
    try:
        view = memoryview(data)
        while view:
            count = os.write(fd, view)
            if count <= 0:
                raise OSError("os.write made no progress")
            view = view[count:]
        os.fsync(fd)
    finally:
        os.close(fd)


def _sha_domain(domain: str, payload: object) -> str:
    return sha256_bytes(
        domain.encode("utf-8")
        + b"\0"
        + canonical_json_bytes(payload)
    )


def _text(name: str, value: object, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{name} must be str")
    if not allow_empty and not value:
        raise ValueError(f"{name} must be nonempty")
    if any(ch in value for ch in ("\x00", "\r", "\n")):
        raise ValueError(f"{name} contains control character")
    return value


def _validate_source_collection_code_commit_ancestry(
    *,
    repo_root: Path,
    source_collection_code_commit: str,
    authority_commit: str,
) -> None:
    for name, value in (
        (
            "source_collection_code_commit",
            source_collection_code_commit,
        ),
        (
            "authority_commit",
            authority_commit,
        ),
    ):
        if (
            not isinstance(value, str)
            or len(value) != 40
            or any(
                character
                not in "0123456789abcdef"
                for character in value
            )
        ):
            raise ValueError(
                f"{name} must be 40 lowercase hex"
            )

    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "merge-base",
            "--is-ancestor",
            source_collection_code_commit,
            authority_commit,
        ],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if result.returncode != 0:
        raise ValueError(
            "source-collection code commit must "
            "be an ancestor of finalizer authority"
        )


def _load_human_panel_index(human_panel_root: Path):
    path = human_panel_root / "PANEL_INDEX.json"
    raw = path.read_bytes()
    payload = strict_json_loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("human panel index must be object")
    if raw != canonical_json_bytes(payload):
        raise ValueError("human panel index is not canonical")
    if payload.get("performance_estimand") != NO_PERFORMANCE_ESTIMAND:
        raise ValueError("human panel performance estimand mismatch")
    cases = payload.get("cases")
    if not isinstance(cases, list) or len(cases) != 3:
        raise ValueError("human panel must contain exactly three cases")
    return path, payload, raw


def _validate_approval(
    *,
    path: Path,
    human_panel_root: Path,
):
    raw = path.read_bytes()
    payload = strict_json_loads(raw)
    if not isinstance(payload, dict):
        raise TypeError("human approval must be object")
    if raw != canonical_json_bytes(payload):
        raise ValueError(
            "human approval must use canonical compact sorted-key JSON bytes"
        )
    expected_top = {
        "schema_id",
        "schema_version",
        "approval_token",
        "reviewer_decision",
        "reviewer_id",
        "human_panel_index_sha256",
        "source_panel_manifest_sha256",
        "source_collection_ledger_sha256",
        "selected_failure_panel_sha256",
        "decisions",
    }
    if set(payload) != expected_top:
        raise ValueError("human approval top-level fields mismatch")
    if payload["schema_id"] != APPROVAL_SCHEMA:
        raise ValueError("human approval schema mismatch")
    if payload["schema_version"] != APPROVAL_VERSION:
        raise ValueError("human approval version mismatch")
    if payload["approval_token"] != APPROVAL_TOKEN:
        raise ValueError("human approval token mismatch")
    if payload["reviewer_decision"] != APPROVAL_DECISION:
        raise ValueError("human approval is not APPROVED")
    reviewer_id = _text("reviewer_id", payload["reviewer_id"])

    panel_index_path, panel_index, panel_index_raw = _load_human_panel_index(
        human_panel_root
    )
    observed_panel_sha = sha256_bytes(panel_index_raw)
    if payload["human_panel_index_sha256"] != observed_panel_sha:
        raise ValueError("human approval panel index SHA mismatch")

    for key in (
        "source_panel_manifest_sha256",
        "source_collection_ledger_sha256",
        "selected_failure_panel_sha256",
    ):
        if payload[key] != panel_index[key]:
            raise ValueError(f"human approval binding mismatch: {key}")

    raw_decisions = payload["decisions"]
    if not isinstance(raw_decisions, list) or len(raw_decisions) != 3:
        raise ValueError("human approval decisions must contain three cases")

    panel_cases = {
        item["case_id"]: item
        for item in panel_index["cases"]
    }
    if len(panel_cases) != 3:
        raise ValueError("human panel case IDs are not unique")

    expected_decision_fields = {
        "case_id",
        "case_summary_sha256",
        "source_panel_manifest_sha256",
        "source_collection_ledger_sha256",
        "selected_failure_panel_sha256",
        "case_receipt_sha256",
        "attempt_bundle_sha256",
        "source_attempt_id",
        "source_task_id",
        "source_round",
        "source_condition",
        "relevant_start_model_call_index",
        "registered_failure_onset_model_call_index",
        "final_model_call_index",
        "registered_recovery_start_model_call_index",
        "registered_recovery_final_model_call_index",
        "activation_condition_text",
        "release_condition_text",
        "non_applicability_condition_text",
        "candidate_mechanism_text",
        "proposed_recovery_steps",
        "reviewer_notes",
    }

    decisions = []
    seen = set()

    for decision in raw_decisions:
        if not isinstance(decision, dict):
            raise TypeError("human approval decision must be object")
        if set(decision) != expected_decision_fields:
            raise ValueError(
                "human approval decision fields mismatch: "
                + repr(sorted(set(decision) ^ expected_decision_fields))
            )

        case_id = decision["case_id"]
        if case_id in seen:
            raise ValueError("duplicate human approval case")
        seen.add(case_id)
        case = panel_cases.get(case_id)
        if case is None:
            raise ValueError("approval case is not in selected human panel")

        case_summary_path = human_panel_root / "cases" / case_id / "case_summary.json"
        case_summary_raw = case_summary_path.read_bytes()
        case_summary = strict_json_loads(case_summary_raw)
        if case_summary_raw != canonical_json_bytes(case_summary):
            raise ValueError("case summary not canonical")
        if decision["case_summary_sha256"] != sha256_bytes(case_summary_raw):
            raise ValueError("case summary SHA mismatch")

        bindings = {
            "source_panel_manifest_sha256":
                "source_panel_manifest_sha256",
            "source_collection_ledger_sha256":
                "source_collection_ledger_sha256",
            "selected_failure_panel_sha256":
                "selected_failure_panel_sha256",
            "case_receipt_sha256":
                "case_receipt_sha256",
            "attempt_bundle_sha256":
                "attempt_bundle_sha256",
            "source_attempt_id":
                "execution_attempt_id",
            "source_task_id":
                "source_task_id",
        }

        for (
            decision_key,
            summary_key,
        ) in bindings.items():
            if (
                decision[decision_key]
                != case_summary[summary_key]
            ):
                raise ValueError(
                    "human decision case binding mismatch: "
                    + decision_key
                )

        if decision["source_round"] != SOURCE_ROUND:
            raise ValueError("human decision source_round mismatch")
        if decision["source_condition"] != SOURCE_CONDITION:
            raise ValueError("human decision source_condition mismatch")

        start = decision["relevant_start_model_call_index"]
        onset = decision["registered_failure_onset_model_call_index"]
        final = decision["final_model_call_index"]
        for name, value in (
            ("relevant_start_model_call_index", start),
            ("registered_failure_onset_model_call_index", onset),
            ("final_model_call_index", final),
        ):
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} invalid")
        if not start <= onset <= final:
            raise ValueError("human decision factual range order invalid")
        if final > case_summary["valid_model_call_index_max"]:
            raise ValueError("human decision final call outside case")

        recovery_start = decision[
            "registered_recovery_start_model_call_index"
        ]
        recovery_final = decision[
            "registered_recovery_final_model_call_index"
        ]
        if (recovery_start is None) != (recovery_final is None):
            raise ValueError("human recovery range must be both null/non-null")
        if recovery_start is not None:
            if (
                type(recovery_start) is not int
                or type(recovery_final) is not int
                or not onset <= recovery_start <= recovery_final <= final
            ):
                raise ValueError("human recovery range order invalid")

        _text("activation_condition_text", decision["activation_condition_text"])
        _text("release_condition_text", decision["release_condition_text"])
        _text(
            "non_applicability_condition_text",
            decision["non_applicability_condition_text"],
            allow_empty=True,
        )
        _text(
            "candidate_mechanism_text",
            decision["candidate_mechanism_text"],
            allow_empty=True,
        )
        _text("reviewer_notes", decision["reviewer_notes"], allow_empty=True)

        steps = decision["proposed_recovery_steps"]
        if not isinstance(steps, list):
            raise TypeError("proposed_recovery_steps must be array")
        for step in steps:
            _text("proposed recovery step", step)

        decisions.append(
            {
                "decision": decision,
                "case_summary": case_summary,
                "case_summary_raw": case_summary_raw,
                "decision_sha256": sha256_bytes(
                    canonical_json_bytes(decision)
                ),
            }
        )

    if set(seen) != set(panel_cases):
        raise ValueError("human approval does not cover all selected cases")

    return (
        payload,
        raw,
        reviewer_id,
        tuple(decisions),
        panel_index,
    )


def _boundary(
    *,
    boundary_type: BoundaryTypeV1,
    registration_id: str,
    condition_text: str,
    approval_sha: str,
    experience_ref: MemoryEvidenceRefV1,
) -> MemoryBoundaryClauseV1:
    return MemoryBoundaryClauseV1(
        boundary_type=boundary_type,
        boundary_authority=MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
        origin_role="HUMAN_REGISTERED",
        registration_id=registration_id,
        origin_artifact_ref=MemoryEvidenceRefV1(
            source_kind="REGISTERED_BOUNDARY_ARTIFACT",
            source_id=registration_id,
            source_sha256=approval_sha,
        ),
        condition_text=condition_text,
        source_refs=(experience_ref,),
        verification_status=(
            BoundaryVerificationStatusV1.REGISTERED_UNVERIFIED
        ),
    )


def _build_assembly(
    *,
    experience,
    decision: dict[str, object],
    approval_sha: str,
    reviewer_id: str,
):
    experience_sha = sha256_bytes(experience.canonical_bytes())
    experience_ref = MemoryEvidenceRefV1(
        source_kind="SEQUENCE_FAILURE_EXPERIENCE_V1",
        source_id=experience.experience_id,
        source_sha256=experience_sha,
    )

    lineage_id = _sha_domain(
        "PROCEDURAL_MEMORY_LINEAGE_FROM_SOURCE_EXPERIENCE_V1",
        {
            "experience_id": experience.experience_id,
            "source_bundle_sha256": experience.source_bundle_sha256,
        },
    )

    base_id = _sha_domain(
        "PROCEDURAL_MEMORY_HUMAN_ASSEMBLY_IDS_V1",
        {
            "experience_id": experience.experience_id,
            "approval_sha256": approval_sha,
        },
    )

    activation_id = "ACT-" + base_id[:24]
    release_id = "REL-" + base_id[24:48]

    activation = _boundary(
        boundary_type=BoundaryTypeV1.ACTIVATION,
        registration_id=activation_id,
        condition_text=decision["activation_condition_text"],
        approval_sha=approval_sha,
        experience_ref=experience_ref,
    )
    release = _boundary(
        boundary_type=BoundaryTypeV1.RELEASE,
        registration_id=release_id,
        condition_text=decision["release_condition_text"],
        approval_sha=approval_sha,
        experience_ref=experience_ref,
    )

    non_app_text = decision["non_applicability_condition_text"]
    if non_app_text:
        nonapp_id = "NONAPP-" + base_id[8:32]
        non_app = (
            _boundary(
                boundary_type=BoundaryTypeV1.NON_APPLICABILITY,
                registration_id=nonapp_id,
                condition_text=non_app_text,
                approval_sha=approval_sha,
                experience_ref=experience_ref,
            ),
        )
        non_app_disposition = (
            NonApplicabilityDispositionV1.REGISTERED_CONDITIONS
        )
    else:
        non_app = ()
        non_app_disposition = (
            NonApplicabilityDispositionV1
            .UNRESOLVED_NO_REGISTERED_CONDITION
        )

    applicability = ApplicabilityBoundarySetV1(
        activation=(activation,),
        continuation=(),
        revalidation_requirement=RevalidationRequirementV1.NOT_REQUIRED,
        revalidation=(),
        release=(release,),
        termination=(),
        non_applicability_disposition=non_app_disposition,
        non_applicability=non_app,
        policy_visible_state_change_trigger=(),
    )

    mechanism_text = decision["candidate_mechanism_text"]
    semantic = ()
    if mechanism_text:
        annotation_id = "ANN-" + base_id[16:40]
        semantic = (
            SemanticHypothesisAnnotationV1(
                annotation_id=annotation_id,
                annotation_type=(
                    SemanticAnnotationTypeV1.CANDIDATE_MECHANISM
                ),
                authority_type=MemoryAuthorityTypeV1.SEMANTIC_HYPOTHESIS,
                text=mechanism_text,
                supporting_refs=(experience_ref,),
                counterevidence_refs=(),
                semantic_confidence=SemanticConfidenceV1.UNSPECIFIED,
                origin_role="HUMAN_REVIEWER",
                origin_identity=reviewer_id,
                origin_artifact_ref=MemoryEvidenceRefV1(
                    source_kind="SEMANTIC_ANNOTATION_ARTIFACT",
                    source_id=annotation_id,
                    source_sha256=approval_sha,
                ),
            ),
        )

    observed = ()
    if (
        decision["registered_recovery_start_model_call_index"]
        is not None
    ):
        observed = (
            ObservedRecoveryBindingV1(
                authority_type=MemoryAuthorityTypeV1.REGISTERED_BOUNDARY,
                source_experience_id=experience.experience_id,
                registered_recovery_start_model_call_index=decision[
                    "registered_recovery_start_model_call_index"
                ],
                registered_recovery_final_model_call_index=decision[
                    "registered_recovery_final_model_call_index"
                ],
                source_refs=(experience_ref,),
            ),
        )

    steps = tuple(decision["proposed_recovery_steps"])
    proposed = ()
    if steps:
        proposal_id = "PROP-" + base_id[32:56]
        proposed = (
            ProposedRecoveryV1(
                proposal_id=proposal_id,
                authority_type=MemoryAuthorityTypeV1.RECOVERY_PROPOSAL,
                procedure_steps=steps,
                source_refs=(experience_ref,),
                origin_role="HUMAN_REVIEWER",
                origin_identity=reviewer_id,
                origin_artifact_ref=MemoryEvidenceRefV1(
                    source_kind="RECOVERY_PROPOSAL_ARTIFACT",
                    source_id=proposal_id,
                    source_sha256=approval_sha,
                ),
            ),
        )

    assembly_id = "ASSEMBLY-" + base_id[:32]
    assembly = ProceduralMemoryAssemblyInputV1(
        schema_id="PROCEDURAL_MEMORY_ASSEMBLY_REGISTRATION_V1",
        schema_version=1,
        registration_id=assembly_id,
        lineage=ProceduralMemoryLineageV1(
            memory_lineage_id=lineage_id,
            record_version=1,
            previous_record_binding=None,
        ),
        creation_event_id="CREATE-" + base_id[:24],
        creator_role="HUMAN_APPROVED_REGISTERED_BUILDER",
        source_experience_refs=(experience_ref,),
        applicability=applicability,
        semantic_hypotheses=semantic,
        observed_recovery_bindings=observed,
        proposed_recoveries=proposed,
        relations=(),
        created_snapshot_candidate=None,
    )
    return assembly


def _build_replay_source(
    *,
    source,
    experience,
    decision,
    case_summary,
):
    start = decision["relevant_start_model_call_index"]
    policy_call = source.policy_calls[start]
    episode = source.episode_artifact

    transitions = tuple(
        sorted(
            (
                transition
                for transition in source.public_transitions
                if transition.model_call_index < start
            ),
            key=lambda item: item.environment_step_index,
        )
    )

    expectations = []
    for expected_index, transition in enumerate(transitions):
        if transition.environment_step_index != expected_index:
            raise ValueError(
                "source replay prefix environment-step indices are not contiguous"
            )
        expectations.append(
            ReplayTransitionExpectationV1(
                environment_step_index=expected_index,
                action=transition.submitted_action,
                pre_observation_sha256=(
                    transition.pre_action_observation_sha256
                ),
                pre_menu_sequence_sha256=(
                    transition.pre_action_admissible_commands_sha256
                ),
                resulting_observation_sha256=(
                    transition.resulting_observation_sha256
                ),
                resulting_menu_sequence_sha256=(
                    transition.resulting_admissible_commands_sha256
                ),
                score=transition.score,
                done=transition.done,
                won=transition.won,
            )
        )

    if source.policy_calls[0].model_call_index != 0:
        raise ValueError("source episode policy calls do not start at zero")

    # Full environment prefix identity is distinct from M0. M0 below binds
    # the policy-visible recent executed-history window, whereas this hash
    # binds every real environment transition before the registered source
    # state.
    prefix_payload = [
        {
            "environment_step_index": item.environment_step_index,
            "action": item.action,
            "pre_observation_sha256": item.pre_observation_sha256,
            "pre_menu_sequence_sha256": item.pre_menu_sequence_sha256,
            "resulting_observation_sha256": (
                item.resulting_observation_sha256
            ),
            "resulting_menu_sequence_sha256": (
                item.resulting_menu_sequence_sha256
            ),
            "score": item.score,
            "done": item.done,
            "won": item.won,
        }
        for item in expectations
    ]
    executed_prefix_sha = _sha_domain(
        "SOURCE_EXECUTED_PREFIX_V1",
        prefix_payload,
    )

    budget = dict(policy_call.budget_before)
    budget_state = BudgetState(
        policy_attempt_count=budget["policy_attempt_count"],
        environment_step_count=budget["environment_step_count"],
        protocol_failure_count=budget["protocol_failure_count"],
        inadmissible_action_count=budget["inadmissible_action_count"],
        consecutive_nonexecuted_attempt_count=budget[
            "consecutive_nonexecuted_attempt_count"
        ],
    )

    fingerprint = build_source_decision_state_fingerprint_v1(
        source_task_id=episode.task_id,
        source_gamefile_sha256=episode.gamefile_sha256,
        source_bundle_sha256=source.attempt_bundle.attempt_bundle_sha256,
        source_policy_condition=SOURCE_CONDITION,
        executed_prefix_sha256=executed_prefix_sha,
        observation_sha256=policy_call.observation_sha256,
        menu_sequence_sha256=(
            policy_call.admissible_commands_sequence_sha256
        ),
        memory_m0_sha256=policy_call.executed_history_sha256,
        interface_feedback_code=policy_call.interface_feedback_before,
        budget_state=budget_state,
        model_call_index=start,
        base_policy_input_sha256=policy_call.prompt_sha256,
    )

    reset_call = source.policy_calls[0]
    return RegisteredReplaySourceV1(
        schema_id="REGISTERED_SOURCE_STATE_REPLAY_V1",
        schema_version=1,
        source_task_id=episode.task_id,
        exact_gamefile=case_summary["absolute_gamefile"],
        source_gamefile_sha256=episode.gamefile_sha256,
        source_bundle_sha256=source.attempt_bundle.attempt_bundle_sha256,
        source_policy_condition=SOURCE_CONDITION,
        runtime_manifest_sha256=(
            episode.environment_runtime_manifest_sha256
        ),
        executed_prefix_sha256=executed_prefix_sha,
        reset_observation_sha256=reset_call.observation_sha256,
        reset_menu_sequence_sha256=(
            reset_call.admissible_commands_sequence_sha256
        ),
        transitions=tuple(expectations),
        memory_m0_sha256=policy_call.executed_history_sha256,
        interface_feedback_code=policy_call.interface_feedback_before,
        budget_state=budget_state,
        model_call_index=start,
        base_policy_input_sha256=policy_call.prompt_sha256,
        expected_source_fingerprint=fingerprint,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--source-collection-root", required=True)
    parser.add_argument("--source-panel-manifest", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--task-access-protected-manifest", required=True)
    parser.add_argument("--human-panel-root", required=True)
    parser.add_argument("--human-approval", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--authority-commit", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    observed_head = subprocess.check_output(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        text=True,
    ).strip()
    if observed_head != args.authority_commit:
        raise SystemExit("STOP=FINALIZER_AUTHORITY_COMMIT_MISMATCH")

    output_root = Path(args.output_root).resolve()
    if output_root.exists():
        raise SystemExit("STOP=FINALIZER_OUTPUT_ALREADY_EXISTS")
    output_root.mkdir(parents=True)

    panel_raw = Path(args.source_panel_manifest).read_bytes()
    panel = SourcePanelManifestV1.from_json(panel_raw)
    if panel_raw != panel.canonical_bytes():
        raise SystemExit("STOP=FINALIZER_SOURCE_PANEL_NOT_CANONICAL")
    try:
        _validate_source_collection_code_commit_ancestry(
            repo_root=repo_root,
            source_collection_code_commit=(
                panel.source_collection_code_commit
            ),
            authority_commit=observed_head,
        )
    except ValueError as exc:
        raise SystemExit(
            "STOP=FINALIZER_SOURCE_PANEL_CODE_ANCESTRY_MISMATCH"
        ) from exc

    runtime_raw = Path(args.runtime_binding).read_bytes()
    runtime = strict_json_loads(runtime_raw)
    if not isinstance(runtime, dict):
        raise SystemExit("STOP=FINALIZER_RUNTIME_NOT_OBJECT")
    if sha256_bytes(runtime_raw) != panel.runtime_binding_sha256:
        raise SystemExit("STOP=FINALIZER_RUNTIME_SHA_MISMATCH")

    task_access_path = Path(args.task_access_protected_manifest)
    task_access_raw = task_access_path.read_bytes()
    if sha256_bytes(task_access_raw) != PROTECTED_TASK_ACCESS_SHA256:
        raise SystemExit("STOP=FINALIZER_TASK_ACCESS_AUTHORITY_MISMATCH")

    collection_root = Path(args.source_collection_root).resolve()
    ledger_path = collection_root / "source_collection_ledger.jsonl"
    ledger = read_source_collection_ledger_v1(ledger_path)
    if not ledger:
        raise SystemExit("STOP=FINALIZER_EMPTY_SOURCE_COLLECTION_LEDGER")

    approval, approval_raw, reviewer_id, decisions, human_panel_index = (
        _validate_approval(
            path=Path(args.human_approval),
            human_panel_root=Path(args.human_panel_root),
        )
    )
    approval_sha = sha256_bytes(approval_raw)

    if approval["source_panel_manifest_sha256"] != panel.panel_manifest_sha256:
        raise SystemExit("STOP=FINALIZER_APPROVAL_SOURCE_PANEL_MISMATCH")
    if (
        approval["source_collection_ledger_sha256"]
        != sha256_file(ledger_path)
    ):
        raise SystemExit("STOP=FINALIZER_APPROVAL_LEDGER_SHA_MISMATCH")

    materializer = _load_script(
        repo_root
        / "scripts/memory/materialize_sequence_failure_experience_v1.py",
        "_finalizer_sequence_materializer",
    )

    exact_root = output_root / "exact_inputs"
    registrations_root = exact_root / "failure_window_registrations"
    experience_root = exact_root / "sequence_experiences"
    assembly_root = exact_root / "assembly_registrations"
    replay_root = exact_root / "registered_replays"
    for path in (
        registrations_root,
        experience_root,
        assembly_root,
        replay_root,
    ):
        path.mkdir(parents=True)

    _write_once(
        output_root / "human_approval.json",
        approval_raw,
    )

    materialization_items = []
    replay_cases = []
    exact_records = []

    for item in decisions:
        decision = item["decision"]
        case_summary = item["case_summary"]
        case_id = decision["case_id"]
        panel_index = case_summary["panel_index"]

        receipt = ledger[panel_index]
        if receipt.receipt_sha256 != decision["case_receipt_sha256"]:
            raise SystemExit("STOP=FINALIZER_CASE_RECEIPT_MISMATCH")

        attempt_dir = (
            collection_root
            / "evaluator_run"
            / "attempts"
            / receipt.execution_attempt_id
        )
        source_base = materializer.load_attempt_directory_v1(attempt_dir)
        if (
            source_base.attempt_bundle.attempt_bundle_sha256
            != decision["attempt_bundle_sha256"]
        ):
            raise SystemExit("STOP=FINALIZER_ATTEMPT_BUNDLE_SHA_MISMATCH")

        binding, record_bytes = materializer._binding_from_manifest_line(
            manifest_bytes=task_access_raw,
            line_index=case_summary["task_access_record_line_index"],
        )
        source = SequenceSourceEvidenceV1(
            episode_artifact=source_base.episode_artifact,
            traces=source_base.traces,
            policy_calls=source_base.policy_calls,
            public_transitions=source_base.public_transitions,
            attempt_bundle=source_base.attempt_bundle,
            task_access_record_line_index=(
                case_summary["task_access_record_line_index"]
            ),
            task_access_record_bytes=record_bytes,
        )

        registration_id = "FM-HR-" + _sha_domain(
            "HUMAN_FAILURE_WINDOW_REGISTRATION_ID_V1",
            {
                "approval_sha256": approval_sha,
                "case_id": case_id,
            },
        )[:32]

        registration = RegisteredFailureSequenceWindowV1(
            schema_id="REGISTERED_FAILURE_SEQUENCE_WINDOW_V1",
            schema_version=1,
            registration_id=registration_id,
            registration_authority_type="REGISTERED_BOUNDARY_LABEL",
            registration_protocol_id="HUMAN_REGISTERED_RANGE_V1",
            registration_artifact_sha256=approval_sha,
            registration_record_sha256=item["decision_sha256"],
            source_bundle_sha256=decision["attempt_bundle_sha256"],
            source_attempt_id=decision["source_attempt_id"],
            source_task_id=decision["source_task_id"],
            source_round=SOURCE_ROUND,
            source_condition=SOURCE_CONDITION,
            relevant_start_model_call_index=decision[
                "relevant_start_model_call_index"
            ],
            registered_failure_onset_model_call_index=decision[
                "registered_failure_onset_model_call_index"
            ],
            final_model_call_index=decision["final_model_call_index"],
            registered_recovery_start_model_call_index=decision[
                "registered_recovery_start_model_call_index"
            ],
            registered_recovery_final_model_call_index=decision[
                "registered_recovery_final_model_call_index"
            ],
        )
        registration_bytes = canonical_json_bytes(registration.to_dict())
        registration_path = registrations_root / (case_id + ".json")
        _write_once(registration_path, registration_bytes)

        experience = build_sequence_failure_experience_v1(
            source=source,
            task_access_binding=binding,
            registration=registration,
        )
        experience_path = experience_root / (case_id + ".json")
        _write_once(experience_path, experience.canonical_bytes())

        assembly = _build_assembly(
            experience=experience,
            decision=decision,
            approval_sha=approval_sha,
            reviewer_id=reviewer_id,
        )
        assembly_path = assembly_root / (case_id + ".json")
        _write_once(assembly_path, assembly.canonical_bytes())

        replay = _build_replay_source(
            source=source,
            experience=experience,
            decision=decision,
            case_summary=case_summary,
        )
        replay_path = replay_root / (case_id + ".json")
        _write_once(replay_path, replay.canonical_bytes())

        experience_sha = sha256_file(experience_path)
        assembly_sha = sha256_file(assembly_path)
        contamination = EvaluationContaminationStatusV1.CLEAN

        candidate_id = candidate_id_for_item_v1(
            source_experience_sha256s=(experience_sha,),
            assembly_registration_sha256=assembly_sha,
            previous_record_sha256=None,
            evaluation_contamination_status=contamination,
        )
        candidate_item = CandidateMaterializationItemV1(
            candidate_id=candidate_id,
            source_experience_paths=(str(experience_path),),
            source_experience_sha256s=(experience_sha,),
            assembly_registration_path=str(assembly_path),
            assembly_registration_sha256=assembly_sha,
            previous_record_path=None,
            previous_record_sha256=None,
            evaluation_contamination_status=contamination,
        )

        materialization_items.append(
            {
                "candidate_id": candidate_item.candidate_id,
                "source_experience_paths": list(
                    candidate_item.source_experience_paths
                ),
                "source_experience_sha256s": list(
                    candidate_item.source_experience_sha256s
                ),
                "assembly_registration_path": (
                    candidate_item.assembly_registration_path
                ),
                "assembly_registration_sha256": (
                    candidate_item.assembly_registration_sha256
                ),
                "previous_record_path": None,
                "previous_record_sha256": None,
                "evaluation_contamination_status": contamination.value,
            }
        )

        replay_case_id = _sha_domain(
            "SOURCE_STATE_REPLAY_QUALIFICATION_CASE_V1",
            {
                "source_fingerprint_sha256": (
                    replay.expected_source_fingerprint.fingerprint_sha256
                ),
                "replay_source_sha256": sha256_file(replay_path),
            },
        )
        replay_cases.append(
            {
                "case_id": replay_case_id,
                "replay_source_path": str(replay_path),
                "replay_source_sha256": sha256_file(replay_path),
                "registration_id": (
                    "fm-a9-" + replay_case_id[:20]
                ),
            }
        )

        exact_records.append(
            {
                "case_id": case_id,
                "registration_id": registration_id,
                "registration_sha256": sha256_file(registration_path),
                "experience_id": experience.experience_id,
                "experience_sha256": experience_sha,
                "assembly_registration_id": assembly.registration_id,
                "assembly_sha256": assembly_sha,
                "replay_source_sha256": sha256_file(replay_path),
                "source_fingerprint_sha256": (
                    replay.expected_source_fingerprint.fingerprint_sha256
                ),
                "candidate_id": candidate_id,
                "replay_case_id": replay_case_id,
            }
        )

    materialization_manifest = {
        "authority_commit": observed_head,
        "tokenizer_id": (
            "SOURCE_COLLECTION_POLICY_TOKENIZER_V1:"
            + runtime["tokenizer_identity_manifest_sha256"][:16]
        ),
        "tokenizer_revision": runtime[
            "tokenizer_identity_manifest_sha256"
        ],
        "tokenizer_local_path": runtime["base_model_local_path"],
        "items": materialization_items,
    }
    materialization_bytes = canonical_json_bytes(materialization_manifest)
    materialization_path = output_root / "MATERIALIZATION_MANIFEST.json"
    _write_once(materialization_path, materialization_bytes)

    replay_manifest = {
        "authority_commit": observed_head,
        "cases": replay_cases,
    }
    replay_bytes = canonical_json_bytes(replay_manifest)
    replay_manifest_path = output_root / "REPLAY_QUALIFICATION_MANIFEST.json"
    _write_once(replay_manifest_path, replay_bytes)

    exact_index = {
        "schema_id": "FAILURE_MEMORY_APPROVED_SOURCE_FINALIZATION_INDEX_V1",
        "schema_version": 1,
        "authority_commit": observed_head,
        "human_approval_sha256": approval_sha,
        "source_panel_manifest_sha256": panel.panel_manifest_sha256,
        "source_collection_ledger_sha256": sha256_file(ledger_path),
        "selected_failure_panel_sha256": approval[
            "selected_failure_panel_sha256"
        ],
        "records": exact_records,
        "materialization_manifest_sha256": sha256_bytes(
            materialization_bytes
        ),
        "replay_manifest_sha256": sha256_bytes(replay_bytes),
        "effect_authority": "UNTESTED",
        "policy_exposure": "NOT_EXPOSED_PACKAGE_A",
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        "real_alfworld_executed": False,
        "policy_inference_executed": False,
    }
    _write_once(
        output_root / "FINALIZATION_INDEX.json",
        canonical_json_bytes(exact_index),
    )

    print("APPROVED_FAILURE_WINDOW_COUNT=3")
    print("SEQUENCE_FAILURE_EXPERIENCE_COUNT=3")
    print("PROCEDURAL_ASSEMBLY_REGISTRATION_COUNT=3")
    print("REGISTERED_SOURCE_STATE_REPLAY_COUNT=3")
    print(
        "MATERIALIZATION_MANIFEST_SHA256="
        + sha256_bytes(materialization_bytes)
    )
    print(
        "REPLAY_MANIFEST_SHA256="
        + sha256_bytes(replay_bytes)
    )
    print("EFFECT_AUTHORITY=UNTESTED")
    print("POLICY_EXPOSURE=NOT_EXPOSED_PACKAGE_A")
    print("NO_PERFORMANCE_ESTIMAND")
    print("APPROVED_SOURCE_FINALIZATION_PRE_A9_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
