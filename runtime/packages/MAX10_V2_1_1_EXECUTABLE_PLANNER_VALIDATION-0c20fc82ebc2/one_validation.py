"""One isolated, reused-input validation; native science and tail remain owners.

The caller installs the registered runtime/strategy/PRE extensions first. This
module neither resumes a campaign nor creates a next request. Its source request
is intentionally the original request; experiment identity is separate.
"""
from __future__ import annotations

from contextlib import contextmanager
import copy
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import types


class ValidationError(ValueError):
    pass


SOURCE_FILES = {
    "census": "local/GROUP_PREPARATION_CENSUS.json",
    "tail": "group/V1232U_STRONG_ANALYZER_TAIL_TERMINAL_V1.json",
    "universe": "group/V1232U_DYNAMIC_PLANNER_PAIR_UNIVERSE_V1.json",
    "execution": "local/strong_local_runtime/execution_manifest.json",
    "source_units": "local/SOURCE_UNITS.json",
}
SCOPE = {
    "validation_kind": "REUSED_INPUT_STRATEGY_VALIDATION",
    "formal_valid_round_contribution": 0,
    "independent_new_source_sample_count": 0,
    "new_rollout_count": 0,
    "new_analyzer_call_count": 0,
    "next_round_launched": False,
    "old_campaign_authority_modified": False,
}


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode("utf-8")


def _path(value):
    path = Path(value)
    if not path.is_absolute() or ".." in path.parts:
        raise ValidationError("EXACT_ABSOLUTE_PATH_REQUIRED")
    for node in (path, *path.parents):
        if node.is_symlink() or (hasattr(node, "is_junction") and node.is_junction()):
            raise ValidationError("PATH_ALIAS_FORBIDDEN")
    return path


def _sha(value, label):
    if not isinstance(value, str) or re.fullmatch("[0-9a-f]{64}", value) is None:
        raise ValidationError("SHA256_REQUIRED:" + label)
    return value


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValidationError("DUPLICATE_JSON_KEY:" + key)
        value[key] = item
    return value


def _loads(raw):
    def bad_constant(value):
        raise ValidationError("NONFINITE_JSON:" + value)
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=bad_constant)


def normalize_ref(ref):
    if not isinstance(ref, dict) or set(ref) not in ({"path", "sha256"}, {"path", "file_sha256"}):
        raise ValidationError("EXACT_FILE_REF_REQUIRED")
    return {"path": str(_path(ref["path"])),
            "sha256": _sha(ref.get("sha256", ref.get("file_sha256")), "file ref")}


