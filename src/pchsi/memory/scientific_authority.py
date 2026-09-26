"""Artifact-backed, independently recomputable scientific authorities.

A result authority is accepted only when it binds a pre-outcome execution
manifest, all registered cells, complete receipts/results, identity artifacts,
role-pack evidence, no-writeback/no-contamination audits, and a deterministic
recomputation under the frozen decision rule.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping

from pchsi.evaluation.canonical_evidence import (
    canonical_json_bytes,
    require_lower_sha256,
    sha256_bytes,
    strict_json_loads,
)
from pchsi.memory.scientific_decision import (
    REGISTERED_STAGES,
    STAGE_2,
    recompute_stage_decisions_v1,
    validate_cell_result_v1,
    validate_decision_rule_v1,
)

_AUTHORITY_KEYS = frozenset({
    "schema_id", "schema_version", "authority_scope", "scientific_stage",
    "result_authority_sha256", "execution_manifest_binding",
    "decision_rule_binding", "cell_census_binding", "audit_bindings",
    "registered_cell_count", "resolved_cell_count", "scientific_execution_complete",
    "method_frozen", "registered_statistical_decision", "supporting_artifacts",
    "result_payload", "authority_boundaries",
})
_BINDING_KEYS = frozenset({"path", "sha256", "size_bytes", "role"})
_AUDIT_BINDING_KEYS = frozenset({
    "contamination", "writeback", "independent_recomputation",
    "role_pack", "round_governance",
})
_BOUNDARY_KEYS = frozenset({
    "analyzer_is_proposal_only", "verifier_is_effect_authority",
    "tests_are_not_scientific_evidence", "no_hidden_writeback",
    "researcher_is_read_only_evidence_consumer",
})
_MANIFEST_KEYS = frozenset({
    "schema_id", "schema_version", "manifest_sha256", "stage", "fixed_code_head",
    "scientific_execution_authorized", "preoutcome_frozen", "registered_cell_count",
    "cell_result_schema_id", "bindings", "operational_paths",
})
_MANIFEST_BINDING_ROLES = frozenset({
    "scientific_protocol", "scientific_program", "runtime_identity",
    "policy_identity", "environment_identity", "panel", "schedule",
    "cell_manifest", "cell_executor", "decision_rule",
})
_CENSUS_KEYS = frozenset({
    "schema_id", "schema_version", "execution_manifest_sha256",
    "registered_cell_count", "resolved_cell_count", "cells", "census_sha256",
})
_CENSUS_ROW_KEYS = frozenset({
    "cell_id", "receipt_file_sha256", "result_file_sha256",
    "receipt_sha256", "cell_result_sha256",
})
_CELL_MANIFEST_ROW_KEYS = frozenset({
    "cell_id", "comparison_group_id", "condition", "round_index", "split",
    "task_id", "task_family", "snapshot_sha256",
})
_RECEIPT_KEYS = frozenset({
    "schema_id", "schema_version", "receipt_sha256", "cell_id",
    "execution_manifest_sha256", "cell_result_sha256", "cell_complete",
    "scientific_outcome_produced", "infrastructure_error",
})

_STAGE_SCHEMA = {
    "STAGE_1B_FROZEN_POLICY_FM0_FM3":
        "STAGE_1B_FROZEN_POLICY_FM0_FM3_RESULT_AUTHORITY_V2",
    "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY":
        "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY_RESULT_AUTHORITY_V2",
    "STAGE_3_FROZEN_FORMAL_EVALUATION":
        "STAGE_3_FROZEN_ID_OOD_RESULT_AUTHORITY_V2",
}
_STAGE_QUESTIONS = {
    "STAGE_1B_FROZEN_POLICY_FM0_FM3": frozenset({"Q1", "Q2", "Q3"}),
    "STAGE_2_MULTI_ROUND_EXTERNAL_MEMORY": frozenset({"Q1", "Q3"}),
    "STAGE_3_FROZEN_FORMAL_EVALUATION": frozenset({"Q1", "Q2", "Q3"}),
}


def _text(name: str, value: object) -> str:
    if not isinstance(value, str) or not value or any(ch in value for ch in "\x00\r\n"):
        raise ValueError(f"{name} must be nonempty one-line text")
    return value


def _hex40(name: str, value: object) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"{name} must be 40 lowercase hexadecimal characters")
    return value


def _exact(name: str, value: Mapping[str, object], keys: frozenset[str]) -> None:
    if set(value) != keys:
        raise ValueError(
            f"{name} fields mismatch: missing={sorted(keys-set(value))!r} "
            f"extra={sorted(set(value)-keys)!r}"
        )


def _domain_sha(domain: str, value: Mapping[str, object], field: str) -> str:
    payload = dict(value)
    payload.pop(field, None)
    return sha256_bytes(domain.encode("utf-8") + b"\0" + canonical_json_bytes(payload))


def _canonical_json(path: Path) -> dict[str, object]:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"regular non-symlink JSON required: {path}")
    raw = path.read_bytes()
    value = strict_json_loads(raw)
    if not isinstance(value, dict):
        raise TypeError(f"JSON object required: {path}")
    expected = canonical_json_bytes(value)
    if raw not in {expected, expected + b"\n"}:
        raise ValueError(f"noncanonical JSON: {path}")
    return value


def _artifact_path(root: Path, raw: object) -> Path:
    text = _text("artifact path", raw)
    pure = PurePosixPath(text)
    if pure.is_absolute() or not pure.parts or any(part in {".", ".."} for part in pure.parts):
        raise ValueError("artifact path must be normalized relative path")
    path = root.joinpath(*pure.parts)
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"supporting artifact invalid: {text}")
    return path


def _load_binding(
    *,
    root: Path,
    value: object,
    support_by_sha: Mapping[str, tuple[Path, str]],
    expected_role: str | None = None,
) -> tuple[Path, str]:
    if not isinstance(value, dict):
        raise TypeError("artifact binding must be object")
    _exact("artifact binding", value, _BINDING_KEYS)
    path = _artifact_path(root, value["path"])
    require_lower_sha256("artifact binding SHA", value["sha256"])
    if type(value["size_bytes"]) is not int or value["size_bytes"] < 0:
        raise ValueError("artifact binding size invalid")
    role = _text("artifact binding role", value["role"])
    if expected_role is not None and role != expected_role:
        raise ValueError(f"artifact role mismatch: expected {expected_role}, got {role}")
    raw = path.read_bytes()
    if len(raw) != value["size_bytes"] or sha256_bytes(raw) != value["sha256"]:
        raise ValueError("artifact binding bytes mismatch")
    support = support_by_sha.get(value["sha256"])
    if support is None or support[0] != path or support[1] != role:
        raise ValueError("bound artifact is absent from supporting_artifacts")
    return path, role


def _manifest_binding_digests(value: Mapping[str, object]) -> dict[str, dict[str, str]]:
    bindings = value["bindings"]
    if not isinstance(bindings, dict):
        raise TypeError("execution manifest bindings must be object")
    required = set(_MANIFEST_BINDING_ROLES)
    if value["stage"] == STAGE_2:
        required.add("snapshot_registry")
    else:
        required.add("snapshot")
    if not required.issubset(bindings):
        raise ValueError("execution manifest misses registered bindings")
    allowed = required
    if set(bindings) - allowed:
        raise ValueError("execution manifest contains unknown bindings")
    result: dict[str, dict[str, str]] = {}
    for name, row in bindings.items():
        if not isinstance(row, dict) or set(row) != {
            "file_sha256", "semantic_sha256", "size_bytes", "role"
        }:
            raise ValueError("execution manifest binding row invalid")
        require_lower_sha256(f"manifest file binding {name}", row["file_sha256"])
        require_lower_sha256(f"manifest semantic binding {name}", row["semantic_sha256"])
        if type(row["size_bytes"]) is not int or row["size_bytes"] < 0:
            raise ValueError("manifest binding size invalid")
        if row["role"] != name:
            raise ValueError("manifest binding role/name mismatch")
        result[name] = {
            "file_sha256": row["file_sha256"],
            "semantic_sha256": row["semantic_sha256"],
        }
    return result


def _collect_lower_sha256_strings(value: object) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for item in value.values():
            found.update(_collect_lower_sha256_strings(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_collect_lower_sha256_strings(item))
    elif (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    ):
        found.add(value)
    return found


def _validate_execution_manifest(
    value: dict[str, object],
    *,
    expected_stage: str,
    expected_fixed_code_head: str,
    expected_program_sha256: str,
) -> dict[str, str]:
    _exact("execution manifest", value, _MANIFEST_KEYS)
    if value["schema_id"] != "FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2" or value["schema_version"] != 2:
        raise ValueError("execution manifest schema mismatch")
    if value["stage"] != expected_stage:
        raise ValueError("execution manifest stage mismatch")
    if value["fixed_code_head"] != expected_fixed_code_head:
        raise ValueError("execution manifest fixed-head mismatch")
    if value["scientific_execution_authorized"] is not False:
        raise ValueError("execution manifest may not self-authorize")
    if value["preoutcome_frozen"] is not True:
        raise ValueError("execution manifest is not pre-outcome frozen")
    if type(value["registered_cell_count"]) is not int or value["registered_cell_count"] < 1:
        raise ValueError("execution manifest registered_cell_count invalid")
    if value["cell_result_schema_id"] != "FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1":
        raise ValueError("execution manifest cell-result schema mismatch")
    if not isinstance(value["operational_paths"], dict):
        raise TypeError("execution manifest operational_paths must be object")
    require_lower_sha256("execution manifest self hash", value["manifest_sha256"])
    expected = _domain_sha(
        "FAILURE_MEMORY_LIVE_EXECUTION_MANIFEST_V2",
        value,
        "manifest_sha256",
    )
    if value["manifest_sha256"] != expected:
        raise ValueError("execution manifest self-hash mismatch")
    bindings = _manifest_binding_digests(value)
    if bindings["scientific_program"]["semantic_sha256"] != expected_program_sha256:
        raise ValueError("execution manifest program semantic binding mismatch")
    return bindings


def _parse_jsonl(path: Path) -> list[dict[str, object]]:
    rows = []
    raw_bytes = path.read_bytes()
    for line_number, raw_line in enumerate(
        raw_bytes.splitlines(keepends=True),
        start=1,
    ):
        if raw_line in {b"\n", b"\r\n"}:
            raise ValueError(
                f"blank JSONL row {line_number}: {path}"
            )
        value = strict_json_loads(raw_line)
        if (
            not isinstance(value, dict)
            or canonical_json_bytes(value) != raw_line
        ):
            raise ValueError(
                f"noncanonical JSONL row {line_number}: {path}"
            )
        rows.append(value)
    if not rows:
        raise ValueError(f"empty JSONL artifact: {path}")
    return rows


def _validate_receipt(
    value: dict[str, object],
    *,
    cell_id: str,
    execution_manifest_sha256: str,
    result_sha256: str,
) -> None:
    _exact("cell receipt", value, _RECEIPT_KEYS)
    if value["schema_id"] != "FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1" or value["schema_version"] != 1:
        raise ValueError("cell receipt schema mismatch")
    if value["cell_id"] != cell_id or value["execution_manifest_sha256"] != execution_manifest_sha256:
        raise ValueError("cell receipt identity mismatch")
    if value["cell_result_sha256"] != result_sha256:
        raise ValueError("cell receipt result binding mismatch")
    if value["cell_complete"] is not True or value["scientific_outcome_produced"] is not True:
        raise ValueError("cell receipt is incomplete")
    if value["infrastructure_error"] is not False:
        raise ValueError("cell receipt reports infrastructure error")
    require_lower_sha256("receipt_sha256", value["receipt_sha256"])
    if value["receipt_sha256"] != _domain_sha(
        "FAILURE_MEMORY_CELL_TERMINAL_RECEIPT_V1", value, "receipt_sha256"
    ):
        raise ValueError("cell receipt self-hash mismatch")


@dataclass(frozen=True, slots=True)
class ValidatedScientificResultAuthorityV2:
    path: Path
    file_sha256: str
    stage: str
    result_authority_sha256: str
    question_decisions: Mapping[str, Mapping[str, object]]
    effect_estimates: Mapping[str, object]
    result_payload: Mapping[str, object]

    def disposition(self, question_id: str) -> str:
        row = self.question_decisions[question_id]
        return str(row["disposition"])

    def summary(self, question_id: str) -> str:
        row = self.question_decisions[question_id]
        return str(row["summary"])


def load_scientific_result_authority_v2(
    *,
    path: Path,
    expected_stage: str,
    expected_fixed_code_head: str,
    expected_scientific_program_sha256: str,
) -> ValidatedScientificResultAuthorityV2:
    if expected_stage not in REGISTERED_STAGES:
        raise ValueError("expected_stage is not registered")
    _hex40("expected_fixed_code_head", expected_fixed_code_head)
    require_lower_sha256("expected scientific program SHA", expected_scientific_program_sha256)
    authority_path = Path(path)
    value = _canonical_json(authority_path)
    _exact("scientific authority", value, _AUTHORITY_KEYS)
    if value["schema_id"] != _STAGE_SCHEMA[expected_stage] or value["schema_version"] != 2:
        raise ValueError("scientific authority schema mismatch")
    if value["scientific_stage"] != expected_stage:
        raise ValueError("scientific authority stage mismatch")
    _text("authority_scope", value["authority_scope"])
    root = authority_path.parent

    support = value["supporting_artifacts"]
    if not isinstance(support, list) or not support:
        raise ValueError("supporting_artifacts must be nonempty list")
    support_by_sha: dict[str, tuple[Path, str]] = {}
    seen_paths: set[str] = set()
    for row in support:
        if not isinstance(row, dict):
            raise TypeError("supporting artifact row must be object")
        _exact("supporting artifact", row, _BINDING_KEYS)
        path_value = _artifact_path(root, row["path"])
        require_lower_sha256("supporting artifact SHA", row["sha256"])
        role = _text("supporting artifact role", row["role"])
        if row["path"] in seen_paths or row["sha256"] in support_by_sha:
            raise ValueError("supporting artifact path or SHA repeats")
        raw = path_value.read_bytes()
        if type(row["size_bytes"]) is not int or row["size_bytes"] != len(raw):
            raise ValueError("supporting artifact size mismatch")
        if sha256_bytes(raw) != row["sha256"]:
            raise ValueError("supporting artifact SHA mismatch")
        seen_paths.add(row["path"])
        support_by_sha[row["sha256"]] = (path_value, role)

    execution_path, _ = _load_binding(
        root=root,
        value=value["execution_manifest_binding"],
        support_by_sha=support_by_sha,
        expected_role="EXECUTION_MANIFEST",
    )
    execution = _canonical_json(execution_path)
    manifest_bindings = _validate_execution_manifest(
        execution,
        expected_stage=expected_stage,
        expected_fixed_code_head=expected_fixed_code_head,
        expected_program_sha256=expected_scientific_program_sha256,
    )
    execution_sha = execution["manifest_sha256"]
    for name, digests in manifest_bindings.items():
        if name == "decision_rule":
            continue
        support_row = support_by_sha.get(digests["file_sha256"])
        if support_row is None:
            raise ValueError(f"execution-manifest artifact not bound: {name}")
        if support_row[1] != f"EXECUTION_BINDING:{name}":
            raise ValueError(f"execution binding role mismatch: {name}")

    decision_path, _ = _load_binding(
        root=root,
        value=value["decision_rule_binding"],
        support_by_sha=support_by_sha,
        expected_role="DECISION_RULE",
    )
    decision_rule = _canonical_json(decision_path)
    validated_rule = validate_decision_rule_v1(decision_rule)
    if validated_rule.stage != expected_stage:
        raise ValueError("authority decision-rule stage mismatch")
    if manifest_bindings["decision_rule"]["file_sha256"] != value["decision_rule_binding"]["sha256"]:
        raise ValueError("execution manifest/authority decision-rule file mismatch")
    if manifest_bindings["decision_rule"]["semantic_sha256"] != validated_rule.rule_sha256:
        raise ValueError("execution manifest/authority decision-rule semantic mismatch")

    cell_manifest_sha = manifest_bindings["cell_manifest"]["file_sha256"]
    cell_manifest_path = support_by_sha[cell_manifest_sha][0]
    cell_manifest_rows = _parse_jsonl(cell_manifest_path)
    registered_ids = []
    registered_by_id: dict[str, dict[str, object]] = {}
    for row in cell_manifest_rows:
        if set(row) != _CELL_MANIFEST_ROW_KEYS:
            raise ValueError("cell manifest row fields mismatch")
        cell_id = _text("cell_manifest.cell_id", row.get("cell_id"))
        _text("cell_manifest.comparison_group_id", row.get("comparison_group_id"))
        _text("cell_manifest.condition", row.get("condition"))
        if row.get("round_index") is not None and (type(row.get("round_index")) is not int or row.get("round_index") < 0):
            raise ValueError("cell manifest round_index invalid")
        if row.get("split") is not None:
            _text("cell_manifest.split", row.get("split"))
        _text("cell_manifest.task_id", row.get("task_id"))
        _text("cell_manifest.task_family", row.get("task_family"))
        if row.get("snapshot_sha256") is not None:
            require_lower_sha256("cell_manifest.snapshot_sha256", row.get("snapshot_sha256"))
        registered_ids.append(cell_id)
        registered_by_id[cell_id] = dict(row)
    if len(registered_ids) != len(set(registered_ids)):
        raise ValueError("registered cell IDs repeat")
    if len(registered_ids) != execution["registered_cell_count"]:
        raise ValueError("execution manifest/cell manifest count mismatch")

    if any(row["snapshot_sha256"] is None for row in cell_manifest_rows):
        raise ValueError("registered cells require snapshot identities")
    registered_snapshot_shas = {
        str(row["snapshot_sha256"])
        for row in cell_manifest_rows
    }
    if expected_stage == STAGE_2:
        registry_sha = manifest_bindings["snapshot_registry"]["file_sha256"]
        registry_path = support_by_sha[registry_sha][0]
        registry = _canonical_json(registry_path)
        registry_snapshot_shas = _collect_lower_sha256_strings(registry)
        if not registered_snapshot_shas.issubset(registry_snapshot_shas):
            raise ValueError("Stage 2 cell snapshot identity is absent from snapshot registry")
    else:
        expected_snapshot_sha = manifest_bindings["snapshot"]["semantic_sha256"]
        if registered_snapshot_shas != {expected_snapshot_sha}:
            raise ValueError("cell snapshot identity differs from execution snapshot binding")

    census_path, _ = _load_binding(
        root=root,
        value=value["cell_census_binding"],
        support_by_sha=support_by_sha,
        expected_role="CELL_CENSUS",
    )
    census = _canonical_json(census_path)
    _exact("cell census", census, _CENSUS_KEYS)
    if census["schema_id"] != "FAILURE_MEMORY_CELL_ARTIFACT_CENSUS_V1" or census["schema_version"] != 1:
        raise ValueError("cell census schema mismatch")
    if census["execution_manifest_sha256"] != execution_sha:
        raise ValueError("cell census execution-manifest binding mismatch")
    if census["registered_cell_count"] != len(registered_ids) or census["resolved_cell_count"] != len(registered_ids):
        raise ValueError("cell census counts mismatch")
    cells = census["cells"]
    if not isinstance(cells, list) or len(cells) != len(registered_ids):
        raise ValueError("cell census population mismatch")
    require_lower_sha256("census_sha256", census["census_sha256"])
    if census["census_sha256"] != _domain_sha(
        "FAILURE_MEMORY_CELL_ARTIFACT_CENSUS_V1", census, "census_sha256"
    ):
        raise ValueError("cell census self-hash mismatch")

    cell_results: list[dict[str, object]] = []
    observed_ids = []
    for row in cells:
        if not isinstance(row, dict):
            raise TypeError("cell census row must be object")
        _exact("cell census row", row, _CENSUS_ROW_KEYS)
        cell_id = _text("cell census cell_id", row["cell_id"])
        for name in (
            "receipt_file_sha256", "result_file_sha256",
            "receipt_sha256", "cell_result_sha256",
        ):
            require_lower_sha256(name, row[name])
        receipt_support = support_by_sha.get(row["receipt_file_sha256"])
        result_support = support_by_sha.get(row["result_file_sha256"])
        if receipt_support is None or receipt_support[1] != f"CELL_RECEIPT:{cell_id}":
            raise ValueError("cell receipt supporting artifact missing")
        if result_support is None or result_support[1] != f"CELL_RESULT:{cell_id}":
            raise ValueError("cell result supporting artifact missing")
        result = _canonical_json(result_support[0])
        validated = validate_cell_result_v1(
            result,
            expected_stage=expected_stage,
            expected_execution_manifest_sha256=execution["manifest_sha256"],
        )
        if validated["cell_id"] != cell_id or validated["cell_result_sha256"] != row["cell_result_sha256"]:
            raise ValueError("cell result/census identity mismatch")
        registered = registered_by_id[cell_id]
        for field in _CELL_MANIFEST_ROW_KEYS - {"cell_id"}:
            if validated[field] != registered[field]:
                raise ValueError(f"cell result differs from registered cell manifest: {cell_id}:{field}")
        receipt = _canonical_json(receipt_support[0])
        if receipt["receipt_sha256"] != row["receipt_sha256"]:
            raise ValueError("cell receipt/census semantic identity mismatch")
        _validate_receipt(
            receipt,
            cell_id=cell_id,
            execution_manifest_sha256=execution["manifest_sha256"],
            result_sha256=row["cell_result_sha256"],
        )
        observed_ids.append(cell_id)
        cell_results.append(validated)
    if sorted(observed_ids) != sorted(registered_ids):
        raise ValueError("resolved cell population differs from registered population")

    if value["registered_cell_count"] != len(registered_ids) or value["resolved_cell_count"] != len(registered_ids):
        raise ValueError("authority cell counts mismatch")
    if value["scientific_execution_complete"] is not True or value["method_frozen"] is not True:
        raise ValueError("authority is not complete and method-frozen")

    audits = value["audit_bindings"]
    if not isinstance(audits, dict) or set(audits) != _AUDIT_BINDING_KEYS:
        raise ValueError("audit binding population mismatch")
    audit_values: dict[str, dict[str, object]] = {}
    for name, binding in audits.items():
        path_value, _ = _load_binding(
            root=root,
            value=binding,
            support_by_sha=support_by_sha,
            expected_role=f"AUDIT:{name}",
        )
        audit = _canonical_json(path_value)
        if audit.get("status") != "PASS":
            raise ValueError(f"{name} audit did not pass")
        audit_values[name] = audit

    contamination_expected = {
        "status": "PASS",
        "same_round_memory_readback_count": sum(bool(r["same_round_memory_readback"]) for r in cell_results),
        "evaluation_writeback_attempt_count": sum(bool(r["evaluation_writeback_attempted"]) for r in cell_results),
        "unregistered_cell_count": 0,
    }
    for key, expected in contamination_expected.items():
        if audit_values["contamination"].get(key) != expected:
            raise ValueError("contamination audit is not independently supported")
    if contamination_expected["same_round_memory_readback_count"] != 0 or contamination_expected["evaluation_writeback_attempt_count"] != 0:
        raise ValueError("live stage contains prohibited readback/writeback")

    role_presence = {
        role: sum(r["role_pack_sha256s"][role] is not None for r in cell_results)
        for role in ("policy", "analyzer", "researcher")
    }
    if audit_values["role_pack"].get("role_pack_presence_counts") != role_presence:
        raise ValueError("role-pack audit is not independently supported")
    for cell in cell_results:
        cell_id = str(cell["cell_id"])
        for role in ("policy", "analyzer", "researcher"):
            digest = cell["role_pack_sha256s"][role]
            if digest is None:
                continue
            support_row = support_by_sha.get(digest)
            expected_role = f"ROLE_PACK:{role}:{cell_id}"
            if support_row is None or support_row[1] != expected_role:
                raise ValueError(
                    f"{role} Memory pack supporting artifact missing for cell {cell_id}"
                )
    for role in ("policy", "analyzer", "researcher"):
        if role_presence[role] < 1:
            raise ValueError(f"no {role} Memory pack is bound to the stage authority")

    round_summary: dict[str, list[str]] = {}
    if expected_stage == STAGE_2:
        for row in cell_results:
            round_summary.setdefault(str(row["round_index"]), []).append(str(row["snapshot_sha256"]))
        round_summary = {key: sorted(set(values)) for key, values in sorted(round_summary.items())}
        if any(len(values) != 1 for values in round_summary.values()):
            raise ValueError("Stage 2 round uses more than one active snapshot")
    if audit_values["round_governance"].get("round_snapshot_sha256s") != round_summary:
        raise ValueError("round-governance audit is not independently supported")

    recomputed = recompute_stage_decisions_v1(
        stage=expected_stage,
        cell_results=cell_results,
        decision_rule=decision_rule,
        execution_manifest_sha256=execution["manifest_sha256"],
    )
    independent = audit_values["independent_recomputation"]
    if independent.get("decision_sha256") != recomputed["decision_sha256"] or independent.get("cell_result_count") != len(cell_results):
        raise ValueError("independent recomputation audit mismatch")
    registered = value["registered_statistical_decision"]
    if registered != recomputed:
        raise ValueError("registered statistical decision differs from independent recomputation")
    if set(recomputed["question_decisions"]) != _STAGE_QUESTIONS[expected_stage]:
        raise ValueError("question decision population mismatch")

    boundaries = value["authority_boundaries"]
    if not isinstance(boundaries, dict) or set(boundaries) != _BOUNDARY_KEYS:
        raise ValueError("authority boundaries fields mismatch")
    if boundaries != {
        "analyzer_is_proposal_only": True,
        "verifier_is_effect_authority": True,
        "tests_are_not_scientific_evidence": True,
        "no_hidden_writeback": True,
        "researcher_is_read_only_evidence_consumer": True,
    }:
        raise ValueError("authority boundaries are not fail-closed")
    if not isinstance(value["result_payload"], dict):
        raise TypeError("result_payload must be object")

    require_lower_sha256("result_authority_sha256", value["result_authority_sha256"])
    expected_self = _domain_sha(
        "FAILURE_MEMORY_SCIENTIFIC_RESULT_AUTHORITY_V2",
        value,
        "result_authority_sha256",
    )
    if value["result_authority_sha256"] != expected_self:
        raise ValueError("scientific authority self-hash mismatch")
    return ValidatedScientificResultAuthorityV2(
        path=authority_path,
        file_sha256=sha256_bytes(authority_path.read_bytes()),
        stage=expected_stage,
        result_authority_sha256=value["result_authority_sha256"],
        question_decisions=recomputed["question_decisions"],
        effect_estimates=recomputed["effect_estimates"],
        result_payload=dict(value["result_payload"]),
    )
