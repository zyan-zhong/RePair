#!/usr/bin/env python3
"""Read-only offline materializer candidate for SEQUENCE_FAILURE_EXPERIENCE_V1.

This program performs no model call, environment execution, retrieval or
semantic failure analysis. It only loads explicit sealed evidence, validates
its exact identities, reconstructs the already-registered factual sequence,
and writes one canonical output with no-clobber semantics.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from pchsi.evaluation.action_trace import (
    ActionStage,
    ActionTrace,
    TraceProvenance,
)
from pchsi.evaluation.canonical_evidence import (
    sha256_bytes,
    sha256_file,
    strict_json_loads,
)
from pchsi.evaluation.episode_artifact import (
    AttemptBundleBytes,
    build_attempt_bundle_bytes,
)
from pchsi.evaluation.policy_call_evidence import PolicyCallEvidenceV1
from pchsi.evaluation.schema_models import (
    EpisodeArtifactV1,
    PublicTransitionRecordV1,
)
from pchsi.memory.sequence_failure_experience import (
    RegisteredFailureSequenceWindowV1,
    SequenceFailureExperienceV1,
    SequenceSourceEvidenceV1,
    SequenceSourceTaskAccessBindingV1,
    build_sequence_failure_experience_v1,
)


PROTECTED_TASK_ACCESS_MANIFEST_SHA256 = (
    "260766366d72a9af7b0b4809d30a45bb"
    "56f42134dad66b29a4b61ff7ed4793ea"
)
_EXPECTED_ATTEMPT_FILES = frozenset(
    {
        "attempt.json",
        "action_traces.jsonl",
        "policy_calls.jsonl",
        "public_transitions.jsonl",
        "SHA256SUMS",
    }
)


def _require_regular_file(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    if not path.is_file():
        raise ValueError(f"{label} must be a regular file")
    return path


def _require_regular_directory(path: Path, label: str) -> Path:
    path = Path(path)
    if path.is_symlink():
        raise ValueError(f"{label} must not be a symlink")
    if not path.is_dir():
        raise ValueError(f"{label} must be a directory")
    return path


def require_protected_task_access_manifest_v1(path: Path) -> bytes:
    path = _require_regular_file(path, "task-access protected manifest")
    data = path.read_bytes()
    if sha256_bytes(data) != PROTECTED_TASK_ACCESS_MANIFEST_SHA256:
        raise ValueError("protected task-access manifest SHA mismatch")
    return data


def _trace_from_dict(payload: object) -> ActionTrace:
    if not isinstance(payload, dict):
        raise TypeError("ActionTrace JSONL record must be an object")
    provenance_raw = payload.get("provenance")
    if not isinstance(provenance_raw, dict):
        raise TypeError("ActionTrace provenance must be an object")
    provenance = TraceProvenance(**provenance_raw)
    stages_raw = payload.get("stages")
    if not isinstance(stages_raw, list):
        raise TypeError("ActionTrace stages must be an array")
    stages = []
    for raw in stages_raw:
        if not isinstance(raw, dict):
            raise TypeError("ActionTrace stage must be an object")
        expected = {"name", "status", "input_action", "output_action", "changed", "metadata"}
        if set(raw) != expected:
            raise ValueError("ActionTrace stage fields mismatch")
        if raw["changed"] != (raw["input_action"] != raw["output_action"]):
            raise ValueError("ActionTrace stage changed flag mismatch")
        stages.append(
            ActionStage.build(
                name=raw["name"],
                status=raw["status"],
                input_action=raw["input_action"],
                output_action=raw["output_action"],
                metadata=raw["metadata"],
            )
        )
    return ActionTrace.build(
        provenance=provenance,
        pipeline_variant=payload["pipeline_variant"],
        model_call_index=payload["model_call_index"],
        environment_step_index=payload["environment_step_index"],
        execution_status=payload["execution_status"],
        public_task_goal=payload["public_task_goal"],
        observation=payload["observation"],
        prompt_text=payload["prompt_text"],
        admissible_commands=tuple(payload["admissible_commands"]),
        raw_model_response=payload["raw_model_response"],
        literal_action=payload["literal_action"],
        parsed_phase=payload["parsed_phase"],
        model_reason=payload["model_reason"],
        parser_status=payload["parser_status"],
        parser_error=payload["parser_error"],
        parser_metadata=payload["parser_metadata"],
        literal_action_exactly_admissible=payload["literal_action_exactly_admissible"],
        literal_action_casefold_admissible=payload["literal_action_casefold_admissible"],
        stages=tuple(stages),
        final_executed_action=payload["final_executed_action"],
        final_action_admissible=payload["final_action_admissible"],
        attempt_outcome=payload["attempt_outcome"],
        failure_stage=payload["failure_stage"],
        failure_code=payload["failure_code"],
        normalized_action=payload["normalized_action"],
        admissibility_status=payload["admissibility_status"],
        feedback_code=payload["feedback_code"],
        policy_attempt_count_before=payload["policy_attempt_count_before"],
        policy_attempt_count_after=payload["policy_attempt_count_after"],
        environment_step_count_before=payload["environment_step_count_before"],
        environment_step_count_after=payload["environment_step_count_after"],
        protocol_failure_count=payload["protocol_failure_count"],
        inadmissible_action_count=payload["inadmissible_action_count"],
        consecutive_nonexecuted_attempt_count=payload[
            "consecutive_nonexecuted_attempt_count"
        ],
        episode_termination_reason=payload["episode_termination_reason"],
        submitted_environment_action=payload["submitted_environment_action"],
        resulting_observation=payload["resulting_observation"],
        environment_event_flags=payload["environment_event_flags"],
        protocol_failure_count_before=payload["protocol_failure_count_before"],
        inadmissible_action_count_before=payload["inadmissible_action_count_before"],
        consecutive_nonexecuted_attempt_count_before=payload[
            "consecutive_nonexecuted_attempt_count_before"
        ],
    )


def _load_jsonl(path: Path, parser) -> tuple[object, ...]:
    data = _require_regular_file(path, path.name).read_bytes()
    result = []
    for index, line in enumerate(data.splitlines(keepends=True)):
        if not line.endswith(b"\n"):
            raise ValueError(f"{path.name} line {index} lacks terminal LF")
        result.append(parser(line))
    return tuple(result)


def load_attempt_directory_v1(attempt_dir: Path) -> SequenceSourceEvidenceV1:
    attempt_dir = _require_regular_directory(attempt_dir, "attempt directory")
    names = {item.name for item in attempt_dir.iterdir()}
    if "policy_calls.jsonl" not in names:
        raise ValueError("POLICY_CALL_EVIDENCE_REQUIRED")
    if names != _EXPECTED_ATTEMPT_FILES:
        raise ValueError(
            f"attempt directory files mismatch: observed={sorted(names)}"
        )
    for item in attempt_dir.iterdir():
        if item.is_symlink() or not item.is_file():
            raise ValueError("attempt directory may contain only regular non-symlink files")

    episode = EpisodeArtifactV1.from_json(
        (attempt_dir / "attempt.json").read_bytes()
    )
    traces = _load_jsonl(
        attempt_dir / "action_traces.jsonl",
        lambda line: _trace_from_dict(strict_json_loads(line)),
    )
    policy_calls = _load_jsonl(
        attempt_dir / "policy_calls.jsonl",
        PolicyCallEvidenceV1.from_json,
    )
    transitions = _load_jsonl(
        attempt_dir / "public_transitions.jsonl",
        PublicTransitionRecordV1.from_json,
    )

    expected = build_attempt_bundle_bytes(
        episode_artifact=episode,
        traces=traces,
        policy_calls=policy_calls,
        public_transitions=transitions,
    )
    observed_files = {
        name: (attempt_dir / name).read_bytes()
        for name in _EXPECTED_ATTEMPT_FILES
    }
    for name, data in expected.file_bytes():
        if observed_files[name] != data:
            raise ValueError(f"attempt bundle member bytes mismatch: {name}")

    return SequenceSourceEvidenceV1(
        episode_artifact=episode,
        traces=traces,
        policy_calls=policy_calls,
        public_transitions=transitions,
        attempt_bundle=expected,
        task_access_record_line_index=0,
        task_access_record_bytes=b"{}\n",
    )


def _binding_from_manifest_line(
    *,
    manifest_bytes: bytes,
    line_index: int,
) -> tuple[SequenceSourceTaskAccessBindingV1, bytes]:
    if type(line_index) is not int or line_index < 0:
        raise ValueError("task-access line index must be non-negative int")
    lines = manifest_bytes.splitlines(keepends=True)
    if line_index >= len(lines):
        raise ValueError("task-access line index outside protected manifest")
    record_bytes = lines[line_index]
    if not record_bytes.endswith(b"\n"):
        raise ValueError("task-access JSONL record lacks terminal LF")
    payload = strict_json_loads(record_bytes)
    if not isinstance(payload, dict):
        raise ValueError("task-access record must be JSON object")
    if payload.get("access_class") != "TRAIN_MEMORY_SOURCE":
        raise ValueError("active sequence materialization requires TRAIN_MEMORY_SOURCE")
    binding = SequenceSourceTaskAccessBindingV1(
        schema_id="SEQUENCE_SOURCE_TASK_ACCESS_BINDING_V1",
        schema_version=1,
        task_access_protected_manifest_sha256=PROTECTED_TASK_ACCESS_MANIFEST_SHA256,
        task_access_record_line_index=line_index,
        task_access_record_sha256=sha256_bytes(record_bytes),
        task_gamefile_group_id=payload["task_gamefile_group_id"],
        dataset_relative_gamefile=payload["dataset_relative_gamefile"],
        gamefile_sha256=payload["gamefile_sha256"],
        task_type=payload["task_type"],
        split=payload["split"],
        access_class=payload["access_class"],
    )
    return binding, record_bytes


def materialize_prevalidated_v1(
    *,
    experience: SequenceFailureExperienceV1,
    output_path: Path,
) -> None:
    if not isinstance(experience, SequenceFailureExperienceV1):
        raise TypeError("experience must be SequenceFailureExperienceV1")
    output_path = Path(output_path)
    if output_path.is_symlink():
        raise ValueError("output path must not be a symlink")
    parent = output_path.parent
    if parent.is_symlink() or not parent.is_dir():
        raise ValueError("output parent must be an existing non-symlink directory")
    data = experience.canonical_bytes()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    fd = os.open(output_path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except Exception:
        try:
            output_path.unlink(missing_ok=True)
        finally:
            raise


def _load_registration(path: Path) -> RegisteredFailureSequenceWindowV1:
    payload = strict_json_loads(_require_regular_file(path, "registration").read_bytes())
    return RegisteredFailureSequenceWindowV1.from_dict(payload)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--attempt-dir", required=True)
    parser.add_argument("--registration", required=True)
    parser.add_argument("--task-access-protected-manifest", required=True)
    parser.add_argument("--task-access-record-line-index", required=True, type=int)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    manifest_bytes = require_protected_task_access_manifest_v1(
        Path(args.task_access_protected_manifest)
    )
    binding, record_bytes = _binding_from_manifest_line(
        manifest_bytes=manifest_bytes,
        line_index=args.task_access_record_line_index,
    )
    source = load_attempt_directory_v1(Path(args.attempt_dir))
    source = SequenceSourceEvidenceV1(
        episode_artifact=source.episode_artifact,
        traces=source.traces,
        policy_calls=source.policy_calls,
        public_transitions=source.public_transitions,
        attempt_bundle=source.attempt_bundle,
        task_access_record_line_index=args.task_access_record_line_index,
        task_access_record_bytes=record_bytes,
    )
    registration = _load_registration(Path(args.registration))
    experience = build_sequence_failure_experience_v1(
        source=source,
        task_access_binding=binding,
        registration=registration,
    )
    materialize_prevalidated_v1(
        experience=experience,
        output_path=Path(args.output),
    )
    print(f"experience_id={experience.experience_id}")
    print(f"output_sha256={sha256_file(Path(args.output))}")
    print("SEQUENCE_FAILURE_EXPERIENCE_MATERIALIZER_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
