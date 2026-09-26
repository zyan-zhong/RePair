#!/usr/bin/env python3
"""Supplemental AST/data-flow audit for task-access SHA no-fallback."""

from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import sys


class NoFallbackAuditError(RuntimeError):
    pass


HISTORICAL_FIELD = "historical_design_candidate_sha256"
EXACT_FIELD = "approved_exact_contract_protected_sha256"


def _function(tree: ast.AST, name: str) -> ast.FunctionDef:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == name
    ]
    if len(matches) != 1:
        raise NoFallbackAuditError(
            f"FUNCTION_{name.upper()}_COUNT_INVALID"
        )
    return matches[0]


def _class(tree: ast.AST, name: str) -> ast.ClassDef:
    matches = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name == name
    ]
    if len(matches) != 1:
        raise NoFallbackAuditError(
            f"CLASS_{name.upper()}_COUNT_INVALID"
        )
    return matches[0]


def _contains_token(node: ast.AST, token: str) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and child.id == token:
            return True
        if isinstance(child, ast.Attribute) and child.attr == token:
            return True
        if (
            isinstance(child, ast.Constant)
            and child.value == token
        ):
            return True
        if isinstance(child, ast.Subscript):
            key = child.slice
            if (
                isinstance(key, ast.Constant)
                and key.value == token
            ):
                return True
    return False


def _is_authority_attr(node: ast.AST, field: str) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == field
        and isinstance(node.value, ast.Name)
        and node.value.id == "authority"
    )


def _raise_codes(node: ast.AST) -> set[str]:
    result: set[str] = set()
    for child in ast.walk(node):
        if not isinstance(child, ast.Raise):
            continue
        exc = child.exc
        if not isinstance(exc, ast.Call):
            continue
        if not (
            isinstance(exc.func, ast.Name)
            and exc.func.id == "TaskAccessMaterializationError"
        ):
            continue
        if (
            exc.args
            and isinstance(exc.args[0], ast.Constant)
            and isinstance(exc.args[0].value, str)
        ):
            result.add(exc.args[0].value)
    return result


def _receipt_dict(function: ast.FunctionDef) -> ast.Dict:
    matches: list[ast.Dict] = []
    for child in ast.walk(function):
        if not isinstance(child, ast.Assign):
            continue
        if len(child.targets) != 1:
            continue
        target = child.targets[0]
        if (
            isinstance(target, ast.Name)
            and target.id == "receipt_payload"
            and isinstance(child.value, ast.Dict)
        ):
            matches.append(child.value)

    if len(matches) != 1:
        raise NoFallbackAuditError(
            "RECEIPT_PAYLOAD_ASSIGNMENT_COUNT_INVALID"
        )
    return matches[0]


def _dict_map(node: ast.Dict) -> dict[str, ast.AST]:
    result: dict[str, ast.AST] = {}
    for key, value in zip(node.keys, node.values):
        if (
            isinstance(key, ast.Constant)
            and isinstance(key.value, str)
        ):
            if key.value in result:
                raise NoFallbackAuditError(
                    "RECEIPT_DUPLICATE_KEY"
                )
            result[key.value] = value
    return result


def _audit_loader(loader: ast.FunctionDef) -> None:
    v1_reject = False

    for child in ast.walk(loader):
        if isinstance(child, ast.If):
            if (
                _contains_token(child.test, "CONFIG_SCHEMA_V1")
                and "AUTHORITY_CONFIG_V1_REJECTED"
                in _raise_codes(child)
            ):
                v1_reject = True

        if (
            isinstance(child, ast.BoolOp)
            and isinstance(child.op, ast.Or)
            and (
                _contains_token(child, HISTORICAL_FIELD)
                or _contains_token(child, EXACT_FIELD)
            )
        ):
            raise NoFallbackAuditError(
                "AUTHORITY_FALLBACK_OR_FORBIDDEN"
            )

        if (
            isinstance(child, ast.IfExp)
            and (
                _contains_token(child, HISTORICAL_FIELD)
                or _contains_token(child, EXACT_FIELD)
            )
        ):
            raise NoFallbackAuditError(
                "AUTHORITY_CONDITIONAL_FALLBACK_FORBIDDEN"
            )

        if isinstance(child, ast.Call):
            func = child.func
            if (
                isinstance(func, ast.Attribute)
                and func.attr == "get"
                and isinstance(func.value, ast.Name)
                and func.value.id == "payload"
                and (
                    any(
                        _contains_token(arg, HISTORICAL_FIELD)
                        for arg in child.args
                    )
                    or any(
                        _contains_token(arg, EXACT_FIELD)
                        for arg in child.args
                    )
                )
            ):
                raise NoFallbackAuditError(
                    "AUTHORITY_DEFAULTING_GET_FORBIDDEN"
                )

    if not v1_reject:
        raise NoFallbackAuditError(
            "V1_CONFIG_REJECTION_MISSING"
        )


def _audit_distinct_guard(authority_class: ast.ClassDef) -> None:
    post_init = next(
        (
            child
            for child in authority_class.body
            if isinstance(child, ast.FunctionDef)
            and child.name == "__post_init__"
        ),
        None,
    )
    if post_init is None:
        raise NoFallbackAuditError(
            "AUTHORITY_V2_POST_INIT_MISSING"
        )

    for child in ast.walk(post_init):
        if (
            isinstance(child, ast.If)
            and _contains_token(child.test, HISTORICAL_FIELD)
            and _contains_token(child.test, EXACT_FIELD)
            and "CORRECTION_V1_DIGESTS_MUST_DIFFER"
            in _raise_codes(child)
        ):
            return

    raise NoFallbackAuditError(
        "CORRECTION_V1_DISTINCT_DIGEST_GUARD_MISSING"
    )