def read_ref(ref):
    ref = normalize_ref(ref)
    raw = _path(ref["path"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != ref["sha256"]:
        raise ValidationError("SOURCE_FILE_SHA_MISMATCH:" + ref["path"])
    value = _loads(raw)
    if not isinstance(value, dict):
        raise ValidationError("OBJECT_REQUIRED:" + ref["path"])
    return value


def file_ref(path):
    path = _path(path)
    return {"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def write_once(path, value):
    path = _path(Path(path).absolute())
    raw = canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != raw:
            raise ValidationError("IMMUTABLE_IDENTITY_CONFLICT:" + str(path))
        return file_ref(path)
    fd, name = tempfile.mkstemp(prefix="." + path.name, dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if _path(path).read_bytes() != raw:
                raise ValidationError("IMMUTABLE_IDENTITY_CONFLICT:" + str(path))
    finally:
        temporary.unlink(missing_ok=True)
    return file_ref(path)


@contextmanager
def validation_lock(root):
    root = _path(root)
    root.mkdir(parents=True, exist_ok=True)
    path = _path(root / ".validation.lock")
    with path.open("a+b") as stream:
        if os.name == "nt":
            import msvcrt
            if path.stat().st_size == 0:
                stream.write(b"0"); stream.flush()
            stream.seek(0)
            try:
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise ValidationError("VALIDATION_WRITER_ALREADY_ACTIVE") from exc
            try:
                yield
            finally:
                stream.seek(0)
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try:
                fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise ValidationError("VALIDATION_WRITER_ALREADY_ACTIVE") from exc
            try:
                yield
            finally:
                fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def _source_inputs(authority):
    root = _path(authority["source_analyzer_root"])
    refs = authority["source_files"]
    if set(refs) != set(SOURCE_FILES):
        raise ValidationError("SOURCE_FILE_ROLES_MISMATCH")
    values = {}
    for role, relative in SOURCE_FILES.items():
        if _path(refs[role]["path"]) != root / relative:
            raise ValidationError("SOURCE_TYPED_PATH_MISMATCH:" + role)
        values[role] = read_ref(refs[role])
    return values


def _preflight(binding, values, authority, root):
    if authority.get("schema_id") != "PCHSI_REUSED_INPUT_SINGLE_VALIDATION_AUTHORITY_V1":
        raise ValidationError("VALIDATION_AUTHORITY_SCHEMA")
    if type(authority.get("max_validation_runs")) is not int or authority["max_validation_runs"] != 1:
        raise ValidationError("EXACTLY_ONE_VALIDATION_REQUIRED")
    eid = authority.get("experiment_id")
    if not isinstance(eid, str) or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,127}", eid) is None:
        raise ValidationError("EXPERIMENT_ID_REQUIRED")
    _sha(authority["implementation_sha256"], "implementation")
    _sha(authority["source_pre_logical_call_id"], "source PRE")
    if type(authority["round_index"]) is not int or authority["round_index"] < 1:
        raise ValidationError("SOURCE_NATIVE_ROUND_INDEX_REQUIRED")
    start = read_ref(authority["source_request_ref"])
    result = read_ref(authority["source_result_ref"])
    if values["request"] != start or read_ref(binding["refs"]["request"]) != start:
        raise ValidationError("FROZEN_SOURCE_REQUEST_CHANGED")
    if any(binding.get(k) != start[k] for k in ("round_id", "parent_policy_id")):
        raise ValidationError("BINDING_SOURCE_IDENTITY_CHANGED")
    for key in ("round_id", "request_sha256", "execution_attempt_id", "parent_policy_id",
                "parent_policy_artifact_sha256", "round_start_memory_snapshot_sha256"):
        if result.get(key) != start[key]:
            raise ValidationError("SOURCE_RESULT_IDENTITY_CHANGED:" + key)
    if (result.get("outcome") not in {"NO_TRAINING_UPDATE", "ROLLED_BACK"}
            or result.get("next_parent_policy_id") != start["parent_policy_id"]
            or result.get("next_parent_policy_artifact_sha256") != start["parent_policy_artifact_sha256"]):
        raise ValidationError("SOURCE_PARENT_REUSE_NOT_VALID")
    parent = read_ref(authority["live_parent_ref"])
    if (parent.get("policy_id") != start["parent_policy_id"]
            or parent.get("artifact_sha256") != start["parent_policy_artifact_sha256"]):
        raise ValidationError("LIVE_PARENT_CHANGED_REUSE_FORBIDDEN")
    for name, role in (("current_inputs_ref", "current_inputs"),
                       ("current_execution_binding_ref", "rollout_execution_binding"),
                       ("current_memory_state_ref", "memory_state")):
        if normalize_ref(authority[name]) != normalize_ref(result["stage_evidence_refs"][role]):
            raise ValidationError("SOURCE_CURRENT_REF_CHANGED:" + role)
        read_ref(authority[name])
    if authority["current_parent_context"] != result["current_parent_context"]:
        raise ValidationError("SOURCE_PARENT_CONTEXT_CHANGED")
    source_root = _path(authority["source_analyzer_root"])
    if root == source_root or root.is_relative_to(source_root) or source_root.is_relative_to(root):
        raise ValidationError("VALIDATION_ROOT_MUST_BE_ISOLATED")
    sources = _source_inputs(authority)
    return start, result, sources


def _stage(root, name, inputs, operation, recover_callable=None):
    directory = root / "stages" / name
    intent = {"schema_id": "SINGLE_VALIDATION_STAGE_INTENT_V1", "stage": name, "inputs": inputs}
    intent_path = directory / "INTENT.json"
    receipt_path = directory / "RESULT.json"
    existed = intent_path.exists()
    if receipt_path.exists() and not existed:
        raise ValidationError("STAGE_RESULT_WITHOUT_INTENT:" + name)
    intent_ref = write_once(intent_path, intent)
    if receipt_path.exists():
        receipt = read_ref(file_ref(receipt_path))
        if receipt.get("intent_ref") != intent_ref:
            raise ValidationError("STAGE_RESULT_INTENT_IDENTITY")
        return receipt["output"]
    if existed:
        if recover_callable is None:
            raise ValidationError("AMBIGUOUS_STAGE_NO_AUTOMATIC_RESEND:" + name)
        adopted = recover_callable(stage=name, inputs=inputs, stage_intent_ref=intent_ref, experiment_root=root)
        proof = read_ref(adopted["native_recovery_ref"])
        if (proof.get("status") != "VERIFIED_NATIVE_STAGE_RECOVERY" or proof.get("stage") != name
                or normalize_ref(proof["intent_ref"]) != normalize_ref(intent_ref)):
            raise ValidationError("NATIVE_RECOVERY_PROOF_IDENTITY")
        output = adopted["output"]
    else:
        output = operation()
    write_once(receipt_path, {"schema_id": "SINGLE_VALIDATION_STAGE_RESULT_V1",
                             "intent_ref": intent_ref, "output": output})
    return output


def _clone(function, globals_patch):
    result = types.FunctionType(function.__code__, {**function.__globals__, **globals_patch},
                                function.__name__, function.__defaults__, function.__closure__)
    result.__kwdefaults__ = function.__kwdefaults__
    return result


from memory_reader import memory_reuse_context


def export_validation(*, start, result, authority, experiment_root, native_module=None):
    """Use native lane projectors, with isolated derived authority and zero increment."""
    if native_module is None:
        from entry import paper_export as native_module
    root = _path(experiment_root)
    original_binding = read_ref(authority["paper_binding_ref"])
    contract = read_ref(authority["paper_contract_ref"])
    if original_binding["paper_export_contract_file_sha256"] != normalize_ref(authority["paper_contract_ref"])["sha256"]:
        raise ValidationError("EXPORT_SOURCE_CONTRACT_SHA_MISMATCH")
    formal = root / "validation_export_authority"
    contract_ref = write_once(formal / "PCHSI_PAPER_ROUND_EXPORT_CONTRACT_V1.json", contract)
    derived = {**original_binding, "paper_export_root": str(root / "validation_export_registry"),
        "paper_export_contract_file_sha256": contract_ref["sha256"],
        "source_formal_binding_ref": normalize_ref(authority["paper_binding_ref"]),
        "experiment_id": authority["experiment_id"], **SCOPE}
    write_once(formal / "FORMAL_MAX10_PAPER_TELEMETRY_BINDING_V1.json", derived)
    native_write = native_module._write_once

    def validation_write(path, value):
        path = _path(path)
        if not path.is_relative_to(root):
            raise ValidationError("EXPORT_WRITE_ESCAPES_VALIDATION_ROOT")
        value = copy.deepcopy(value)
        schema = value.get("schema_id")
        if schema == "FORMAL_PAPER_ATTEMPT_EXPORT_INDEX_V1":
            value.update(schema_id="REUSED_INPUT_VALIDATION_ATTEMPT_EXPORT_INDEX_V1",
                         experiment_id=authority["experiment_id"], valid_round_contribution=0,
                         source_request_ref=normalize_ref(authority["source_request_ref"]), **SCOPE)
        elif schema == "FORMAL_REGISTERED_PAPER_EXPORT_ENTRY_V1":
            value.update(schema_id="REUSED_INPUT_VALIDATION_EXPORT_ENTRY_V1",
                         experiment_id=authority["experiment_id"], **SCOPE)
        elif schema == "FORMAL_PAPER_LANE_PROJECTION_V1":
            value.update(experiment_id=authority["experiment_id"], **SCOPE)
        return native_write(path, value)

    exporter = _clone(native_module.export_attempt, {"_write_once": validation_write})
    deployment = {**authority["deployment"], "formal_state_root": str(formal)}
    return exporter(attempt_root=root, start=start, result=result, deployment=deployment)


class NativeOperations:
    """Default adapters import the already-installed, registered native runtime."""
    def validate_start(self, binding, values):
        from continuity_binding.api import native_request
        from adapter import validate_binding
        native_request(values["request"])
        observed = validate_binding(binding)
        if observed["request"] != values["request"]:
            raise ValidationError("NATIVE_SOURCE_REQUEST_CHANGED")

    def evidence(self, analyzer_root):
        from entry.driver import current_h44_evidence
        return current_h44_evidence(analyzer_root)

    def post(self, **kwargs):
        from continuity_binding.api import validate_current_post
        return validate_current_post(**kwargs)

    def replay(self, result):
        from entry.driver import replay_closed_h44
        replay_closed_h44(result)

    def train(self, **kwargs):
        from entry.training_job import execute_current_training_job
        return execute_current_training_job(**kwargs)

    def offoff(self, **kwargs):
        from entry.offoff_job import execute_current_offoff_job
        return execute_current_offoff_job(**kwargs)

    def close(self, *, reuse, **kwargs):
        from memory_binding import api as memory_api
        from entry.tail import close_round_tail
        with memory_reuse_context(memory_api, reuse["authority"], reuse["candidate_universe_ref"]):
            return close_round_tail(**kwargs)

    def validate_result(self, *, start, result, authority):
        from entry.driver import ExistingComponentRoundDriver
        # The native method's only instance dependencies are the exact deployment
        # and current-parent binding. No campaign preflight or admission is run.
        context = types.SimpleNamespace(deployment=authority["deployment"],owner_root=Path(authority["owner_root"]),
            _binding=lambda request: {"current_parent_context": authority["current_parent_context"]})
        ExistingComponentRoundDriver.validate_result(context, start, result)

    def export(self, **kwargs):
        return export_validation(**kwargs)


def run_validation(*, binding, values, core, authority, experiment_root,
                   pre_callable, capture_callable, h44_callable, native=None, recover_callable=None):
    """Execute/adopt exactly one validation, with no campaign or next-round hook.

    PRE uses the native positional signature and returns (accepted, handoff), or
    a dict with accepted/handoff and candidate_universe_ref for a derived universe.
    Capture and H44 retain their native positional signatures. Uncertain sent
    stages fail closed; reentry never silently sends them again.
    """
    root = _path(Path(experiment_root).absolute())
    authority = copy.deepcopy(authority)
    binding = copy.deepcopy(binding)
    values = copy.deepcopy(values)
    native = native or NativeOperations()
    from functools import partial
    stage = partial(_stage, recover_callable=recover_callable)
    start, source_result, sources = _preflight(binding, values, authority, root)
    binding.update(output_root=str(root / "analyzer"), _request=start)
    native.validate_start(binding, values)
    intent = {"schema_id": "REUSED_INPUT_SINGLE_VALIDATION_INTENT_V1", "authority": authority,
              "binding": binding, "experiment_root": str(root), **SCOPE}
    with validation_lock(root):
        intent_ref = write_once(root / "INTENT.json", intent)
        terminal_path = root / "VALIDATION_TERMINAL.json"
        if terminal_path.exists():
            terminal = read_ref(file_ref(terminal_path))
            if terminal.get("intent_ref") != intent_ref:
                raise ValidationError("VALIDATION_TERMINAL_INTENT_IDENTITY")
            if any(terminal.get(k) != v for k, v in SCOPE.items()):
                raise ValidationError("VALIDATION_TERMINAL_SCOPE_CHANGED")
            result = read_ref(terminal["result_ref"])
            native.validate_result(start=start, result=result, authority=authority)
            read_ref(terminal["export_ref"])
            return terminal
        if (root / "VALIDATION_STOP.json").exists() and recover_callable is None:
            raise ValidationError("PERSISTED_VALIDATION_STOP_NO_AUTOMATIC_RESEND")
        write_once(root / "INITIAL_ANALYZER_BINDING.json", binding)
        fixed = {"validation_intent_ref": intent_ref}
        try:
            universe_ref = authority.get("candidate_universe_ref", authority["source_files"]["universe"])
            universe = read_ref(universe_ref)

            def run_pre():
                value = pre_callable(binding, values, core, sources["tail"], universe, root / "analyzer/pre")
                if isinstance(value, (tuple, list)) and len(value) == 2:
                    value = {"accepted": value[0], "handoff": value[1], "candidate_universe_ref": universe_ref}
                if not isinstance(value, dict) or not {"accepted", "handoff"} <= set(value):
                    raise ValidationError("PRE_RESULT_CONTRACT")
                value.setdefault("candidate_universe_ref", universe_ref)
                value["binding_after_pre"] = copy.deepcopy(binding)
                return value

            pre = stage(root, "PRE", fixed, run_pre)
            binding = copy.deepcopy(pre.get("binding_after_pre", binding))
            write_once(root / "CURRENT_ANALYZER_BINDING.json", binding)
            accepted, handoff = pre["accepted"], pre["handoff"]
            new_id = accepted["accepted_pre_logical_call_id"]
            _sha(new_id, "new PRE")
            if new_id == authority["source_pre_logical_call_id"]:
                raise ValidationError("PRE_OLD_LOGICAL_IDENTITY_REUSE_FORBIDDEN")
            if not handoff.get("selected_states"):
                raise ValidationError("ZERO_SELECTED_PRE_IS_NOT_NO_TRAIN")
            candidate_universe_ref = pre["candidate_universe_ref"]
            read_ref(candidate_universe_ref)
            capture = stage(root, "CAPTURE", {**fixed, "pre": pre}, lambda: capture_callable(
                binding, values, core, root / "analyzer/pre", accepted, handoff,
                sources["census"]["sources"], root / "analyzer/h44"))
            stage(root, "H44", {**fixed, "capture": capture}, lambda: h44_callable(
                binding, capture, root / "analyzer/h44", execute=True))
            evidence = native.evidence(root / "analyzer")
            plan = read_ref(evidence["execution_plan"])
            old_plan = read_ref(source_result["stage_evidence_refs"]["execution_plan"])
            if plan.get("source_request") != start or plan.get("plan_sha256") == old_plan.get("plan_sha256"):
                raise ValidationError("NEW_EXECUTION_PLAN_IDENTITY_REQUIRED")
            if not _path(evidence["execution_plan"]["path"]).is_relative_to(root):
                raise ValidationError("NEW_EXECUTION_PLAN_MUST_BE_ISOLATED")
            replay_result = {"attempt_root": str(root), "stage_evidence_refs": evidence}
            native.replay(replay_result)
            post, _ = native.post(start=start, evidence_refs=evidence)
            recommendation = post.get("researcher_training_recommendation")
            if recommendation not in {"TRAIN", "NO_TRAIN"}:
                raise ValidationError("NATIVE_POST_ROUTE_REQUIRED")
            training_ref = next_policy = None
            parent_context = authority["current_parent_context"]
            if recommendation == "TRAIN":
                trained = stage(root, "TRAIN", {**fixed, "evidence": evidence}, lambda: native.train(
                    start=start, analyzer_binding=binding, h44_run_root=Path(evidence["execution_plan"]["path"]).parent,
                    output_root=root / "training", current_parent_context=parent_context,
                    round_index=authority["round_index"], deployment=authority["deployment"]))
                evaluated = stage(root, "OFFOFF", {**fixed, "trained": trained}, lambda: native.offoff(
                    start=start, current_inputs_ref=authority["current_inputs_ref"], trained=trained,
                    output_root=root / "offoff", deployment=authority["deployment"]))
                training_ref = evaluated["terminal_ref"]
                outcome = read_ref(training_ref)["outcome"]
                if outcome not in {"PROMOTED", "ROLLED_BACK"}:
                    raise ValidationError("NATIVE_OFFOFF_VERDICT_REQUIRED")
                if outcome == "PROMOTED":
                    next_policy = evaluated["next_policy_input_refs"]
                    parent_context = evaluated["current_parent_context"]

            def close():
                result = native.close(start=start, analyzer_binding=binding, analyzer_output_root=root / "analyzer",
                    attempt_root=root, stage_evidence_refs=evidence,
                    current_execution_binding_ref=authority["current_execution_binding_ref"],
                    current_inputs_ref=authority["current_inputs_ref"],
                    current_memory_state_ref=authority["current_memory_state_ref"],
                    training_result_ref=training_ref, next_policy_input_refs=next_policy,
                    reuse={"authority": authority, "candidate_universe_ref": candidate_universe_ref})
                result.update(attempt_root=str(root), current_parent_context=parent_context)
                if result.get("next_request") is not None:
                    raise ValidationError("VALIDATION_CANNOT_BUILD_NEXT_REQUEST")
                native.validate_result(start=start, result=result, authority=authority)
                return result

            result = stage(root, "MEMORY_CLOSE", {**fixed, "evidence": evidence,
                "training_terminal_ref": training_ref, "candidate_universe_ref": candidate_universe_ref}, close)
            result_ref = write_once(root / "VALIDATION_RESULT.json", result)
            export_ref = stage(root, "EXPORT", {**fixed, "result_ref": result_ref}, lambda: native.export(
                start=start, result=result, authority=authority, experiment_root=root))
            read_ref(export_ref)
            terminal = {"schema_id": "REUSED_INPUT_SINGLE_VALIDATION_TERMINAL_V1",
                "status": "VALIDATION_COMPLETE", "experiment_id": authority["experiment_id"],
                "source_round_id": start["round_id"], "source_request_ref": authority["source_request_ref"],
                "intent_ref": intent_ref, "result_ref": result_ref, "export_ref": export_ref,
                "validation_run_count": 1, **SCOPE}
            write_once(terminal_path, terminal)
            return terminal
        except Exception as exc:
            write_once(root / "VALIDATION_STOP.json", {
                "schema_id": "REUSED_INPUT_SINGLE_VALIDATION_STOP_V1", "intent_ref": intent_ref,
                "error_type": type(exc).__name__, "message": str(exc),
                "completion_claimed": False, "automatic_resend_authorized": False, **SCOPE})
            raise
