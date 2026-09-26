#!/usr/bin/env python3
"""Build frozen token-budget contract from outcome-blind calibration lengths."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from transformers import AutoTokenizer

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.policy_view_safety import (
    policy_visible_contains_bound_identity_v1,
)
from pchsi.memory.token_budget_calibration import (
    TokenBudgetAnalyzerResultV1,
    build_calibration_fm2_payload_v1,
    build_complete_window_fm1_payload_v1,
    calibration_payload_safety_v1,
    exact_library_pack_count_v1,
    exact_token_count_v1,
)
from pchsi.memory.token_budget_contract import (
    CALIBRATION_FAILURE_TARGET_V1,
    COVERAGE_TARGET_V1,
    FailureMemoryTokenBudgetContractV1,
    FM1_LLM_COMPRESSION_POLICY,
    FM1_POSTHOC_EXCERPT_POLICY,
    FM1_TRUNCATION_POLICY,
    LIBRARY_TOTAL_CANDIDATES_V1,
    MAX_RECORD_COUNT_V1,
    MIN_VALID_CALIBRATION_RECORDS_V1,
    NO_PERFORMANCE_ESTIMAND,
    SINGLE_RECORD_CANDIDATES_V1,
    TOKEN_BUDGET_SCHEMA_V1,
    choose_smallest_ceiling_v1,
)


class LocalTokenizerCounter:
    def __init__(
        self,
        *,
        tokenizer_id: str,
        tokenizer_revision: str,
        local_path: Path,
    ):
        self.tokenizer_id = tokenizer_id
        self.tokenizer_revision = tokenizer_revision
        self._tokenizer = AutoTokenizer.from_pretrained(
            str(local_path),
            local_files_only=True,
            trust_remote_code=False,
        )

    def count_tokens(self, text: str) -> int:
        return len(
            self._tokenizer.encode(
                text,
                add_special_tokens=False,
            )
        )


def _load_attempt_loader(repo_root: Path):
    path = (
        repo_root
        / "scripts/memory/materialize_sequence_failure_experience_v1.py"
    )
    spec = importlib.util.spec_from_file_location(
        "_token_budget_contract_attempt_loader",
        path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load attempt evidence loader")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _failure_id(ordinal: int, failure: dict[str, object]) -> str:
    return (
        "FM-TB-F"
        + f"{ordinal:02d}"
        + "-"
        + failure["attempt_bundle_sha256"][:12]
    )


def _forbidden_source_identities(source) -> tuple[str, ...]:
    values = []

    episode = source.episode_artifact
    for value in (
        episode.task_id,
        episode.gamefile_sha256,
        episode.execution_attempt_id,
        source.attempt_bundle.attempt_bundle_sha256,
    ):
        if isinstance(value, str) and value:
            values.append(value)

    return tuple(dict.fromkeys(values))


def _source_identity_clean(
    *,
    payload: dict[str, object],
    source,
) -> bool:
    return not policy_visible_contains_bound_identity_v1(
        policy_visible_payload=payload,
        forbidden_exact_identities=(
            _forbidden_source_identities(source)
        ),
    )


def _write_jsonl(
    path: Path,
    rows: list[dict[str, object]],
) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    with path.open("wb") as handle:
        for row in rows:
            handle.write(canonical_json_bytes(row))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--failure-panel", required=True)
    parser.add_argument("--analyzer-root", required=True)
    parser.add_argument("--runtime-binding", required=True)
    parser.add_argument("--source-panel-manifest", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    failure_panel_path = Path(args.failure_panel)
    failure_panel_raw = failure_panel_path.read_bytes()
    failure_panel = strict_json_loads(failure_panel_raw)

    if (
        not isinstance(failure_panel, dict)
        or failure_panel.get("failure_count")
        != CALIBRATION_FAILURE_TARGET_V1
        or failure_panel.get("performance_estimand")
        != NO_PERFORMANCE_ESTIMAND
        or failure_panel.get("memory_on_execution_used") is not False
    ):
        raise SystemExit("STOP=FAILURE_PANEL_INVALID_FOR_BUDGET_FREEZE")

    failures = failure_panel.get("failures")
    if not isinstance(failures, list) or len(failures) != 30:
        raise SystemExit("STOP=FAILURE_PANEL_COUNT_NOT_30")

    analyzer_root = Path(args.analyzer_root)
    analyzer_index = strict_json_loads(
        (analyzer_root / "analyzer_index.json").read_bytes()
    )
    if (
        not isinstance(analyzer_index, dict)
        or analyzer_index.get("failure_count") != 30
        or analyzer_index.get("performance_estimand")
        != NO_PERFORMANCE_ESTIMAND
        or analyzer_index.get("memory_on_execution_used") is not False
    ):
        raise SystemExit("STOP=ANALYZER_INDEX_INVALID")

    runtime = strict_json_loads(
        Path(args.runtime_binding).read_bytes()
    )
    if not isinstance(runtime, dict):
        raise SystemExit("STOP=RUNTIME_BINDING_NOT_OBJECT")

    source_panel = strict_json_loads(
        Path(args.source_panel_manifest).read_bytes()
    )
    if not isinstance(source_panel, dict):
        raise SystemExit("STOP=SOURCE_PANEL_NOT_OBJECT")

    tokenizer_revision = runtime[
        "tokenizer_identity_manifest_sha256"
    ]
    tokenizer = LocalTokenizerCounter(
        tokenizer_id=(
            "TOKEN_BUDGET_POLICY_TOKENIZER_V1:"
            + tokenizer_revision[:16]
        ),
        tokenizer_revision=tokenizer_revision,
        local_path=Path(runtime["base_model_local_path"]),
    )

    attempt_loader = _load_attempt_loader(repo_root)

    ledger_rows = []
    valid = []

    for ordinal, failure in enumerate(failures):
        fid = _failure_id(ordinal, failure)
        result_path = (
            analyzer_root
            / "cases"
            / fid
            / "analyzer_result.json"
        )
        if not result_path.is_file():
            raise SystemExit(
                "STOP=ANALYZER_RESULT_MISSING:"
                + fid
            )

        result = TokenBudgetAnalyzerResultV1.from_json(
            result_path.read_bytes()
        )
        if result.failure_id != fid:
            raise SystemExit(
                "STOP=ANALYZER_FAILURE_ID_MISMATCH:"
                + fid
            )

        row = {
            "ordinal": ordinal,
            "failure_id": fid,
            "panel_index": failure["panel_index"],
            "attempt_bundle_sha256": failure[
                "attempt_bundle_sha256"
            ],
            "analyzer_status": result.status,
            "calibration_disposition": None,
            "fm1_token_count": None,
            "fm2_token_count": None,
            "fm1_safety_status": None,
            "fm2_safety_status": None,
            "source_identity_clean": None,
            "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        }

        if result.status == "ABSTAIN":
            row["calibration_disposition"] = "ANALYZER_ABSTAIN"
            ledger_rows.append(row)
            continue

        source = attempt_loader.load_attempt_directory_v1(
            Path(failure["attempt_directory"])
        )
        if (
            source.attempt_bundle.attempt_bundle_sha256
            != failure["attempt_bundle_sha256"]
            or source.episode_artifact.success is not False
        ):
            raise SystemExit(
                "STOP=CALIBRATION_ATTEMPT_IDENTITY_INVALID:"
                + fid
            )

        try:
            fm1_payload = build_complete_window_fm1_payload_v1(
                source=source,
                analyzer_result=result,
            )
            fm2_payload = build_calibration_fm2_payload_v1(
                result
            )
        except (ValueError, TypeError) as exc:
            row["calibration_disposition"] = (
                "ANALYZER_RANGE_INVALID:"
                + type(exc).__name__
            )
            ledger_rows.append(row)
            continue

        fm1_report, fm2_report = (
            calibration_payload_safety_v1(
                fm1_payload=fm1_payload,
                fm2_payload=fm2_payload,
            )
        )

        source_identity_clean = (
            _source_identity_clean(
                payload=fm1_payload.to_dict(),
                source=source,
            )
            and _source_identity_clean(
                payload=fm2_payload.to_dict(),
                source=source,
            )
        )

        row["fm1_safety_status"] = fm1_report.static_status
        row["fm2_safety_status"] = fm2_report.static_status
        row["source_identity_clean"] = source_identity_clean

        if (
            fm1_report.static_status != "PASS"
            or fm1_report.critical_safety_failure
            or fm1_report.static_failure_codes
            or fm2_report.static_status != "PASS"
            or fm2_report.critical_safety_failure
            or fm2_report.static_failure_codes
            or not source_identity_clean
        ):
            row["calibration_disposition"] = (
                "STATIC_POLICY_VIEW_SAFETY_OR_IDENTITY_REJECT"
            )
            ledger_rows.append(row)
            continue

        fm1_count = exact_token_count_v1(
            payload=fm1_payload.to_dict(),
            tokenizer=tokenizer,
        )
        fm2_count = exact_token_count_v1(
            payload=fm2_payload.to_dict(),
            tokenizer=tokenizer,
        )

        row["fm1_token_count"] = fm1_count
        row["fm2_token_count"] = fm2_count
        row["calibration_disposition"] = "VALID_LENGTH_RECORD"

        valid.append(
            {
                "ordinal": ordinal,
                "failure_id": fid,
                "fm1_payload": fm1_payload.to_dict(),
                "fm2_payload": fm2_payload.to_dict(),
                "fm1_token_count": fm1_count,
                "fm2_token_count": fm2_count,
            }
        )
        ledger_rows.append(row)

    if len(valid) < MIN_VALID_CALIBRATION_RECORDS_V1:
        raise SystemExit(
            "STOP=VALID_TOKEN_BUDGET_CALIBRATION_RECORDS_BELOW_20:"
            + str(len(valid))
        )

    fm1_counts = tuple(
        item["fm1_token_count"]
        for item in valid
    )
    fm2_counts = tuple(
        item["fm2_token_count"]
        for item in valid
    )

    # Valid records remain in frozen failure order. Pack consecutive,
    # non-overlapping triples; no replacement for rejected/abstained records.
    pack_counts = []
    for start in range(0, len(valid) - 2, 3):
        group = valid[start : start + 3]
        if len(group) != 3:
            break
        pack_counts.append(
            exact_library_pack_count_v1(
                payloads=tuple(
                    item["fm2_payload"]
                    for item in group
                ),
                tokenizer=tokenizer,
            )
        )

    if not pack_counts:
        raise SystemExit("STOP=NO_VALID_THREE_RECORD_LIBRARY_PACK")

    single = choose_smallest_ceiling_v1(
        observed_token_counts=fm1_counts,
        candidates=SINGLE_RECORD_CANDIDATES_V1,
        coverage_target=COVERAGE_TARGET_V1,
    )
    library = choose_smallest_ceiling_v1(
        observed_token_counts=tuple(pack_counts),
        candidates=LIBRARY_TOTAL_CANDIDATES_V1,
        coverage_target=COVERAGE_TARGET_V1,
    )

    prompt_raw = (
        analyzer_root
        / "analyzer_prompt.json"
    ).read_bytes()

    contract = FailureMemoryTokenBudgetContractV1(
        schema_id=TOKEN_BUDGET_SCHEMA_V1,
        schema_version=1,
        source_panel_manifest_sha256=source_panel[
            "panel_manifest_sha256"
        ],
        calibration_failure_panel_sha256=sha256_bytes(
            failure_panel_raw
        ),
        analyzer_prompt_sha256=sha256_bytes(prompt_raw),
        analyzer_model=analyzer_index["analyzer_model"],
        tokenizer_id=tokenizer.tokenizer_id,
        tokenizer_revision=tokenizer.tokenizer_revision,
        calibration_failure_count=30,
        valid_calibration_record_count=len(valid),
        fm1_token_counts=fm1_counts,
        fm2_token_counts=fm2_counts,
        library_pack_token_counts=tuple(pack_counts),
        single_record_candidates=SINGLE_RECORD_CANDIDATES_V1,
        library_total_candidates=LIBRARY_TOTAL_CANDIDATES_V1,
        coverage_target=COVERAGE_TARGET_V1,
        single_record_hard_ceiling=single,
        library_total_hard_ceiling=library,
        max_record_count=MAX_RECORD_COUNT_V1,
        fm1_truncation_policy=FM1_TRUNCATION_POLICY,
        fm1_llm_compression_policy=FM1_LLM_COMPRESSION_POLICY,
        fm1_posthoc_excerpt_policy=FM1_POSTHOC_EXCERPT_POLICY,
        performance_estimand=NO_PERFORMANCE_ESTIMAND,
        memory_on_execution_used=False,
        contract_sha256=None,
    )

    output_root = Path(args.output_root)
    if output_root.exists() or output_root.is_symlink():
        raise SystemExit("STOP=TOKEN_BUDGET_CONTRACT_OUTPUT_ROOT_EXISTS")
    output_root.mkdir(parents=True)

    _write_jsonl(
        output_root / "calibration_length_ledger.jsonl",
        ledger_rows,
    )

    valid_index = {
        "schema_id": "FAILURE_MEMORY_TOKEN_BUDGET_VALID_RECORDS_V1",
        "schema_version": 1,
        "valid_record_count": len(valid),
        "failure_ids": [
            item["failure_id"]
            for item in valid
        ],
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
    }
    (
        output_root
        / "valid_calibration_records.json"
    ).write_bytes(
        canonical_json_bytes(valid_index)
    )

    (
        output_root
        / "failure_memory_token_budget_contract_v1.json"
    ).write_bytes(
        contract.canonical_bytes()
    )

    summary = {
        "schema_id": "FAILURE_MEMORY_TOKEN_BUDGET_CALIBRATION_SUMMARY_V1",
        "schema_version": 1,
        "failure_count": 30,
        "valid_record_count": len(valid),
        "fm1_min": min(fm1_counts),
        "fm1_max": max(fm1_counts),
        "fm2_min": min(fm2_counts),
        "fm2_max": max(fm2_counts),
        "library_pack_count": len(pack_counts),
        "single_record_hard_ceiling": single,
        "library_total_hard_ceiling": library,
        "coverage_target": COVERAGE_TARGET_V1,
        "contract_sha256": contract.contract_sha256,
        "performance_estimand": NO_PERFORMANCE_ESTIMAND,
        "memory_on_execution_used": False,
    }
    (
        output_root
        / "calibration_summary.json"
    ).write_bytes(
        canonical_json_bytes(summary)
    )

    print(
        "TOKEN_BUDGET_VALID_CALIBRATION_RECORD_COUNT="
        + str(len(valid))
    )
    print(
        "TOKEN_BUDGET_FM1_COUNTS="
        + json.dumps(
            list(fm1_counts),
            separators=(",", ":"),
        )
    )
    print(
        "TOKEN_BUDGET_FM2_COUNTS="
        + json.dumps(
            list(fm2_counts),
            separators=(",", ":"),
        )
    )
    print(
        "TOKEN_BUDGET_LIBRARY_PACK_COUNTS="
        + json.dumps(
            pack_counts,
            separators=(",", ":"),
        )
    )
    print(
        "TOKEN_BUDGET_SINGLE_RECORD_HARD_CEILING="
        + str(single)
    )
    print(
        "TOKEN_BUDGET_LIBRARY_TOTAL_HARD_CEILING="
        + str(library)
    )
    print(
        "TOKEN_BUDGET_CONTRACT_SHA256="
        + contract.contract_sha256
    )
    print("NO_PERFORMANCE_ESTIMAND")
    print("FAILURE_MEMORY_TOKEN_BUDGET_CONTRACT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
