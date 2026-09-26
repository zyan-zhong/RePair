#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Any, Mapping

from dynamic_primary_pre_v2 import (
    build_dynamic_pre_contract_v2,
    finalize_dynamic_primary_pre_v2,
)
from dynamic_pre_v2_semantic_normalization import try_semantic_normalization
from infra_recovery_disposition import classify_infrastructure_recovery
from current_round_researcher_memory_v1 import (
    build_current_round_evidence,
    resolve_stable_memory_authority,
)

PACKAGE_ROOT = Path(__file__).resolve().parent
PROMPT_PATH = PACKAGE_ROOT / "assets/prompts/RESEARCHER_PRE_PRIMARY_V2.txt"
SCHEMA_PATH = PACKAGE_ROOT / "assets/schemas/strong_researcher_pre_primary_v2.json"
RECOVERY_POLICY_PATH = PACKAGE_ROOT / "assets/configs/v1232w_autonomous_infrastructure_recovery_policy_v1.json"


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def load_json(path: Path) -> dict[str, Any]:
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("REQUIRED_REGULAR_JSON_MISSING:" + str(path))
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("JSON_OBJECT_REQUIRED:" + str(path))
    return value


def sha256_file_local(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha64(value: object, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise RuntimeError(label + "_INVALID_SHA256")
    return value


def write_or_verify_json(path: Path, value: Mapping[str, object]) -> None:
    raw = canonical_bytes(dict(value))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or path.is_symlink():
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise RuntimeError("EXISTING_ARTIFACT_IDENTITY_MISMATCH:" + str(path))
        return
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        view = memoryview(raw)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError("write made no progress")
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)


def find_badcase_root(path: Path) -> Path:
    for p in [path, *path.parents]:
        if p.name == "badcase":
            return p
    raise RuntimeError("BADCASE_ROOT_NOT_DERIVABLE")


def git_object_id(value: object, object_format: str, label: str) -> str:
    fmt = str(object_format).strip().lower()
    try:
        expected = hashlib.new(fmt).digest_size * 2
    except Exception as exc:
        raise RuntimeError(label + "_OBJECT_FORMAT_UNSUPPORTED:" + fmt) from exc
    if not isinstance(value, str) or len(value) != expected or any(c not in "0123456789abcdef" for c in value):
        raise RuntimeError(label + "_INVALID_GIT_OBJECT_ID")
    return value


def tracked_repo_identity(repo: Path) -> dict[str, str]:
    fmt = subprocess.run(["git", "-C", str(repo), "rev-parse", "--show-object-format=storage"], capture_output=True, text=True)
    if fmt.returncode != 0:
        raise RuntimeError("REPO_OBJECT_FORMAT_READ_FAILED:" + fmt.stderr.strip())
    object_format = fmt.stdout.strip().lower()
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "--verify", "HEAD^{commit}"], capture_output=True, text=True)
    if head.returncode != 0:
        raise RuntimeError("REPO_HEAD_COMMIT_READ_FAILED:" + head.stderr.strip())
    head_oid = git_object_id(head.stdout.strip(), object_format, "REPO_HEAD")
    typ = subprocess.run(["git", "-C", str(repo), "cat-file", "-t", head_oid], capture_output=True, text=True)
    if typ.returncode != 0 or typ.stdout.strip() != "commit":
        raise RuntimeError("REPO_HEAD_OBJECT_TYPE_INVALID")
    status = subprocess.run(["git", "-C", str(repo), "status", "--porcelain=v1", "-z", "--untracked-files=no"], capture_output=True)
    if status.returncode != 0:
        raise RuntimeError("REPO_STATUS_READ_FAILED")
    if status.stdout:
        raise RuntimeError("REPO_TRACKED_WORKTREE_NOT_CLEAN")
    return {"head_oid": head_oid, "object_format": object_format}


def discover_strong_repo(root: Path) -> tuple[Path, dict[str, Any]]:
    github = find_badcase_root(root) / "github_exports"
    rel = Path("docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json")
    found: list[tuple[Path, dict[str, Any]]] = []
    if not github.is_dir() or github.is_symlink():
        raise RuntimeError("GITHUB_EXPORT_ROOT_INVALID")
    for child in sorted(github.iterdir()):
        if not child.is_dir() or child.is_symlink():
            continue
        auth_path = child / rel
        if not auth_path.is_file() or auth_path.is_symlink():
            continue
        try:
            auth = load_json(auth_path)
        except Exception:
            continue
        if auth.get("schema_id") != "ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1":
            continue
        if auth.get("strong_primary_fresh_round_execution_authorized") is not True:
            continue
        roles = set(auth.get("strong_primary_roles") or [])
        if not {"ANALYZER", "RESEARCH_PLANNER_PRE", "RESEARCH_PLANNER_POST"} <= roles:
            continue
        required = [
            child / "src/pchsi/cognitive_runtime/orchestrator.py",
            child / "src/pchsi/cognitive_runtime/request_renderer.py",
            child / "src/pchsi/cognitive_runtime/identity.py",
            child / "src/pchsi/memory/consumer_views.py",
            child / "configs/research_intelligence/planner_bound_f0f1_replication_protocol_v2.json",
        ]
        if all(p.is_file() and not p.is_symlink() for p in required):
            found.append((child.resolve(), auth))
    if len(found) != 1:
        raise RuntimeError("STRONG_REPO_DISCOVERY_NOT_UNIQUE:" + repr([str(x[0]) for x in found]))
    return found[0]


def import_repo(repo: Path) -> None:
    sys.path.insert(0, str(repo / "src"))


def discover_r1_root(u_root: Path, terminal_sha: str) -> Path:
    base = find_badcase_root(u_root) / "new_human_pi1/control/v1232r_wave1_complete_pair_adoption_and_canonical_act3_group_prep"
    found = []
    if base.is_dir() and not base.is_symlink():
        for child in sorted(base.iterdir()):
            p = child / "PCHSI_V1232R1_TERMINAL_V1.json"
            if child.is_dir() and not child.is_symlink() and p.is_file() and not p.is_symlink():
                try:
                    obj = load_json(p)
                except Exception:
                    continue
                if obj.get("terminal_sha256") == terminal_sha:
                    found.append(child.resolve())
    if len(found) != 1:
        raise RuntimeError("R1_ROOT_DISCOVERY_NOT_UNIQUE:" + repr([str(x) for x in found]))
    return found[0]


def discover_q_root(root: Path, wave_sha: str) -> Path:
    base = find_badcase_root(root) / "new_human_pi1/control/v1232q_strong_analyzer_wave1_and_canonical_act3_reuse"
    found = []
    if base.is_dir() and not base.is_symlink():
        for child in sorted(base.iterdir()):
            p = child / "V1232Q_STRONG_LOCAL_WAVE_TERMINAL_V1.json"
            if child.is_dir() and not child.is_symlink() and p.is_file() and not p.is_symlink():
                try:
                    obj = load_json(p)
                except Exception:
                    continue
                if obj.get("wave_sha256") == wave_sha:
                    found.append(child.resolve())
    if len(found) != 1:
        raise RuntimeError("Q_ROOT_DISCOVERY_NOT_UNIQUE:" + repr([str(x) for x in found]))
    return found[0]


def researcher_memory_candidates(badcase: Path, snapshot_sha: str) -> list[dict[str, Any]]:
    roots = [badcase / "new_human_pi1/control", badcase / "pchsi_scripts"]
    by_view: dict[str, dict[str, Any]] = {}
    for root in roots:
        if not root.is_dir() or root.is_symlink():
            continue
        paths = set(root.rglob("*RESEARCHER*MEMORY*VIEW*.json")) | set(root.rglob("*RESEARCHER*VIEW*MEMORY*.json"))
        for path in sorted(paths):
            if path.is_symlink() or not path.is_file():
                continue
            try:
                obj = load_json(path)
            except Exception:
                continue
            if obj.get("schema_id") != "RESEARCHER_MEMORY_VIEW_V1":
                continue
            if obj.get("snapshot_sha256") != snapshot_sha:
                continue
            if obj.get("purpose") != "ROUND_RESEARCH_PLANNING":
                continue
            view_sha = obj.get("view_sha256")
            if not isinstance(view_sha, str) or len(view_sha) != 64:
                continue
            if view_sha in by_view and by_view[view_sha] != obj:
                raise RuntimeError("RESEARCHER_MEMORY_VIEW_SHA_COLLISION")
            by_view[view_sha] = obj
    return [by_view[k] for k in sorted(by_view)]


