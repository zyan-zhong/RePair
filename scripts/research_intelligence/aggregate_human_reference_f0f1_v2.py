#!/usr/bin/env python3
"""Offline Environment-Verifier aggregation for Human Reference F0/F1.

No model or environment execution occurs here. Each scheduled branch must
produce exactly one terminal branch record: either complete branch evidence or
an explicit failure/ambiguity record. Failed/ambiguous branches are not retried
by this program and make their pair UNCERTAIN. Five pairs are then aggregated
with the frozen four-of-five stability rule.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

from pchsi.evaluation.canonical_evidence import canonical_json_bytes, strict_json_loads
from pchsi.reference_loop.canonical import domain_hash
from pchsi.research_intelligence.human_f0f1_runtime import (
    aggregate_five_pair_effects_v1,
    build_pair_result_hash_v1,
    build_state_result_hash_v1,
    classify_pair_effect_v1,
    validate_continuation_record_v1,
)


def _write_once(path: Path, value: object) -> None:
    if path.exists() or path.is_symlink():
        raise FileExistsError(str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def _load_record(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict) or canonical_json_bytes(value) != raw:
        raise ValueError("branch record is not canonical: " + str(path))
    schema = value.get("schema_id")
    if schema == "CLEAN_REFERENCE_F0F1_BRANCH_EVIDENCE_V1":
        if value.get("scientific_outcome_produced") is not True: raise ValueError("branch evidence does not carry a scientific outcome")
        if value.get("automatic_retry_count") != 0: raise ValueError("branch evidence reports automatic retry")
        observed = domain_hash(
            schema,
            value,
            excluded_field="branch_evidence_sha256",
        )
        if value.get("branch_evidence_sha256") != observed:
            raise ValueError("branch evidence domain hash mismatch")
        value = dict(value)
        value["_record_kind"] = "EVIDENCE"
        value["_record_sha256"] = value["branch_evidence_sha256"]
        return value
    if schema == "CLEAN_REFERENCE_F0F1_BRANCH_FAILURE_V1":
        expected = hashlib.sha256(
            b"CLEAN_REFERENCE_F0F1_BRANCH_FAILURE_V1\0"
            + canonical_json_bytes(
                {k: v for k, v in value.items() if k != "branch_failure_sha256"}
            )
        ).hexdigest()
        if value.get("branch_failure_sha256") != expected:
            raise ValueError("branch failure domain hash mismatch")
        if value.get("scientific_outcome_produced") is not False:
            raise ValueError("failure record cannot claim scientific outcome")
        if value.get("automatic_retry_authorized") is not False:
            raise ValueError("failure record unexpectedly authorizes retry")
        value = dict(value)
        value["_record_kind"] = "FAILURE"
        value["_record_sha256"] = value["branch_failure_sha256"]
        return value
    raise ValueError("unexpected branch record schema: " + str(schema))


def _load_execution_manifest(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file(): raise ValueError("execution manifest path invalid")
    raw=path.read_bytes(); value=strict_json_loads(raw)
    if not isinstance(value,dict) or canonical_json_bytes(value)!=raw: raise ValueError("execution manifest is not canonical")
    if value.get("schema_id")!="CLEAN_REFERENCE_F0F1_EXECUTION_MANIFEST_V1": raise ValueError("execution manifest schema mismatch")
    observed=domain_hash("CLEAN_REFERENCE_F0F1_EXECUTION_MANIFEST_V1",value,excluded_field="execution_manifest_sha256")
    if value.get("execution_manifest_sha256")!=observed: raise ValueError("execution manifest domain hash mismatch")
    if value.get("seed_schedule") != [17,31,47,73,101]: raise ValueError("execution manifest seed_schedule changed")
    state_count=value.get("state_count")
    if type(state_count) is not int or state_count <= 0: raise ValueError("execution manifest state_count invalid")
    expected_pairs=state_count*5; expected_branches=expected_pairs*2
    if value.get("pair_count")!=expected_pairs or value.get("branch_count")!=expected_branches: raise ValueError("execution manifest population counts changed")
    branches=value.get("branches")
    if not isinstance(branches,list) or len(branches)!=expected_branches: raise ValueError("execution manifest branch population mismatch")
    keys=[(r.get("pair_id"),r.get("branch")) for r in branches if isinstance(r,dict)]
    if len(keys)!=expected_branches or len(set(keys))!=expected_branches: raise ValueError("execution manifest branch keys are not unique")
    return value

def _validate_record_against_manifest(record: dict[str, object], expected: dict[str, object]) -> None:
    for field in ("pair_id","state_position","repetition","branch","continuation_seed","source_state_sha256","research_candidate_id","source_candidate_sha256","registered_repair_action"):
        if record.get(field)!=expected.get(field): raise ValueError("execution manifest record mismatch at "+field)


def _pair(f0: dict[str, object], f1: dict[str, object]) -> dict[str, object]:
    same_fields = (
        "execution_manifest_sha256", "pair_id", "state_position", "repetition",
        "continuation_seed", "source_state_sha256", "research_candidate_id",
        "source_candidate_sha256", "registered_repair_action",
    )
    for field in same_fields:
        if f0.get(field) != f1.get(field):
            raise ValueError("F0/F1 pair binding mismatch at " + field)
    if f0.get("branch") != "F0" or f1.get("branch") != "F1":
        raise ValueError("pair branch identities invalid")

    f0_complete = f0.get("_record_kind") == "EVIDENCE" and f0.get("evidence_complete") is True
    f1_complete = f1.get("_record_kind") == "EVIDENCE" and f1.get("evidence_complete") is True
    if f0_complete and f0.get("intervention") is not None:
        raise ValueError("F0 unexpectedly contains registered repair intervention")
    if f1_complete:
        intervention = f1.get("intervention")
        if not isinstance(intervention, dict):
            raise ValueError("complete F1 is missing registered repair intervention")
        if intervention.get("role") != "REGISTERED_REPAIR_INTERVENTION":
            raise ValueError("F1 intervention role invalid")
        if intervention.get("action") != f1.get("registered_repair_action"):
            raise ValueError("F1 intervention action differs from frozen repair")

    classification = classify_pair_effect_v1(
        f0_success=f0.get("terminal_success") if f0_complete else None,
        f1_success=f1.get("terminal_success") if f1_complete else None,
        f0_complete=f0_complete,
        f1_complete=f1_complete,
    )
    result = {
        "schema_id": "CLEAN_REFERENCE_F0F1_PAIR_RESULT_V1",
        "schema_version": 1,
        "execution_manifest_sha256": f0["execution_manifest_sha256"],
        "pair_id": f0["pair_id"],
        "state_position": f0["state_position"],
        "repetition": f0["repetition"],
        "continuation_seed": f0["continuation_seed"],
        "source_state_sha256": f0["source_state_sha256"],
        "research_candidate_id": f0["research_candidate_id"],
        "source_candidate_sha256": f0["source_candidate_sha256"],
        "registered_repair_action": f0["registered_repair_action"],
        "f0_branch_record_kind": f0["_record_kind"],
        "f1_branch_record_kind": f1["_record_kind"],
        "f0_branch_record_sha256": f0["_record_sha256"],
        "f1_branch_record_sha256": f1["_record_sha256"],
        "f0_terminal_success": f0.get("terminal_success") if f0_complete else None,
        "f1_terminal_success": f1.get("terminal_success") if f1_complete else None,
        "effect": classification["effect"],
        "terminal_relation": classification["terminal_relation"],
        "pair_complete": bool(f0_complete and f1_complete),
        "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
        "pair_result_sha256": "0" * 64,
    }
    result["pair_result_sha256"] = build_pair_result_hash_v1(result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execution-root", required=True)
    parser.add_argument("--execution-manifest", required=True)
    parser.add_argument("--output-root", required=True)
    args = parser.parse_args()
    root = Path(args.execution_root)
    manifest=_load_execution_manifest(Path(args.execution_manifest))
    expected_manifest_sha=str(manifest["execution_manifest_sha256"])
    expected_by_key={(str(r["pair_id"]),str(r["branch"])):r for r in manifest["branches"]}
    out = Path(args.output_root)
    if out.exists() or out.is_symlink():
        raise SystemExit("STOP=HUMAN_F0F1_AGGREGATE_OUTPUT_EXISTS")
    out.mkdir(parents=True, mode=0o700)

    paths = sorted(root.rglob("CLEAN_REFERENCE_F0F1_BRANCH_EVIDENCE_V1.json"))
    paths += sorted(root.rglob("CLEAN_REFERENCE_F0F1_BRANCH_FAILURE_V1.json"))
    by_pair: dict[str, dict[str, dict[str, object]]] = {}
    for path in paths:
        value = _load_record(path)
        if value.get("execution_manifest_sha256") != expected_manifest_sha: raise SystemExit("STOP=BRANCH_RECORD_EXECUTION_MANIFEST_MISMATCH")
        pair_id = str(value["pair_id"])
        branch = str(value["branch"])
        expected=expected_by_key.get((pair_id,branch))
        if expected is None: raise SystemExit("STOP=UNSCHEDULED_BRANCH_RECORD:"+pair_id+":"+branch)
        _validate_record_against_manifest(value,expected)
        validate_continuation_record_v1(value, expected)
        bucket = by_pair.setdefault(pair_id, {})
        if branch in bucket:
            raise SystemExit("STOP=DUPLICATE_BRANCH_RECORD:" + pair_id + ":" + branch)
        bucket[branch] = value

    observed_keys={(pair_id,branch) for pair_id,bucket in by_pair.items() for branch in bucket}
    if observed_keys != set(expected_by_key): raise SystemExit("STOP=scheduled branch population mismatch")

    pair_results = []
    for pair_id in sorted(by_pair):
        bucket = by_pair[pair_id]
        if set(bucket) != {"F0", "F1"}:
            raise SystemExit("STOP=MISSING_SCHEDULED_BRANCH_RECORD:" + pair_id)
        result = _pair(bucket["F0"], bucket["F1"])
        pair_results.append(result)
        _write_once(out / "pairs" / (pair_id + ".json"), result)

    states: dict[str, list[dict[str, object]]] = {}
    for pair in pair_results:
        states.setdefault(str(pair["source_state_sha256"]), []).append(pair)

    state_results = []
    for state_id in sorted(states):
        pairs = sorted(states[state_id], key=lambda row: int(row["repetition"]))
        if [int(row["repetition"]) for row in pairs] != [1, 2, 3, 4, 5]:
            raise SystemExit("STOP=STATE_DOES_NOT_HAVE_EXACT_FIVE_REPETITIONS:" + state_id)
        if len({row["research_candidate_id"] for row in pairs}) != 1:
            raise SystemExit("STOP=OUTCOME_ADAPTIVE_CANDIDATE_REPLACEMENT_DETECTED:" + state_id)
        if len({row["source_candidate_sha256"] for row in pairs}) != 1:
            raise SystemExit("STOP=SOURCE_CANDIDATE_CHANGED_ACROSS_REPETITIONS:" + state_id)
        if len({row["registered_repair_action"] for row in pairs}) != 1:
            raise SystemExit("STOP=REPAIR_ACTION_CHANGED_ACROSS_REPETITIONS:" + state_id)
        aggregate = aggregate_five_pair_effects_v1([str(row["effect"]) for row in pairs])
        state = {
            "schema_id": "CLEAN_REFERENCE_F0F1_STATE_RESULT_V1",
            "schema_version": 1,
            "execution_manifest_sha256": pairs[0]["execution_manifest_sha256"],
            "source_state_sha256": state_id,
            "research_candidate_id": pairs[0]["research_candidate_id"],
            "source_candidate_sha256": pairs[0]["source_candidate_sha256"],
            "registered_repair_action": pairs[0]["registered_repair_action"],
            "pair_result_sha256s": [row["pair_result_sha256"] for row in pairs],
            "stable_effect": aggregate["stable_effect"],
            "effect_counts": aggregate["effect_counts"],
            "four_of_five_stable": aggregate["four_of_five_stable"],
            "paired_repetition_count": 5,
            "incomplete_pair_count": sum(row["pair_complete"] is not True for row in pairs),
            "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
            "state_result_sha256": "0" * 64,
        }
        state["state_result_sha256"] = build_state_result_hash_v1(state)
        state_results.append(state)
        _write_once(out / "states" / (state_id + ".json"), state)

    expected_states=int(manifest["state_count"]); expected_pairs=int(manifest["pair_count"]); expected_branches=int(manifest["branch_count"])
    if len(state_results) != expected_states or len(pair_results) != expected_pairs or len(paths) != expected_branches:
        raise SystemExit(
            "STOP=CLEAN_REFERENCE_F0F1_POPULATION_MISMATCH:"
            f"branches={len(paths)} pairs={len(pair_results)} states={len(state_results)}"
        )

    summary = {
        "schema_id": "CLEAN_REFERENCE_F0F1_RESULT_PACKAGE_V1",
        "schema_version": 1,
        "execution_manifest_sha256": expected_manifest_sha,
        "branch_record_count": int(manifest["branch_count"]),
        "pair_count": int(manifest["pair_count"]),
        "state_count": int(manifest["state_count"]),
        "stable_effect_counts": {
            label: sum(row["stable_effect"] == label for row in state_results)
            for label in ("BENEFIT", "HARM", "NEUTRAL", "UNCERTAIN")
        },
        "incomplete_pair_count": sum(row["pair_complete"] is not True for row in pair_results),
        "state_result_sha256s": [row["state_result_sha256"] for row in state_results],
        "environment_verifier_authority": True,
        "automatic_retry_count": 0,
        "training_execution_count": 0,
        "result_package_sha256": "0" * 64,
    }
    summary["result_package_sha256"] = domain_hash(
        "CLEAN_REFERENCE_F0F1_RESULT_PACKAGE_V1",
        summary,
        excluded_field="result_package_sha256",
    )
    _write_once(out / "CLEAN_REFERENCE_F0F1_RESULT_PACKAGE_V1.json", summary)
    print("CLEAN_REFERENCE_F0F1_RESULT_PACKAGE_PASS")
    print("RESULT_PACKAGE_SHA256=" + str(summary["result_package_sha256"]))
    print("BRANCH_RECORD_COUNT=" + str(summary["branch_record_count"]))
    print("PAIR_COUNT=" + str(summary["pair_count"]))
    print("STATE_COUNT=" + str(summary["state_count"]))
    print("INCOMPLETE_PAIR_COUNT=" + str(summary["incomplete_pair_count"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
