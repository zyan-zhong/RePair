#!/usr/bin/env python3
"""Run the frozen calibration-only Hierarchical Analyzer on 30 failures.

The first 30 failure identities are already frozen by the source-calibration
panel before this program is allowed to call the model. Analyzer output is
calibration-only and creates no active Memory authority.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

from openai import OpenAI

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.token_budget_calibration import (
    ANALYZER_AUTHORITY,
    ANALYZER_RESULT_SCHEMA_V1,
    TokenBudgetAnalyzerResultV1,
)
from pchsi.memory.token_budget_contract import (
    CALIBRATION_FAILURE_TARGET_V1,
    NO_PERFORMANCE_ESTIMAND,
)


PROMPT_ID = "FAILURE_MEMORY_TOKEN_BUDGET_ANALYZER_PROMPT_V1"

SYSTEM_PROMPT = """You are the Hierarchical Analyzer for a train-side, pre-outcome Failure Memory token-budget calibration.

Your output is a CALIBRATION_ONLY_ANALYZER_PROPOSAL. It will be used only to estimate representation lengths before any Memory-assisted policy execution. It is not factual registration authority, Benefit/Harm evidence, or policy advice.

Given one failed agent trajectory:
1. localize one contiguous failure-relevant window;
2. identify the first model call where the terminal failure mechanism begins to manifest;
3. include enough immediately preceding context to make the failure development understandable;
4. end at the final relevant call, normally the episode terminal call;
5. produce concise descriptive activation cues, one concise failure-pattern hypothesis, concise release cues, and optional non-applicability cues.