def partition_predecessor_memory_candidates(
    views: list[dict[str, Any]],
    *,
    current_round_evidence: Mapping[str, object],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Exclude same-round derived Researcher views from predecessor authority discovery.

    A resume may see the Researcher view materialized by the earlier invocation.
    That view is downstream of the current Analyzer evidence and must not become
    an additional predecessor-memory candidate on resume.  The partition is
    semantic (exact current-round evidence binding), not path/name/count based.
    """
    predecessor: list[dict[str, Any]] = []
    current_round_derived: list[dict[str, Any]] = []
    expected = dict(current_round_evidence)
    for raw in views:
        row = dict(raw)
        bound = row.get("round_evidence")
        if isinstance(bound, dict) and bound == expected:
            current_round_derived.append(row)
        else:
            predecessor.append(row)
    return predecessor, current_round_derived


def translate_pair_universe(u_pair: Mapping[str, Any], domain_hash: Any) -> dict[str, Any]:
    rows = u_pair.get("pair_table")
    if not isinstance(rows, list) or not rows:
        raise RuntimeError("U_PAIR_TABLE_INVALID")
    translated = []
    states = set()
    for expected_index, raw in enumerate(rows):
        if not isinstance(raw, dict):
            raise RuntimeError("U_PAIR_ROW_NOT_OBJECT")
        if raw.get("state_index") != expected_index:
            raise RuntimeError("U_PAIR_STATE_INDEX_DRIFT")
        state = sha64(raw.get("source_state_sha256"), "U_PAIR_SOURCE_STATE")
        if state in states:
            raise RuntimeError("U_PAIR_DUPLICATE_SOURCE_STATE")
        states.add(state)
        context = raw.get("source_context")
        if not isinstance(context, dict) or context.get("source_state_sha256") != state:
            raise RuntimeError("U_PAIR_SOURCE_CONTEXT_BINDING_DRIFT")
        out: dict[str, Any] = {
            "pair_status": "COMPLETE_A2_A3",
            "state_index": expected_index,
            "source_state_sha256": state,
            "task_family": raw.get("task_family"),
            "source_context": context,
            "source_context_audit": raw.get("source_context_audit"),
        }
        for condition in ("A2", "A3"):
            wrapper = raw.get(condition)
            if not isinstance(wrapper, dict):
                raise RuntimeError("U_PAIR_CONDITION_WRAPPER_MISSING:" + condition)
            candidate = wrapper.get("candidate")
            if not isinstance(candidate, dict):
                raise RuntimeError("U_PAIR_CANDIDATE_BYTES_MISSING:" + condition)
            csha = sha64(wrapper.get("candidate_sha256"), "U_PAIR_CANDIDATE")
            if candidate.get("candidate_sha256") != csha or candidate.get("source_state_sha256") != state:
                raise RuntimeError("U_PAIR_CANDIDATE_BINDING_DRIFT:" + condition)
            out[condition] = {
                "candidate_sha256": csha,
                "source_state_sha256": state,
                "selected_execution_identity_sha256": sha64(wrapper.get("selected_execution_identity_sha256"), "U_PAIR_EXECUTION_IDENTITY"),
                "candidate": candidate,
                "candidate_provenance": wrapper.get("candidate_provenance"),
                "group_result_sha256s": list(wrapper.get("group_result_sha256s") or []),
                "formal_x_dispositions": list(wrapper.get("formal_x_dispositions") or []),
            }
        translated.append(out)
    view = {
        "schema_id": "V1232V_DYNAMIC_PRE_PAIR_UNIVERSE_VIEW_V1",
        "schema_version": 1,
        "source_v1232u_pair_universe_sha256": sha64(u_pair.get("pair_universe_sha256"), "U_PAIR_UNIVERSE"),
        "pair_count": len(translated),
        "pair_table": translated,
        "representation_repair_only": True,
        "scientific_selection_changed": False,
        "legacy_fixed_cardinality_assumed": False,
        "view_sha256": "0" * 64,
    }
    view["view_sha256"] = domain_hash("V1232V_DYNAMIC_PRE_PAIR_UNIVERSE_VIEW_V1", view, excluded_field="view_sha256")
    return view


def make_stage_row(prompt_sha: str, schema_sha: str) -> dict[str, Any]:
    return {
        "condition_id": None,
        "logical_call_budget_per_unit": 1,
        "max_output_tokens": 24576,
        "memory_exposure": True,
        "output_schema_id": "STRONG_RESEARCHER_PRE_PRIMARY_V2",
        "output_schema_relative_path": str(SCHEMA_PATH),
        "output_schema_sha256": schema_sha,
        "previous_response_id_policy": "ABSENT",
        "prompt_relative_path": str(PROMPT_PATH),
        "prompt_sha256": prompt_sha,
        "prompt_template_id": "RESEARCHER_PRE_PRIMARY_V2",
        "required_projection_identity_fields": [
            "round_id", "blind_input_sha256", "dynamic_contract_sha256",
            "dynamic_pair_universe_sha256", "researcher_memory_view_sha256",
            "dynamic_contract", "blind_input",
        ],
        "role": "TRAINING_RESEARCHER",
        "scientific_unit_type": "ROUND",
        "shared_conversation_state": False,
        "stage_id": "R-PRE-PRIMARY-V2",
        "tools": [],
    }


def build_overlay_manifest(base: Mapping[str, Any], prompt_sha: str, schema_sha: str, domain_hash: Any) -> dict[str, Any]:
    rows = [dict(x) for x in base.get("stage_rows", [])]
    if any(x.get("stage_id") == "R-PRE-PRIMARY-V2" for x in rows):
        raise RuntimeError("PRE_V2_ALREADY_REGISTERED_IN_FIXED_RUNTIME")
    rows.append(make_stage_row(prompt_sha, schema_sha))
    out = dict(base)
    out["stage_rows"] = rows
    out["runtime_manifest_sha256"] = "0" * 64
    out["runtime_manifest_sha256"] = domain_hash("UNIFIED_COGNITIVE_RUNTIME_MANIFEST_V1", out, excluded_field="runtime_manifest_sha256")
    return out


def expected_logical_call_id(*, unit_identity: Mapping[str, Any], round_id: str, policy_version: str, request_body_sha256: str, domain_hash: Any) -> str:
    return domain_hash("COGNITIVE_LOGICAL_CALL_ID_V1", {
        "scientific_unit_identity_sha256": unit_identity["identity_sha256"],
        "stage_id": "R-PRE-PRIMARY-V2",
        "condition_id": None,
        "round_id": round_id,
        "policy_version": policy_version,
        "request_body_sha256": request_body_sha256,
    })


def freeze_f0f1_handoff(*, artifact: Mapping[str, Any], pair_view: Mapping[str, Any], protocol: Mapping[str, Any], u_pair_sha: str, pre_artifact_sha: str, domain_hash: Any) -> dict[str, Any]:
    selected_reviews = [x for x in artifact.get("state_reviews", []) if isinstance(x, dict) and x.get("selected_for_verification") is True]
    pair_rows = pair_view["pair_table"]
    seeds = list(protocol.get("paired_seeds") or [])
    reps = protocol.get("paired_repetitions_per_state")
    arms = protocol.get("branch_arms_per_repetition")
    if type(reps) is not int or type(arms) is not int or arms != 2 or len(seeds) != reps or len(set(seeds)) != len(seeds):
        raise RuntimeError("F0F1_REPLICATION_PROTOCOL_SEED_BINDING_INVALID")
    selected_states = []
    branches = []
    seen_states = set()
    for review in selected_reviews:
        idx = review.get("state_index")
        if type(idx) is not int or not 0 <= idx < len(pair_rows):
            raise RuntimeError("PRE_SELECTED_STATE_INDEX_INVALID")
        pair = pair_rows[idx]
        state = pair["source_state_sha256"]
        if review.get("source_state_sha256") != state or state in seen_states:
            raise RuntimeError("PRE_SELECTED_STATE_BINDING_INVALID")
        seen_states.add(state)
        cond = review.get("preferred_condition")
        if cond not in {"A2", "A3"}:
            raise RuntimeError("PRE_SELECTED_CONDITION_INVALID")
        candidate = pair[cond]
        if review.get("preferred_candidate_sha256") != candidate["candidate_sha256"]:
            raise RuntimeError("PRE_SELECTED_CANDIDATE_BINDING_INVALID")
        selected_states.append({
            "state_index": idx,
            "source_state_sha256": state,
            "preferred_condition": cond,
            "preferred_candidate_sha256": candidate["candidate_sha256"],
            "preferred_execution_identity_sha256": candidate["selected_execution_identity_sha256"],
            "source_context": pair["source_context"],
            "candidate": candidate["candidate"],
            "candidate_provenance": candidate.get("candidate_provenance"),
            "exact_state_replay_rebind_required": True,
            "source_context_is_analyzer_projection_not_replay_authority": True,
        })
        for rep_index, seed in enumerate(seeds):
            for arm in ("F0", "F1"):
                row = {
                    "state_index": idx,
                    "source_state_sha256": state,
                    "replicate_index": rep_index,
                    "paired_seed": seed,
                    "arm": arm,
                    "preferred_condition": cond,
                    "f1_candidate_sha256": candidate["candidate_sha256"] if arm == "F1" else None,
                    "f1_execution_identity_sha256": candidate["selected_execution_identity_sha256"] if arm == "F1" else None,
                    "branch_key_sha256": "0" * 64,
                }
                row["branch_key_sha256"] = domain_hash("V1232V_PLANNER_BOUND_F0F1_BRANCH_KEY_V1", row, excluded_field="branch_key_sha256")
                branches.append(row)
    budget = artifact.get("verification_plan", {}).get("selected_branch_run_budget")
    if budget != len(branches):
        raise RuntimeError("PRE_SELECTED_BRANCH_BUDGET_HANDOFF_MISMATCH")
    handoff = {
        "schema_id": "V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1",
        "schema_version": 1,
        "source_v1232u_pair_universe_sha256": u_pair_sha,
        "source_dynamic_pre_pair_view_sha256": pair_view["view_sha256"],
        "source_pre_primary_record_sha256": pre_artifact_sha,
        "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
        "state_budget_authority": "RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE",
        "paired_repetitions_per_state": reps,
        "branch_arms_per_repetition": arms,
        "paired_seeds": seeds,
        "stable_direction_min_pairs": protocol.get("stable_direction_min_pairs"),
        "outcome_adaptive_reselection_allowed": False,
        "outcome_adaptive_budget_change_allowed": False,
        "selected_state_count": len(selected_states),
        "selected_branch_run_budget": len(branches),
        "selected_states": selected_states,
        "branch_plan": branches,
        "current_train_exact_state_replay_rebind_required": True,
        "native_f0f1_environment_execution_performed": False,
        "environment_call_count": 0,
        "training_execution_count": 0,
        "human_scientific_decision_count": 0,
        "automatic_retry_count": 0,
        "legacy_fixed_state_cardinality_assumed": False,
        "handoff_sha256": "0" * 64,
    }
    handoff["handoff_sha256"] = domain_hash("V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1", handoff, excluded_field="handoff_sha256")
    return handoff


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--v1232u-output-root", required=True)
    ap.add_argument("--authorize-bounded-infrastructure-recovery", action="store_true")
    args = ap.parse_args()
    u_root = Path(args.v1232u_output_root).resolve()
    if u_root.is_symlink() or not u_root.is_dir():
        raise RuntimeError("V1232U_OUTPUT_ROOT_INVALID")

    u_term = load_json(u_root / "PCHSI_V1232U_TERMINAL_V1.json")
    u_tail = load_json(u_root / "V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1.json")
    u_pair = load_json(u_root / "V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json")
    if u_term.get("status") != "STRONG_ANALYZER_TAIL_CLOSED_DYNAMIC_PLANNER_PAIR_UNIVERSE_READY":
        raise RuntimeError("V1232U_NOT_SUCCESS_TERMINAL")
    if u_term.get("dynamic_pair_universe_sha256") != u_pair.get("pair_universe_sha256"):
        raise RuntimeError("V1232U_PAIR_UNIVERSE_BINDING_MISMATCH")
    if u_term.get("analyzer_tail_terminal_sha256") != u_tail.get("terminal_sha256"):
        raise RuntimeError("V1232U_ANALYZER_TAIL_BINDING_MISMATCH")
    if u_pair.get("complete_pair_count") != len(u_pair.get("pair_table") or []) or u_pair.get("complete_pair_count") != u_term.get("dynamic_planner_pair_count"):
        raise RuntimeError("V1232U_PAIR_COUNT_DRIFT")
    if not isinstance(u_pair.get("complete_pair_count"), int) or u_pair["complete_pair_count"] <= 0:
        raise RuntimeError("V1232U_DYNAMIC_PAIR_UNIVERSE_EMPTY")
    if u_pair.get("legacy_fixed_cardinality_assumed") is not False or u_pair.get("dynamic_pre_v2_required") is not True:
        raise RuntimeError("V1232U_DYNAMIC_PRE_AUTHORITY_DRIFT")

    repo, role_auth = discover_strong_repo(u_root)
    repo_identity = tracked_repo_identity(repo)
    import_repo(repo)
    from pchsi.reference_loop.canonical import domain_hash, sha256_file, strict_json_loads
    from pchsi.cognitive_runtime import orchestrator as orch
    from pchsi.cognitive_runtime import request_renderer as rr
    from pchsi.cognitive_runtime import manifest as runtime_manifest_module
    from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
    from pchsi.memory.consumer_views import ResearcherMemoryViewV1, ResearcherPurposeV1
    from pchsi.cognitive_runtime.output_validation import validated_artifact_identity as original_artifact_identity
    import jsonschema

    # Fixed-runtime import/signature preflight before output-root creation or provider calls.
    required_signatures = {
        "execute_one": (orch.execute_one, {"output_root", "unit_identity", "stage_id", "condition_id", "round_id", "policy_version", "projection", "task_access"}),
        "render_stage_request": (rr.render_stage_request, {"stage_id", "projection"}),
    }
    for api_name, (fn, required_params) in required_signatures.items():
        if not required_params <= set(inspect.signature(fn).parameters):
            raise RuntimeError("FIXED_RUNTIME_CALLABLE_SIGNATURE_DRIFT:" + api_name)

    # Resolve current round-start Memory through U -> R1 -> Q -> rollout handoff.
    r1_sha = sha64(u_term.get("source_r1_terminal_sha256"), "SOURCE_R1_TERMINAL")
    r1_root = discover_r1_root(u_root, r1_sha)
    r1_term = load_json(r1_root / "PCHSI_V1232R1_TERMINAL_V1.json")
    if r1_term.get("terminal_sha256") != r1_sha:
        raise RuntimeError("R1_TERMINAL_IDENTITY_MISMATCH")
    q_sha = sha64(r1_term.get("source_q_wave_sha256"), "SOURCE_Q_WAVE")
    q_root = discover_q_root(u_root, q_sha)
    q_handoff = load_json(q_root / "V1232Q_SOURCE_ROLLOUT_HANDOFF_COPY.json")
    rollout_request_path = Path(str(q_handoff.get("rollout_request_path")))
    if rollout_request_path.is_symlink() or not rollout_request_path.is_file() or sha256_file(rollout_request_path) != q_handoff.get("rollout_request_sha256"):
        raise RuntimeError("ROLLOUT_REQUEST_AUTHORITY_INVALID")
    rollout_request = load_json(rollout_request_path)
    round_start_snapshot_sha = sha64(rollout_request.get("round_start_memory_snapshot_sha256"), "ROUND_START_MEMORY_SNAPSHOT")

    # Representation-only translation of U pair rows to the already-frozen Dynamic PRE V2 row contract.
    pair_view = translate_pair_universe(u_pair, domain_hash)
    pair_rows = pair_view["pair_table"]

    protocol_path = repo / "configs/research_intelligence/planner_bound_f0f1_replication_protocol_v2.json"
    protocol = load_json(protocol_path)
    expected_protocol = {
        "schema_id": "PLANNER_BOUND_F0F1_REPLICATION_PROTOCOL_V2",
        "state_budget_authority": "RESEARCH_PLANNER_PRE_SELECTED_UNIVERSE",
        "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
        "legacy_select12_authority_for_current_round": False,
        "outcome_adaptive_budget_change_allowed": False,
        "outcome_adaptive_reselection_allowed": False,
        "branch_arms_per_repetition": 2,
    }
    for k, v in expected_protocol.items():
        if protocol.get(k) != v:
            raise RuntimeError("F0F1_PROTOCOL_AUTHORITY_DRIFT:" + k)
    dynamic_contract = build_dynamic_pre_contract_v2(
        pair_rows=pair_rows,
        f0f1_protocol=protocol,
        dynamic_pair_universe_sha256=sha64(u_pair.get("pair_universe_sha256"), "U_PAIR_UNIVERSE"),
    )

    # Stable predecessor Researcher Memory authority: no latest/first/manual selection.
    # Build current-round evidence first so a resume can semantically exclude the
    # current stage's own previously materialized Researcher view from predecessor
    # discovery. This prevents resume self-inclusion from changing audit-only
    # candidate counts while leaving the stable Memory payload unchanged.
    badcase = find_badcase_root(u_root)
    current_round_evidence = build_current_round_evidence(
        round_id=str(u_term["round_id"]),
        parent_policy_id=str(u_term["parent_policy_id"]),
        analyzer_terminal_sha256=sha64(u_tail.get("terminal_sha256"), "ANALYZER_TAIL_TERMINAL"),
        dynamic_pair_universe_sha256=sha64(u_pair.get("pair_universe_sha256"), "U_PAIR_UNIVERSE"),
        dynamic_pair_count=len(pair_rows),
        round_start_memory_snapshot_sha256=round_start_snapshot_sha,
    )
    all_memory_candidates = researcher_memory_candidates(badcase, round_start_snapshot_sha)
    memory_candidates, current_round_derived_memory_views = partition_predecessor_memory_candidates(
        all_memory_candidates,
        current_round_evidence=current_round_evidence,
    )
    stable = resolve_stable_memory_authority(memory_candidates, snapshot_sha256=round_start_snapshot_sha)
    current_memory = ResearcherMemoryViewV1(
        snapshot_sha256=round_start_snapshot_sha,
        purpose=ResearcherPurposeV1.ROUND_RESEARCH_PLANNING,
        train_side_records=tuple(stable["train_side_records"]),
        round_evidence=current_round_evidence,
        heldout_aggregate_metrics={},
    ).to_dict()

    blind_input: dict[str, Any] = {
        "schema_id": "STRONG_RESEARCHER_BLIND_PRE_INPUT_V3",
        "schema_version": 3,
        "round_id": str(u_term["round_id"]),
        "parent_policy_id": str(u_term["parent_policy_id"]),
        "pre_outcome_only": True,
        "human_pre_visible": False,
        "human_selection_visible": False,
        "human_rationale_visible": False,
        "sealed_benchmark_per_task_results_visible": False,
        "current_or_future_f0f1_outcomes_visible": False,
        "analyzer_terminal_sha256": u_tail["terminal_sha256"],
        "registered_candidate_universe": pair_view,
        "dynamic_contract": dynamic_contract,
        "researcher_memory_view": current_memory,
        "f0f1_replication_protocol": protocol,
        "blind_input_sha256": "0" * 64,
    }
    blind_input["blind_input_sha256"] = domain_hash("STRONG_RESEARCHER_BLIND_PRE_INPUT_V3", blind_input, excluded_field="blind_input_sha256")

    projection = {
        "round_id": str(u_term["round_id"]),
        "blind_input_sha256": blind_input["blind_input_sha256"],
        "dynamic_contract_sha256": dynamic_contract["contract_sha256"],
        "dynamic_pair_universe_sha256": u_pair["pair_universe_sha256"],
        "researcher_memory_view_sha256": current_memory["view_sha256"],
        "dynamic_contract": dynamic_contract,
        "blind_input": blind_input,
    }

    prompt_sha = sha256_file(PROMPT_PATH)
    schema_sha = sha256_file(SCHEMA_PATH)
    base_manifest = runtime_manifest_module.load_runtime_manifest()
    overlay_manifest = build_overlay_manifest(base_manifest, prompt_sha, schema_sha, domain_hash)
    schema_obj = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema_obj)
    schema_validator = jsonschema.Draft202012Validator(schema_obj)

    # Process-local runtime overlay only; scientific fixed checkout is not mutated.
    rr.load_runtime_manifest = lambda path=None: overlay_manifest
    orch.load_runtime_manifest = lambda path=None: overlay_manifest
    normalization_state: dict[str, Any] = {"used": False, "receipt": None}

    def validate_pre(stage_id: str, text: str, raw_response_sha256: str, projection: Mapping[str, object]) -> dict[str, object]:
        if stage_id != "R-PRE-PRIMARY-V2":
            raise RuntimeError("V1232V_UNEXPECTED_RUNTIME_STAGE:" + stage_id)
        value = strict_json_loads(text)
        if not isinstance(value, dict):
            raise ValueError("PRE V2 provider output must be one JSON object")
        errors = sorted(schema_validator.iter_errors(value), key=lambda e: list(e.path))
        if errors:
            raise ValueError("PRE_V2_SCHEMA_INVALID:" + errors[0].message)

        def scientific_validator(candidate: Mapping[str, object]) -> dict[str, object]:
            return finalize_dynamic_primary_pre_v2(
                value=candidate,
                pair_rows=pair_rows,
                contract=dynamic_contract,
                blind_input_sha256=str(blind_input["blind_input_sha256"]),
                round_id=str(u_term["round_id"]),
            )
        try:
            return scientific_validator(value)
        except Exception as original:
            normalized = try_semantic_normalization(
                original_output=value,
                contract=dynamic_contract,
                original_validation_error=str(original),
                validator=scientific_validator,
            )
            if normalized.get("status") == "ACCEPTED_AFTER_DETERMINISTIC_NORMALIZATION":
                normalization_state["used"] = True
                normalization_state["receipt"] = {
                    "schema_id": "V1232V_DYNAMIC_PRE_V2_SEMANTIC_NORMALIZATION_RECEIPT_V1",
                    "schema_version": 1,
                    "original_raw_response_sha256": raw_response_sha256,
                    "normalization_class": normalized.get("normalization_class"),
                    "changed_paths": normalized.get("changed_paths"),
                    "provider_call_count": 0,
                    "scientific_choices_changed": False,
                }
                return normalized["validated_artifact"]
            raise original

    def artifact_identity(stage_id: str, artifact: Mapping[str, object]) -> str:
        if stage_id == "R-PRE-PRIMARY-V2":
            return sha64(artifact.get("primary_record_sha256"), "PRE_PRIMARY_RECORD")
        return original_artifact_identity(stage_id=stage_id, artifact=artifact)

    orch.validate_stage_output = validate_pre
    orch.validated_artifact_identity = artifact_identity

    unit_id = domain_hash("V1232V_PRE_SCIENTIFIC_UNIT_ID_V1", {
        "round_id": u_term["round_id"],
        "dynamic_pair_universe_sha256": u_pair["pair_universe_sha256"],
        "blind_input_sha256": blind_input["blind_input_sha256"],
        "researcher_memory_view_sha256": current_memory["view_sha256"],
    })
    unit_identity = build_scientific_unit_identity(
        scientific_unit_type="ROUND",
        scientific_unit_id=unit_id,
        source_unit_manifest_sha256=blind_input["blind_input_sha256"],
        task_set_manifest_sha256=u_pair["pair_universe_sha256"],
        task_id=None,
        gamefile_sha256=None,
        group_manifest_sha256=None,
        round_evidence_package_sha256=u_tail["terminal_sha256"],
    )
    task_access = {
        "schema_id": "V1232V_RESEARCH_PLANNER_PRE_TASK_ACCESS_V1",
        "schema_version": 1,
        "task_id": str(u_term["round_id"]),
        "gamefile_sha256": u_pair["pair_universe_sha256"],
        "access_class": "TRAIN_UPDATE_RESEARCH_PLANNER_VISIBLE",
        "dataset_split": "train",
        "teacher_call_permitted": True,
        "training_permitted": False,
        "select_evaluation_permitted": False,
        "confirmatory_permitted": False,
        "benchmark_result_values_visible": False,
        "policy_action_authority": False,
    }

    role_path = repo / "docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json"
    activation = domain_hash("V1232V_DYNAMIC_PRE_ACTIVATION_V1", {
        "v1232u_terminal_sha256": u_term["terminal_sha256"],
        "v1232u_pair_universe_sha256": u_pair["pair_universe_sha256"],
        "pair_view_sha256": pair_view["view_sha256"],
        "dynamic_contract_sha256": dynamic_contract["contract_sha256"],
        "researcher_memory_view_sha256": current_memory["view_sha256"],
        "blind_input_sha256": blind_input["blind_input_sha256"],
        "fixed_repo_head_oid": repo_identity["head_oid"],
        "fixed_repo_object_format": repo_identity["object_format"],
        "role_authority_file_sha256": sha256_file(role_path),
        "prompt_sha256": prompt_sha,
        "schema_sha256": schema_sha,
    })
    out = badcase / "new_human_pi1/control/v1232v_dynamic_strong_planner_pre_v2_and_f0f1_handoff" / activation
    if out.is_symlink():
        raise RuntimeError("V1232V_OUTPUT_ROOT_SYMLINK_FORBIDDEN")
    out.mkdir(parents=True, exist_ok=True)
    runtime_root = out / "strong_pre_runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)

    write_or_verify_json(out / "V1232V_DYNAMIC_PRE_PAIR_UNIVERSE_VIEW_V1.json", pair_view)
    write_or_verify_json(out / "STRONG_RESEARCHER_PRE_PRIMARY_DYNAMIC_CONTRACT_V2.json", dynamic_contract)
    write_or_verify_json(out / "RESEARCHER_MEMORY_VIEW_V1.json", current_memory)
    write_or_verify_json(out / "STRONG_RESEARCHER_BLIND_PRE_INPUT_V3.json", blind_input)
    write_or_verify_json(out / "V1232V_PRE_PROJECTION_V1.json", projection)
    write_or_verify_json(out / "V1232V_PRE_SCIENTIFIC_UNIT_IDENTITY_V1.json", unit_identity)
    write_or_verify_json(out / "V1232V_PRE_TASK_ACCESS_V1.json", task_access)
    activation_artifact = {
        "schema_id": "V1232V_DYNAMIC_PRE_ACTIVATION_V1",
        "schema_version": 1,
        "activation_sha256": activation,
        "source_v1232u_output_root": str(u_root),
        "source_v1232u_terminal_sha256": u_term["terminal_sha256"],
        "source_v1232u_pair_universe_sha256": u_pair["pair_universe_sha256"],
        "round_start_memory_snapshot_sha256": round_start_snapshot_sha,
        "stable_researcher_memory_signature_sha256": stable["stable_memory_signature_sha256"],
        "researcher_memory_candidate_view_count": stable["candidate_view_count"],
        "fixed_repo_head_oid": repo_identity["head_oid"],
        "fixed_repo_object_format": repo_identity["object_format"],
        "runtime_manifest_sha256": overlay_manifest["runtime_manifest_sha256"],
        "provider_call_budget": 1,
        "environment_call_budget": 0,
        "training_execution_budget": 0,
        "human_scientific_decision_budget": 0,
    }
    write_or_verify_json(out / "V1232V_DYNAMIC_PRE_ACTIVATION_V1.json", activation_artifact)
    resume_memory_census = {
        "schema_id": "V1232X_PREDECESSOR_RESEARCHER_MEMORY_RESUME_CENSUS_V1",
        "schema_version": 1,
        "round_start_memory_snapshot_sha256": round_start_snapshot_sha,
        "current_round_evidence_sha256": domain_hash("RESEARCHER_MEMORY_CURRENT_ROUND_EVIDENCE_V1", current_round_evidence),
        "all_matching_memory_view_count": len(all_memory_candidates),
        "excluded_current_round_derived_view_count": len(current_round_derived_memory_views),
        "predecessor_memory_candidate_view_count": len(memory_candidates),
        "stable_memory_signature_sha256": stable["stable_memory_signature_sha256"],
        "materialized_current_memory_view_sha256": current_memory["view_sha256"],
        "selection_rule": "EXCLUDE_EXACT_CURRENT_ROUND_EVIDENCE_BOUND_VIEWS_THEN_REQUIRE_ONE_STABLE_MEMORY_SIGNATURE",
        "filesystem_path_order_authority": False,
        "mtime_authority": False,
        "manual_memory_selection_allowed": False,
        "scientific_selection_changed": False,
        "provider_call_count": 0,
        "census_sha256": "0" * 64,
    }
    resume_memory_census["census_sha256"] = domain_hash(
        "V1232X_PREDECESSOR_RESEARCHER_MEMORY_RESUME_CENSUS_V1",
        resume_memory_census,
        excluded_field="census_sha256",
    )
    write_or_verify_json(out / "V1232X_PREDECESSOR_RESEARCHER_MEMORY_RESUME_CENSUS_V1.json", resume_memory_census)

    rendered = rr.render_stage_request(stage_id="R-PRE-PRIMARY-V2", projection=projection)
    logical_id = expected_logical_call_id(
        unit_identity=unit_identity,
        round_id=str(u_term["round_id"]),
        policy_version=str(u_term["parent_policy_id"]),
        request_body_sha256=rendered["request_body_sha256"],
        domain_hash=domain_hash,
    )
    call_dir = runtime_root / logical_id
    provider_calls = 0
    reused = False
    recovery_provider_calls = 0
    recovery_terminal_reused = False
    recovery_class = None
    recovery_logical_id = None
    original_pre_status = None

    recovery_policy = load_json(RECOVERY_POLICY_PATH)
    if recovery_policy.get("schema_id") != "V1232W_AUTONOMOUS_INFRASTRUCTURE_RECOVERY_POLICY_V1":
        raise RuntimeError("V1232X_RECOVERY_POLICY_SCHEMA_INVALID")
    if int(recovery_policy.get("maximum_provider_recovery_calls", -1)) != 1:
        raise RuntimeError("V1232X_RECOVERY_POLICY_BUDGET_DRIFT")
    write_or_verify_json(out / "V1232W_AUTONOMOUS_INFRASTRUCTURE_RECOVERY_POLICY_V1.json", recovery_policy)

    def _load_existing_terminal(*, expected_id: str, identity: Mapping[str, object]) -> tuple[str, Path, dict[str, object]]:
        cdir = runtime_root / expected_id
        if cdir.is_symlink() or not cdir.is_dir():
            raise RuntimeError("PRE_EXISTING_CALL_DIR_INVALID_NO_RESEND:" + expected_id)
        logical_path = cdir / "logical_call.json"
        if not logical_path.is_file() or logical_path.is_symlink():
            raise RuntimeError("PRE_UNSAFE_PARTIAL_CALL_NO_RESEND:" + expected_id)
        logical = load_json(logical_path)
        checks = {
            "logical_call_id": expected_id,
            "scientific_unit_identity_sha256": identity["identity_sha256"],
            "stage_id": "R-PRE-PRIMARY-V2",
            "condition_id": None,
            "round_id": u_term["round_id"],
            "policy_version": u_term["parent_policy_id"],
            "request_body_sha256": rendered["request_body_sha256"],
        }
        for k, v in checks.items():
            if logical.get(k) != v:
                raise RuntimeError("PRE_EXISTING_TERMINAL_IDENTITY_MISMATCH:" + k)
        return str(logical.get("terminal_method_status")), cdir, logical

    def _classify_infra(cdir: Path, status: str, *, classification_name: str) -> dict[str, object]:
        method_path = cdir / "method_result.json"
        attempt_path = cdir / "attempt_000.json"
        transport_path = cdir / "transport_http_meta.json"
        if not method_path.is_file() or method_path.is_symlink():
            raise RuntimeError("PRE_METHOD_RESULT_MISSING_NO_RECOVERY:" + cdir.name)
        if not attempt_path.is_file() or attempt_path.is_symlink():
            raise RuntimeError("PRE_ATTEMPT_LEDGER_MISSING_NO_RECOVERY:" + cdir.name)
        if not transport_path.is_file() or transport_path.is_symlink():
            raise RuntimeError("PRE_TRANSPORT_META_MISSING_NO_RECOVERY:" + cdir.name)
        method = load_json(method_path)
        attempt = load_json(attempt_path)
        transport = load_json(transport_path)
        if method.get("status") != status:
            raise RuntimeError("PRE_METHOD_LOGICAL_STATUS_MISMATCH:" + cdir.name)
        classified = classify_infrastructure_recovery(method=method, attempt=attempt, transport_meta=transport)
        record = {
            "schema_id": "V1232X_PRE_INFRASTRUCTURE_RECOVERY_CLASSIFICATION_V1",
            "schema_version": 1,
            "logical_call_id": cdir.name,
            "terminal_method_status": status,
            "failure_class": method.get("failure_class"),
            "counts_as_method_failure": method.get("counts_as_method_failure"),
            "hard_stop": method.get("hard_stop"),
            "bytes_transmission_state": attempt.get("bytes_transmission_state"),
            "retry_class": attempt.get("retry_class"),
            "legacy_retry_authority": attempt.get("retry_authority"),
            "terminal_attempt_status": attempt.get("terminal_attempt_status"),
            "transport_failure_class": transport.get("failure_class"),
            "http_status": transport.get("http_status"),
            "recovery_eligible": bool(classified.get("eligible")),
            "recovery_class": classified.get("recovery_class"),
            "request_confirmed_not_sent": bool(classified.get("request_confirmed_not_sent")),
            "provider_rejection_confirmed": bool(classified.get("provider_rejection_confirmed")),
            "historical_classifier_git_blob_oid": recovery_policy["historical_classifier"]["git_blob_oid"],
            "request_body_sha256": rendered["request_body_sha256"],
            "classification_sha256": "0" * 64,
        }
        record["classification_sha256"] = domain_hash("V1232X_PRE_INFRASTRUCTURE_RECOVERY_CLASSIFICATION_V1", record, excluded_field="classification_sha256")
        write_or_verify_json(out / classification_name, record)
        return record

    # First reconcile the exact original V1232V logical call. Never resend the same logical_call_id.
    if call_dir.exists() or call_dir.is_symlink():
        status, call_dir, logical = _load_existing_terminal(expected_id=logical_id, identity=unit_identity)
        reused = True
        original_pre_status = status
        if status == "ACCEPTED":
            artifact = load_json(call_dir / "validated_artifact.json")
            artifact = finalize_dynamic_primary_pre_v2(value=artifact, pair_rows=pair_rows, contract=dynamic_contract, blind_input_sha256=blind_input["blind_input_sha256"], round_id=str(u_term["round_id"]))
            result = {"status": "ACCEPTED", "logical_call_id": logical_id, "call_dir": str(call_dir), "hard_stop": False, "validated_artifact_sha256": artifact["primary_record_sha256"]}
        else:
            classification = _classify_infra(call_dir, status, classification_name="V1232X_ORIGINAL_PRE_INFRASTRUCTURE_CLASSIFICATION_V1.json")
            recovery_class = classification.get("recovery_class")
            if not classification.get("recovery_eligible"):
                terminal = {
                    "schema_id": "PCHSI_V1232X_TERMINAL_V1", "schema_version": 1,
                    "status": "DYNAMIC_STRONG_PLANNER_PRE_AUTONOMOUS_RECOVERY_INELIGIBLE_FAIL_CLOSED",
                    "round_id": u_term["round_id"], "parent_policy_id": u_term["parent_policy_id"],
                    "pre_status": status, "pre_logical_call_id": logical_id,
                    "pre_failure_class": classification.get("failure_class"),
                    "pre_bytes_transmission_state": classification.get("bytes_transmission_state"),
                    "pre_retry_class": classification.get("retry_class"),
                    "autonomous_recovery_eligible": False,
                    "provider_call_count": 0, "recovery_provider_call_count": 0,
                    "same_logical_call_resend_count": 0, "automatic_retry_count": 0,
                    "environment_call_count": 0, "training_execution_count": 0,
                    "human_scientific_decision_count": 0, "human_disposition_required": False,
                    "scientific_attempt_consumed": False,
                    "next": "AUTONOMOUS_ROUND_ATTEMPT_INVALIDATION_OR_FAIL_CLOSED_NO_RESEND",
                    "terminal_sha256": "0" * 64,
                }
                terminal["terminal_sha256"] = domain_hash("PCHSI_V1232X_TERMINAL_V1", terminal, excluded_field="terminal_sha256")
                write_or_verify_json(out / "PCHSI_V1232X_TERMINAL_V1.json", terminal)
                print("STATUS=" + terminal["status"])
                print("V1232X_PRE_STATUS=" + status)
                print("V1232X_PRE_LOGICAL_CALL_ID=" + logical_id)
                print("V1232X_AUTONOMOUS_RECOVERY_ELIGIBLE=false")
                print("V1232X_PROVIDER_CALL_COUNT=0")
                print("V1232X_SAME_LOGICAL_CALL_RESEND_COUNT=0")
                print("HUMAN_SCIENTIFIC_DECISION_COUNT=0")
                print("HUMAN_DISPOSITION_REQUIRED=false")
                return 20
            if not args.authorize_bounded_infrastructure_recovery:
                readiness = {
                    "schema_id": "V1232X_PRE_AUTONOMOUS_RECOVERY_READINESS_V1", "schema_version": 1,
                    "status": "SAFE_INFRASTRUCTURE_RECOVERY_CLASSIFIED_AWAITING_INVOCATION_START_POLICY_AUTHORIZATION",
                    "round_id": u_term["round_id"], "parent_policy_id": u_term["parent_policy_id"],
                    "pre_status": status, "pre_logical_call_id": logical_id,
                    "pre_failure_class": classification.get("failure_class"),
                    "pre_bytes_transmission_state": classification.get("bytes_transmission_state"),
                    "pre_retry_class": classification.get("retry_class"),
                    "autonomous_recovery_eligible": True,
                    "provider_call_count": 0, "same_logical_call_resend_count": 0,
                    "human_scientific_decision_count": 0, "human_disposition_required": False,
                    "next": "RERUN_SAME_PACKAGE_WITH_INVOCATION_START_BOUNDED_INFRASTRUCTURE_POLICY_AUTHORIZATION",
                    "readiness_sha256": "0" * 64,
                }
                readiness["readiness_sha256"] = domain_hash("V1232X_PRE_AUTONOMOUS_RECOVERY_READINESS_V1", readiness, excluded_field="readiness_sha256")
                write_or_verify_json(out / "V1232X_PRE_AUTONOMOUS_RECOVERY_READINESS_V1.json", readiness)
                print("STATUS=" + readiness["status"])
                print("V1232X_AUTONOMOUS_RECOVERY_ELIGIBLE=true")
                print("V1232X_PROVIDER_CALL_COUNT=0")
                print("V1232X_SAME_LOGICAL_CALL_RESEND_COUNT=0")
                print("HUMAN_SCIENTIFIC_DECISION_COUNT=0")
                print("HUMAN_DISPOSITION_REQUIRED=false")
                return 21

            authority = {
                "schema_id": "V1232X_PRE_BOUNDED_INFRASTRUCTURE_RECOVERY_AUTHORITY_V1",
                "schema_version": 1,
                "original_logical_call_id": logical_id,
                "original_scientific_unit_identity_sha256": unit_identity["identity_sha256"],
                "original_request_body_sha256": rendered["request_body_sha256"],
                "recovery_class": recovery_class,
                "original_failure_class": classification.get("failure_class"),
                "maximum_provider_recovery_calls": recovery_policy["maximum_provider_recovery_calls"],
                "second_recovery_authorized": False,
                "same_logical_call_resend_authorized": False,
                "projection_change_authorized": False,
                "request_body_change_authorized": False,
                "model_change_authorized": False,
                "scientific_attempt_increment": 0,
                "human_scientific_decision_count": 0,
                "invocation_start_policy_authorized": True,
                "authority_sha256": "0" * 64,
            }
            authority["authority_sha256"] = domain_hash("V1232X_PRE_BOUNDED_INFRASTRUCTURE_RECOVERY_AUTHORITY_V1", authority, excluded_field="authority_sha256")
            write_or_verify_json(out / "V1232X_PRE_BOUNDED_INFRASTRUCTURE_RECOVERY_AUTHORITY_V1.json", authority)

            remediation_unit_id = domain_hash("V1232X_PRE_INFRASTRUCTURE_REMEDIATION_UNIT_V1", {
                "original_logical_call_id": logical_id,
                "original_scientific_unit_identity_sha256": unit_identity["identity_sha256"],
                "request_body_sha256": rendered["request_body_sha256"],
                "recovery_class": recovery_class,
                "original_failure_class": classification.get("failure_class"),
                "recovery_authority_sha256": authority["authority_sha256"],
            })
            remediation_identity = build_scientific_unit_identity(
                scientific_unit_type="ROUND",
                scientific_unit_id=remediation_unit_id,
                source_unit_manifest_sha256=blind_input["blind_input_sha256"],
                task_set_manifest_sha256=u_pair["pair_universe_sha256"],
                task_id=None,
                gamefile_sha256=None,
                group_manifest_sha256=None,
                round_evidence_package_sha256=u_tail["terminal_sha256"],
            )
            recovery_logical_id = expected_logical_call_id(
                unit_identity=remediation_identity,
                round_id=str(u_term["round_id"]),
                policy_version=str(u_term["parent_policy_id"]),
                request_body_sha256=rendered["request_body_sha256"],
                domain_hash=domain_hash,
            )
            recovery_call_dir = runtime_root / recovery_logical_id
            if recovery_call_dir.exists() or recovery_call_dir.is_symlink():
                recovery_status, recovery_call_dir, _ = _load_existing_terminal(expected_id=recovery_logical_id, identity=remediation_identity)
                recovery_terminal_reused = True
                if recovery_status != "ACCEPTED":
                    recovery_classification = _classify_infra(recovery_call_dir, recovery_status, classification_name="V1232X_REMEDIATION_PRE_INFRASTRUCTURE_CLASSIFICATION_V1.json")
                    terminal = {
                        "schema_id": "PCHSI_V1232X_TERMINAL_V1", "schema_version": 1,
                        "status": "BOUNDED_INFRASTRUCTURE_REMEDIATION_NOT_ACCEPTED_NO_SECOND_RECOVERY",
                        "round_id": u_term["round_id"], "parent_policy_id": u_term["parent_policy_id"],
                        "pre_status": status, "pre_logical_call_id": logical_id,
                        "recovery_class": recovery_class,
                        "recovery_logical_call_id": recovery_logical_id,
                        "recovery_status": recovery_status,
                        "recovery_failure_class": recovery_classification.get("failure_class"),
                        "provider_call_count": 1, "recovery_provider_call_count": 1,
                        "same_logical_call_resend_count": 0, "automatic_retry_count": 0,
                        "environment_call_count": 0, "training_execution_count": 0,
                        "human_scientific_decision_count": 0, "human_disposition_required": False,
                        "scientific_attempt_consumed": False,
                        "next": "AUTONOMOUS_ROUND_ATTEMPT_INVALIDATION_OR_FAIL_CLOSED_NO_SECOND_RECOVERY",
                        "terminal_sha256": "0" * 64,
                    }
                    terminal["terminal_sha256"] = domain_hash("PCHSI_V1232X_TERMINAL_V1", terminal, excluded_field="terminal_sha256")
                    write_or_verify_json(out / "PCHSI_V1232X_TERMINAL_V1.json", terminal)
                    print("STATUS=" + terminal["status"])
                    print("V1232X_RECOVERY_STATUS=" + recovery_status)
                    print("V1232X_PROVIDER_CALL_COUNT=0")
                    print("V1232X_SAME_LOGICAL_CALL_RESEND_COUNT=0")
                    print("HUMAN_SCIENTIFIC_DECISION_COUNT=0")
                    print("HUMAN_DISPOSITION_REQUIRED=false")
                    return 20
                recovery_provider_calls = 1
                artifact = load_json(recovery_call_dir / "validated_artifact.json")
                artifact = finalize_dynamic_primary_pre_v2(value=artifact, pair_rows=pair_rows, contract=dynamic_contract, blind_input_sha256=blind_input["blind_input_sha256"], round_id=str(u_term["round_id"]))
                result = {"status": "ACCEPTED", "logical_call_id": recovery_logical_id, "call_dir": str(recovery_call_dir), "hard_stop": False, "validated_artifact_sha256": artifact["primary_record_sha256"]}
            else:
                result = orch.execute_one(
                    output_root=runtime_root,
                    unit_identity=remediation_identity,
                    stage_id="R-PRE-PRIMARY-V2",
                    condition_id=None,
                    round_id=str(u_term["round_id"]),
                    policy_version=str(u_term["parent_policy_id"]),
                    projection=projection,
                    task_access=task_access,
                )
                provider_calls = 1
                recovery_provider_calls = 1
                recovery_status = str(result.get("status"))
                if recovery_status != "ACCEPTED":
                    # Re-open the durable remediation ledger only to classify it; never authorize a second provider call.
                    if not recovery_call_dir.is_dir() or recovery_call_dir.is_symlink():
                        raise RuntimeError("REMEDIATION_CALL_DIR_MISSING_AFTER_EXECUTION:" + recovery_logical_id)
                    recovery_classification = _classify_infra(recovery_call_dir, recovery_status, classification_name="V1232X_REMEDIATION_PRE_INFRASTRUCTURE_CLASSIFICATION_V1.json")
                    terminal = {
                        "schema_id": "PCHSI_V1232X_TERMINAL_V1", "schema_version": 1,
                        "status": "BOUNDED_INFRASTRUCTURE_REMEDIATION_NOT_ACCEPTED_NO_SECOND_RECOVERY",
                        "round_id": u_term["round_id"], "parent_policy_id": u_term["parent_policy_id"],
                        "pre_status": status, "pre_logical_call_id": logical_id,
                        "recovery_class": recovery_class,
                        "recovery_logical_call_id": recovery_logical_id,
                        "recovery_status": recovery_status,
                        "recovery_failure_class": recovery_classification.get("failure_class"),
                        "provider_call_count": provider_calls, "recovery_provider_call_count": recovery_provider_calls,
                        "same_logical_call_resend_count": 0, "automatic_retry_count": 0,
                        "environment_call_count": 0, "training_execution_count": 0,
                        "human_scientific_decision_count": 0, "human_disposition_required": False,
                        "scientific_attempt_consumed": False,
                        "next": "AUTONOMOUS_ROUND_ATTEMPT_INVALIDATION_OR_FAIL_CLOSED_NO_SECOND_RECOVERY",
                        "terminal_sha256": "0" * 64,
                    }
                    terminal["terminal_sha256"] = domain_hash("PCHSI_V1232X_TERMINAL_V1", terminal, excluded_field="terminal_sha256")
                    write_or_verify_json(out / "PCHSI_V1232X_TERMINAL_V1.json", terminal)
                    print("V1232X_PRE_RECOVERY_CALL status=" + recovery_status + " reused=false logical_call_id=" + recovery_logical_id, flush=True)
                    print("STATUS=" + terminal["status"])
                    print("V1232X_PROVIDER_CALL_COUNT=" + str(provider_calls))
                    print("V1232X_SAME_LOGICAL_CALL_RESEND_COUNT=0")
                    print("HUMAN_SCIENTIFIC_DECISION_COUNT=0")
                    print("HUMAN_DISPOSITION_REQUIRED=false")
                    return 20
                artifact = load_json(recovery_call_dir / "validated_artifact.json")
                artifact = finalize_dynamic_primary_pre_v2(value=artifact, pair_rows=pair_rows, contract=dynamic_contract, blind_input_sha256=blind_input["blind_input_sha256"], round_id=str(u_term["round_id"]))
    else:
        raise RuntimeError("V1232X_ORIGINAL_V1232V_PRE_CALL_MISSING_NO_REEXECUTION:" + logical_id)

    accepted_logical_id = recovery_logical_id if recovery_logical_id is not None else logical_id
    print("V1232X_PRE_CALL status=ACCEPTED reused=" + str(reused or recovery_terminal_reused).lower() + " logical_call_id=" + str(accepted_logical_id), flush=True)
    if normalization_state.get("used") and normalization_state.get("receipt"):
        receipt = dict(normalization_state["receipt"])
        receipt["normalized_primary_record_sha256"] = artifact["primary_record_sha256"]
        receipt["receipt_sha256"] = "0" * 64
        receipt["receipt_sha256"] = domain_hash("V1232V_DYNAMIC_PRE_V2_SEMANTIC_NORMALIZATION_RECEIPT_V1", receipt, excluded_field="receipt_sha256")
        write_or_verify_json(out / "V1232V_DYNAMIC_PRE_V2_SEMANTIC_NORMALIZATION_RECEIPT_V1.json", receipt)

    handoff = freeze_f0f1_handoff(
        artifact=artifact,
        pair_view=pair_view,
        protocol=protocol,
        u_pair_sha=u_pair["pair_universe_sha256"],
        pre_artifact_sha=artifact["primary_record_sha256"],
        domain_hash=domain_hash,
    )
    write_or_verify_json(out / "V1232V_PLANNER_BOUND_F0F1_LAUNCH_HANDOFF_V1.json", handoff)

    selected_count = int(artifact["selected_state_count"])
    branch_budget = int(artifact["verification_plan"]["selected_branch_run_budget"])
    next_status = (
        "CURRENT_TRAIN_EXACT_STATE_REPLAY_REBIND_THEN_NATIVE_F0F1_INDEPENDENT_VERIFIER"
        if selected_count > 0
        else "ZERO_SELECTED_STATES_ROUTE_TO_STRONG_PLANNER_POST_NO_TRAIN_GOVERNANCE"
    )
    terminal = {
        "schema_id": "PCHSI_V1232X_TERMINAL_V1", "schema_version": 1,
        "status": "DYNAMIC_STRONG_PLANNER_PRE_V2_ACCEPTED_F0F1_HANDOFF_READY_AFTER_AUTONOMOUS_RECONCILIATION",
        "round_id": u_term["round_id"], "parent_policy_id": u_term["parent_policy_id"],
        "source_v1232u_terminal_sha256": u_term["terminal_sha256"],
        "source_v1232u_pair_universe_sha256": u_pair["pair_universe_sha256"],
        "dynamic_pair_count": len(pair_rows),
        "pair_representation_view_sha256": pair_view["view_sha256"],
        "researcher_memory_view_sha256": current_memory["view_sha256"],
        "dynamic_contract_sha256": dynamic_contract["contract_sha256"],
        "blind_input_sha256": blind_input["blind_input_sha256"],
        "original_pre_logical_call_id": logical_id,
        "accepted_pre_logical_call_id": accepted_logical_id,
        "recovery_class": recovery_class,
        "recovery_terminal_reused": recovery_terminal_reused,
        "pre_primary_record_sha256": artifact["primary_record_sha256"],
        "selected_state_count": selected_count,
        "selected_branch_run_budget": branch_budget,
        "f0f1_handoff_sha256": handoff["handoff_sha256"],
        "provider_call_count": recovery_provider_calls,
        "recovery_provider_call_count": recovery_provider_calls,
        "original_pre_terminal_reused": reused,
        "pre_terminal_reused": bool(reused or recovery_terminal_reused),
        "semantic_normalization_used": bool(normalization_state.get("used")),
        "same_logical_call_resend_count": 0,
        "automatic_retry_count": 0,
        "environment_call_count": 0,
        "training_execution_count": 0,
        "human_scientific_decision_count": 0,
        "human_disposition_required": False,
        "effect_authority": "INDEPENDENT_ENVIRONMENT_VERIFIER_ONLY",
        "training_policy_status": "HOLD_PENDING_VERIFIED_F0F1_MANIFEST",
        "next": next_status,
        "terminal_sha256": "0" * 64,
    }
    terminal["terminal_sha256"] = domain_hash("PCHSI_V1232X_TERMINAL_V1", terminal, excluded_field="terminal_sha256")
    write_or_verify_json(out / "PCHSI_V1232X_TERMINAL_V1.json", terminal)

    print("STATUS=" + terminal["status"])
    print("V1232X_OUTPUT_ROOT=" + str(out))
    print("V1232X_DYNAMIC_PAIR_COUNT=" + str(len(pair_rows)))
    print("V1232X_SELECTED_STATE_COUNT=" + str(selected_count))
    print("V1232X_SELECTED_BRANCH_RUN_BUDGET=" + str(branch_budget))
    print("V1232X_PROVIDER_CALL_COUNT=" + str(recovery_provider_calls))
    print("V1232X_PROVIDER_CALL_COUNT_THIS_INVOCATION=" + str(provider_calls))
    print("V1232X_PRE_TERMINAL_REUSED=" + str(bool(reused or recovery_terminal_reused)).lower())
    print("V1232X_SEMANTIC_NORMALIZATION_USED=" + str(bool(normalization_state.get('used'))).lower())
    print("V1232X_SAME_LOGICAL_CALL_RESEND_COUNT=0")
    print("V1232X_ENVIRONMENT_CALL_COUNT=0")
    print("V1232X_TRAINING_EXECUTION_COUNT=0")
    print("HUMAN_SCIENTIFIC_DECISION_COUNT=0")
    print("HUMAN_DISPOSITION_REQUIRED=false")
    print("V1232X_RECOVERY_CLASS=" + str(recovery_class))
    print("V1232X_RECOVERY_PROVIDER_CALL_COUNT=" + str(recovery_provider_calls))
    print("V1232X_NEXT=" + next_status)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