def _audit_materialization(function: ast.FunctionDef) -> None:
    for child in ast.walk(function):
        if (
            isinstance(child, ast.BoolOp)
            and isinstance(child.op, ast.Or)
            and (
                _contains_token(child, HISTORICAL_FIELD)
                or _contains_token(child, EXACT_FIELD)
            )
        ):
            raise NoFallbackAuditError(
                "AUTHORITY_FALLBACK_OR_FORBIDDEN"
            )

        if (
            isinstance(child, ast.IfExp)
            and (
                _contains_token(child, HISTORICAL_FIELD)
                or _contains_token(child, EXACT_FIELD)
            )
        ):
            raise NoFallbackAuditError(
                "AUTHORITY_CONDITIONAL_FALLBACK_FORBIDDEN"
            )

    compares = [
        child
        for child in ast.walk(function)
        if isinstance(child, ast.Compare)
        and _contains_token(child, "protected_sha256")
    ]

    if len(compares) != 1:
        raise NoFallbackAuditError(
            "PROTECTED_ADMISSION_COMPARISON_COUNT_INVALID"
        )

    gate = compares[0]

    if _contains_token(gate, HISTORICAL_FIELD):
        raise NoFallbackAuditError(
            "HISTORICAL_FIELD_IN_ADMISSION_COMPARISON"
        )

    if not _contains_token(gate, EXACT_FIELD):
        raise NoFallbackAuditError(
            "EXACT_FIELD_MISSING_FROM_ADMISSION_COMPARISON"
        )

    historical_attrs = [
        child
        for child in ast.walk(function)
        if isinstance(child, ast.Attribute)
        and child.attr == HISTORICAL_FIELD
    ]
    if len(historical_attrs) != 1:
        raise NoFallbackAuditError(
            "HISTORICAL_FIELD_OUTSIDE_PROVENANCE_RECEIPT"
        )

    receipt = _dict_map(_receipt_dict(function))

    for key in (
        HISTORICAL_FIELD,
        EXACT_FIELD,
        "protected_regeneration_sha256",
    ):
        if key not in receipt:
            raise NoFallbackAuditError(
                "RECEIPT_AUTHORITY_BINDINGS_MISSING"
            )

    if not _is_authority_attr(
        receipt[HISTORICAL_FIELD],
        HISTORICAL_FIELD,
    ):
        raise NoFallbackAuditError(
            "RECEIPT_HISTORICAL_PROVENANCE_BINDING_INVALID"
        )

    if not _is_authority_attr(
        receipt[EXACT_FIELD],
        EXACT_FIELD,
    ):
        raise NoFallbackAuditError(
            "RECEIPT_EXACT_AUTHORITY_BINDING_INVALID"
        )

    protected = receipt["protected_regeneration_sha256"]
    if not (
        isinstance(protected, ast.Name)
        and protected.id == "protected_sha256"
    ):
        raise NoFallbackAuditError(
            "RECEIPT_PROTECTED_DIGEST_NOT_GENERATED_DIGEST"
        )


def audit_materializer(path: Path) -> dict[str, object]:
    try:
        source = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise NoFallbackAuditError(
            "MATERIALIZER_UNREADABLE"
        ) from exc

    if "TaskAccessMaterializationAuthorityV1" in source:
        raise NoFallbackAuditError(
            "V1_AUTHORITY_CLASS_REFERENCE_PRESENT"
        )
    if "approved_v2_1_manifest_sha256" in source:
        raise NoFallbackAuditError(
            "OLD_EXECUTION_AUTHORITY_FIELD_PRESENT"
        )

    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise NoFallbackAuditError(
            "MATERIALIZER_AST_PARSE_FAILED"
        ) from exc

    loader = _function(tree, "load_real_authority_config")
    materialize = _function(tree, "materialize_task_access")
    authority_class = _class(
        tree,
        "TaskAccessMaterializationAuthorityV2",
    )

    _audit_loader(loader)
    _audit_distinct_guard(authority_class)
    _audit_materialization(materialize)

    return {
        "schema": "TASK_ACCESS_SHA_AUTHORITY_NO_FALLBACK_AUDIT_V1",
        "materializer_sha256": hashlib.sha256(
            source.encode("utf-8")
        ).hexdigest(),
        "v1_execution_config_rejected": True,
        "historical_candidate_execution_gate_uses": 0,
        "exact_contract_is_protected_admission_gate": True,
        "fallback_or_defaulting_detected": False,
        "receipt_generated_digest_binding_verified": True,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--materializer",
        required=True,
        type=Path,
    )
    args = parser.parse_args(argv)

    try:
        report = audit_materializer(args.materializer)
    except NoFallbackAuditError as exc:
        print(
            "TASK_ACCESS_SHA_AUTHORITY_NO_FALLBACK_AUDIT_STOP="
            + str(exc),
            file=sys.stderr,
        )
        return 2

    print(
        "TASK_ACCESS_SHA_AUTHORITY_NO_FALLBACK_AUDIT_PASS"
    )
    for key in (
        "materializer_sha256",
        "v1_execution_config_rejected",
        "historical_candidate_execution_gate_uses",
        "exact_contract_is_protected_admission_gate",
        "fallback_or_defaulting_detected",
        "receipt_generated_digest_binding_verified",
    ):
        value = report[key]
        if isinstance(value, bool):
            value = str(value).lower()
        print(f"{key}={value}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