Rules:
- Use only model_call_index values present in the provided timeline.
- Require relevant_start <= failure_onset <= final.
- Prefer the terminal failure development over earlier isolated errors that were recovered.
- Activation/release cues must describe Policy-visible or environment-visible state, not hidden state.
- The failure pattern is a SEMANTIC HYPOTHESIS, not factual truth.
- Do not output an exact next environment action, numbered menu choice, oracle path, task/source identity, seed, Memory ID, Benefit/Harm label, performance estimate, or future outcome.
- Do not mention benchmark performance.
- Keep each cue short because this is representation-length calibration.
- If the evidence does not support a defensible contiguous window, return ABSTAIN and leave all semantic arrays empty and all indices null.
"""


OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "status": {
            "type": "string",
            "enum": ["ANALYZED", "ABSTAIN"],
        },
        "relevant_start_model_call_index": {
            "type": ["integer", "null"],
        },
        "failure_onset_model_call_index": {
            "type": ["integer", "null"],
        },
        "final_model_call_index": {
            "type": ["integer", "null"],
        },
        "activation_cues": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "failure_pattern": {
            "type": "string",
        },
        "release_cues": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 3,
        },
        "non_applicability_cues": {
            "type": "array",
            "items": {"type": "string"},
            "maxItems": 2,
        },
    },
    "required": [
        "status",
        "relevant_start_model_call_index",
        "failure_onset_model_call_index",
        "final_model_call_index",
        "activation_cues",
        "failure_pattern",
        "release_cues",
        "non_applicability_cues",
    ],
}


def _load_attempt_loader(repo_root: Path):
    path = (
        repo_root
        / "scripts/memory/materialize_sequence_failure_experience_v1.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_token_budget_analyzer_attempt_loader",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load attempt evidence loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_once(path: Path, data: bytes) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _timeline(source) -> list[dict[str, object]]:
    policy_calls = {
        item.model_call_index: item
        for item in source.policy_calls
    }
    transitions = {
        item.model_call_index: item
        for item in source.public_transitions
    }

    rows = []
    for trace in source.traces:
        call = policy_calls.get(trace.model_call_index)
        if call is None:
            raise ValueError("trace lacks corresponding policy call")
        transition = transitions.get(trace.model_call_index)

        rows.append(
            {
                "model_call_index": trace.model_call_index,
                "environment_step_index": trace.environment_step_index,
                "pre_observation": call.observation,
                "literal_action": trace.literal_action,
                "normalized_action": trace.normalized_action,
                "submitted_environment_action": (
                    trace.submitted_environment_action
                ),
                "execution_status": trace.execution_status.value,
                "interface_feedback_before": (
                    call.interface_feedback_before
                ),
                "attempt_outcome": trace.attempt_outcome,
                "failure_stage": trace.failure_stage,
                "failure_code": trace.failure_code,
                "resulting_observation": (
                    None
                    if transition is None
                    else transition.resulting_observation
                ),
                "score": (
                    None if transition is None else transition.score
                ),
                "done": (
                    None if transition is None else transition.done
                ),
                "won": (
                    None if transition is None else transition.won
                ),
            }
        )

    indices = [
        item["model_call_index"]
        for item in rows
    ]
    if indices != list(range(len(indices))):
        raise ValueError("trajectory model-call indices are not contiguous")
    return rows


def _validate_raw_output(
    *,
    value: object,
    valid_indices: set[int],
) -> dict[str, object]:
    if not isinstance(value, dict):
        raise TypeError("Analyzer output must be object")
    if set(value) != set(OUTPUT_SCHEMA["properties"]):
        raise ValueError("Analyzer output fields mismatch")

    status = value["status"]
    if status == "ABSTAIN":
        if any(
            value[name] is not None
            for name in (
                "relevant_start_model_call_index",
                "failure_onset_model_call_index",
                "final_model_call_index",
            )
        ):
            raise ValueError("ABSTAIN indices must be null")
        if (
            value["activation_cues"]
            or value["failure_pattern"]
            or value["release_cues"]
            or value["non_applicability_cues"]
        ):
            raise ValueError("ABSTAIN semantic fields must be empty")
        return value

    if status != "ANALYZED":
        raise ValueError("unknown Analyzer status")

    start = value["relevant_start_model_call_index"]
    onset = value["failure_onset_model_call_index"]
    final = value["final_model_call_index"]

    if any(
        type(index) is not int or index not in valid_indices
        for index in (start, onset, final)
    ):
        raise ValueError("Analyzer index outside supplied trajectory")
    if not start <= onset <= final:
        raise ValueError("Analyzer index order invalid")

    for name in (
        "activation_cues",
        "release_cues",
        "non_applicability_cues",
    ):
        raw = value[name]
        if not isinstance(raw, list):
            raise TypeError(f"{name} must be array")
        if any(not isinstance(item, str) or not item for item in raw):
            raise ValueError(f"{name} must contain nonempty strings")
    if (
        not isinstance(value["failure_pattern"], str)
        or not value["failure_pattern"]
    ):
        raise ValueError("ANALYZED failure_pattern required")

    return value


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--failure-panel", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--model", required=True)
    args = parser.parse_args()

    if args.model != "gpt-5.6-sol":
        raise SystemExit(
            "STOP=TOKEN_BUDGET_ANALYZER_MODEL_MUST_BE_GPT_5_6_SOL"
        )

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit("STOP=OPENAI_API_KEY_MISSING")

    repo_root = Path(args.repo_root).resolve()
    panel_path = Path(args.failure_panel)
    panel_raw = panel_path.read_bytes()
    panel = strict_json_loads(panel_raw)

    if not isinstance(panel, dict):
        raise SystemExit("STOP=CALIBRATION_FAILURE_PANEL_NOT_OBJECT")
    if (
        panel.get("schema_id")
        != "FAILURE_MEMORY_TOKEN_BUDGET_FAILURE_PANEL_V1"
        or panel.get("failure_count")
        != CALIBRATION_FAILURE_TARGET_V1
        or panel.get("performance_estimand")
        != NO_PERFORMANCE_ESTIMAND
        or panel.get("memory_on_execution_used") is not False
    ):
        raise SystemExit("STOP=CALIBRATION_FAILURE_PANEL_CONTRACT_INVALID")

    failures = panel.get("failures")
    if not isinstance(failures, list) or len(failures) != 30:
        raise SystemExit("STOP=CALIBRATION_FAILURE_PANEL_COUNT_INVALID")

    panel_indices = [
        item.get("panel_index")
        for item in failures
    ]
    if (
        any(type(item) is not int for item in panel_indices)
        or panel_indices != sorted(panel_indices)
        or len(set(panel_indices)) != len(panel_indices)
    ):
        raise SystemExit("STOP=CALIBRATION_FAILURE_PANEL_ORDER_INVALID")

    output_root = Path(args.output_root).resolve()
    if output_root.is_symlink():
        raise SystemExit("STOP=ANALYZER_OUTPUT_ROOT_SYMLINK")
    output_root.mkdir(parents=True, exist_ok=True)

    prompt_payload = {
        "prompt_id": PROMPT_ID,
        "system_prompt": SYSTEM_PROMPT,
        "output_schema": OUTPUT_SCHEMA,
        "model": args.model,
        "calibration_failure_panel_sha256": sha256_bytes(panel_raw),
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        "memory_on_execution_used": False,
    }
    prompt_bytes = canonical_json_bytes(prompt_payload)
    prompt_path = output_root / "analyzer_prompt.json"
    if prompt_path.exists():
        if prompt_path.read_bytes() != prompt_bytes:
            raise SystemExit("STOP=ANALYZER_PROMPT_ALREADY_EXISTS_MISMATCH")
    else:
        _write_once(prompt_path, prompt_bytes)

    prompt_sha = sha256_bytes(prompt_bytes)
    attempt_loader = _load_attempt_loader(repo_root)
    client = OpenAI(max_retries=0)

    analyzed = 0
    abstained = 0

    for ordinal, failure in enumerate(failures):
        failure_id = (
            "FM-TB-F"
            + f"{ordinal:02d}"
            + "-"
            + failure["attempt_bundle_sha256"][:12]
        )
        case_root = output_root / "cases" / failure_id
        result_path = case_root / "analyzer_result.json"
        request_path = case_root / "request.json"
        response_path = case_root / "response.json"

        if result_path.is_file():
            result = TokenBudgetAnalyzerResultV1.from_json(
                result_path.read_bytes()
            )
            if result.failure_id != failure_id:
                raise SystemExit(
                    "STOP=EXISTING_ANALYZER_RESULT_ID_MISMATCH:"
                    + failure_id
                )
            if result.status == "ANALYZED":
                analyzed += 1
            else:
                abstained += 1
            continue

        if request_path.exists() or response_path.exists():
            raise SystemExit(
                "STOP=AMBIGUOUS_PRIOR_ANALYZER_CALL_REQUIRES_AUDIT:"
                + failure_id
            )

        attempt_dir = Path(failure["attempt_directory"])
        source = attempt_loader.load_attempt_directory_v1(
            attempt_dir
        )
        if (
            source.attempt_bundle.attempt_bundle_sha256
            != failure["attempt_bundle_sha256"]
        ):
            raise SystemExit(
                "STOP=ANALYZER_ATTEMPT_BUNDLE_MISMATCH:"
                + failure_id
            )
        if source.episode_artifact.success is not False:
            raise SystemExit(
                "STOP=ANALYZER_PANEL_ITEM_NOT_FAILURE:"
                + failure_id
            )

        timeline = _timeline(source)
        user_payload = {
            "trajectory_termination_reason": (
                source.episode_artifact.termination_reason
            ),
            "timeline": timeline,
        }
        user_text = canonical_json_bytes(
            user_payload
        ).decode("utf-8")

        client_request_id = (
            "fm-token-budget-"
            + hashlib.sha256(
                (
                    failure_id
                    + "\0"
                    + prompt_sha
                ).encode("utf-8")
            ).hexdigest()[:32]
        )

        request_receipt = {
            "schema_id": "FAILURE_MEMORY_TOKEN_BUDGET_ANALYZER_REQUEST_V1",
            "schema_version": 1,
            "failure_id": failure_id,
            "panel_index": failure["panel_index"],
            "attempt_bundle_sha256": failure[
                "attempt_bundle_sha256"
            ],
            "model": args.model,
            "analyzer_prompt_sha256": prompt_sha,
            "input_sha256": hashlib.sha256(
                user_text.encode("utf-8")
            ).hexdigest(),
            "client_request_id": client_request_id,
            "store": False,
            "performance_estimand": NO_PERFORMANCE_ESTIMAND,
            "memory_on_execution_used": False,
        }
        _write_once(
            request_path,
            canonical_json_bytes(request_receipt),
        )

        try:
            response = client.responses.create(
                model=args.model,
                input=[
                    {
                        "role": "system",
                        "content": SYSTEM_PROMPT,
                    },
                    {
                        "role": "user",
                        "content": user_text,
                    },
                ],
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "failure_memory_token_budget_analyzer",
                        "schema": OUTPUT_SCHEMA,
                        "strict": True,
                    }
                },
                reasoning={
                    "effort": "high",
                },
                max_output_tokens=1600,
                store=False,
                extra_headers={
                    "X-Client-Request-Id": client_request_id,
                },
            )
        except BaseException as exc:
            error = {
                "schema_id": (
                    "FAILURE_MEMORY_TOKEN_BUDGET_ANALYZER_CALL_ERROR_V1"
                ),
                "schema_version": 1,
                "failure_id": failure_id,
                "exception_type": type(exc).__name__,
                "exception_text": str(exc),
                "scientific_disposition": (
                    "AMBIGUOUS_POST_REQUEST_NO_AUTOMATIC_RETRY"
                ),
            }
            _write_once(
                case_root / "call_error.json",
                canonical_json_bytes(error),
            )
            raise SystemExit(
                "STOP=ANALYZER_API_CALL_FAILED_NO_AUTOMATIC_RETRY:"
                + failure_id
            ) from exc

        output_text = response.output_text
        if not isinstance(output_text, str) or not output_text:
            raise SystemExit(
                "STOP=ANALYZER_EMPTY_OUTPUT:"
                + failure_id
            )

        raw_value = strict_json_loads(
            output_text.encode("utf-8") + (
                b"" if output_text.endswith("\n") else b"\n"
            )
        )
        raw_value = _validate_raw_output(
            value=raw_value,
            valid_indices={
                item["model_call_index"]
                for item in timeline
            },
        )

        response_sha = hashlib.sha256(
            output_text.encode("utf-8")
        ).hexdigest()
        request_id = getattr(
            response,
            "_request_id",
            None,
        )
        response_model = getattr(
            response,
            "model",
            args.model,
        )

        result = TokenBudgetAnalyzerResultV1(
            schema_id=ANALYZER_RESULT_SCHEMA_V1,
            schema_version=1,
            failure_id=failure_id,
            status=raw_value["status"],
            relevant_start_model_call_index=raw_value[
                "relevant_start_model_call_index"
            ],
            failure_onset_model_call_index=raw_value[
                "failure_onset_model_call_index"
            ],
            final_model_call_index=raw_value[
                "final_model_call_index"
            ],
            activation_cues=tuple(
                raw_value["activation_cues"]
            ),
            failure_pattern=raw_value[
                "failure_pattern"
            ],
            release_cues=tuple(
                raw_value["release_cues"]
            ),
            non_applicability_cues=tuple(
                raw_value["non_applicability_cues"]
            ),
            authority=ANALYZER_AUTHORITY,
            request_id=request_id,
            response_model=response_model,
            response_sha256=response_sha,
        )

        response_receipt = {
            "schema_id": "FAILURE_MEMORY_TOKEN_BUDGET_ANALYZER_RESPONSE_V1",
            "schema_version": 1,
            "failure_id": failure_id,
            "request_id": request_id,
            "response_model": response_model,
            "output_text_sha256": response_sha,
            "output_text": output_text,
            "authority": ANALYZER_AUTHORITY,
            "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        }
        _write_once(
            response_path,
            canonical_json_bytes(response_receipt),
        )
        _write_once(
            result_path,
            result.canonical_bytes(),
        )

        if result.status == "ANALYZED":
            analyzed += 1
        else:
            abstained += 1

        print(
            "TOKEN_BUDGET_ANALYZER_CASE_COMPLETE"
            + " failure_id="
            + failure_id
            + " status="
            + result.status
        )

    index = {
        "schema_id": "FAILURE_MEMORY_TOKEN_BUDGET_ANALYZER_INDEX_V1",
        "schema_version": 1,
        "calibration_failure_panel_sha256": sha256_bytes(panel_raw),
        "analyzer_prompt_sha256": prompt_sha,
        "analyzer_model": args.model,
        "failure_count": 30,
        "analyzed_count": analyzed,
        "abstain_count": abstained,
        "authority": ANALYZER_AUTHORITY,
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        "memory_on_execution_used": False,
    }
    index_path = output_root / "analyzer_index.json"
    index_bytes = canonical_json_bytes(index)
    if index_path.exists():
        if index_path.read_bytes() != index_bytes:
            raise SystemExit("STOP=ANALYZER_INDEX_MISMATCH")
    else:
        _write_once(index_path, index_bytes)

    print("TOKEN_BUDGET_ANALYZER_FAILURE_COUNT=30")
    print("TOKEN_BUDGET_ANALYZER_ANALYZED_COUNT=" + str(analyzed))
    print("TOKEN_BUDGET_ANALYZER_ABSTAIN_COUNT=" + str(abstained))
    print("TOKEN_BUDGET_ANALYZER_AUTHORITY=" + ANALYZER_AUTHORITY)
    print("NO_PERFORMANCE_ESTIMAND")
    print("TOKEN_BUDGET_ANALYZER_COMPLETE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
