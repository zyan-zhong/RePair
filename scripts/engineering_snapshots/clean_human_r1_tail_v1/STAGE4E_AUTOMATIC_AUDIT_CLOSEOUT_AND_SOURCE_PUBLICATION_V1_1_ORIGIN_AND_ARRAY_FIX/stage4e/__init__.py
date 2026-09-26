"""Small, outcome-gated adapters; scientific execution remains in existing code."""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path
from typing import Any

class GateError(ValueError):
    """A required frozen contract was not satisfied."""

def strict_loads(raw: str | bytes) -> Any:
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise GateError(f'DUPLICATE_JSON_KEY:{key}')
            out[key] = value
        return out
    def nonfinite(value):
        raise GateError(f'NONFINITE_JSON:{value}')
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=nonfinite)

def canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('utf-8')

def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()

def semantic_sha(value: Any) -> str:
    return sha(canonical(value))

def regular(path: Path) -> Path:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise GateError(f'NOT_REGULAR_FILE:{path}')
    return path

def read_json(path: Path) -> dict:
    value = strict_loads(regular(path).read_bytes())
    if not isinstance(value, dict):
        raise GateError(f'JSON_OBJECT_REQUIRED:{path}')
    return value

def file_sha(path: Path) -> str:
    h = hashlib.sha256()
    with regular(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def require_file_sha(path: Path, expected: str) -> None:
    observed = file_sha(path)
    if observed != expected:
        raise GateError(f'FILE_SHA_MISMATCH:{path}:expected={expected}:observed={observed}')

def write_bytes_exact(path: Path, raw: bytes) -> None:
    path = Path(path)
    if path.is_symlink():
        raise GateError(f'SYMLINK_OUTPUT:{path}')
    if path.exists():
        if regular(path).read_bytes() != raw:
            raise GateError(f'EXISTING_OUTPUT_CHANGED:{path}')
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError:
        if regular(path).read_bytes() != raw:
            raise GateError(f'CONCURRENT_OUTPUT_CONFLICT:{path}')
        return
    try:
        view = memoryview(raw)
        while view:
            n = os.write(fd, view)
            if n <= 0:
                raise OSError('short write')
            view = view[n:]
        os.fsync(fd)
    finally:
        os.close(fd)

def write_exact(path: Path, value: Any) -> None:
    write_bytes_exact(path, canonical(value) + b'\n')

def safe_child(root: Path, name: str) -> Path:
    rel = Path(name)
    if rel.is_absolute() or '..' in rel.parts or not rel.parts:
        raise GateError(f'UNSAFE_RELATIVE_PATH:{name}')
    path = root
    for part in rel.parts:
        path = path / part
        if path.is_symlink():
            raise GateError(f'SYMLINK_INPUT_COMPONENT:{path}')
    return path

def verify_inventory(root: Path, manifest: str = 'PACKAGE_FILES.sha256') -> dict[str,str]:
    result = {}
    for line in regular(root / manifest).read_text(encoding='utf-8').splitlines():
        if not line:
            continue
        if '  ' not in line:
            raise GateError('MALFORMED_FILE_INVENTORY')
        digest, name = line.split('  ', 1)
        if name in result or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            raise GateError('INVALID_FILE_INVENTORY_ENTRY')
        require_file_sha(safe_child(root, name), digest)
        result[name] = digest
    if not result:
        raise GateError('EMPTY_FILE_INVENTORY')
    return result

def validate_completion(value: dict, *, auth_sha: str, binding_sha: str, readiness_sha: str, pair_count: int) -> None:
    required = {
        'schema_id': 'STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1',
        'schema_version': 1,
        'authorization_sha256': auth_sha,
        'binding_sha256': binding_sha,
        'readiness_receipt_sha256': readiness_sha,
        'scientific_execution_complete': True,
        't0_condition_cell_count': pair_count,
        't2_condition_cell_count': pair_count,
        'paired_task_seed_cell_count': pair_count,
        'total_condition_cell_count': 2 * pair_count,
        'result_interpretation_authorized': False,
        'promotion_authorized': False,
        'next_gate': 'STAGE4E_EXISTING_SELECT_RESULT_AUDIT',
    }
    for key, expected in required.items():
        if type(value.get(key)) is not type(expected) or value.get(key) != expected:
            raise GateError(f'COMPLETION_CONTRACT_MISMATCH:{key}')

def project_paired_summary(results: dict, *, round_id: str, evidence_sha: str) -> dict:
    fields = (
        'unique_task_count', 'replicate_seeds', 'paired_cell_count', 'total_condition_cell_count',
        'parent_success_cells', 'candidate_success_cells', 'both_success_cells', 'both_failure_cells',
        'parent_only_success_cells', 'candidate_only_success_cells', 'mean_task_success_rate_delta',
    )
    if any(key not in results for key in fields):
        raise GateError('PAIRED_AGGREGATE_INCOMPLETE')
    out = {key: results[key] for key in fields}
    out.update({
        'schema_id': 'CLEAN_TRAIN_SELECT_AGGREGATE_V1', 'schema_version': 1,
        'round_id': round_id, 'source_audit_sha256': evidence_sha,
        'primary_statistical_unit': 'unique_task', 'seed_replicates_are_not_independent_tasks': True,
        'access_class': 'TRAIN_SELECT_AGGREGATE_ONLY', 'diagnostic_only': True,
        'promotion_eligible': False, 'confirmatory_claim_authorized': False,
        'per_task_evidence_included': False,
        'interpretation': 'DIAGNOSTIC_SELECTED_PORTFOLIO_T2_NOT_VERIFIED_REPAIR_EFFICACY',
        'statistical_significance_evaluated': False,
    })
    return out

def diagnostic_disposition(*, protocol: dict, candidate: dict, delta: float) -> dict:
    if (protocol.get('promotion_eligible') is not False
            or candidate.get('promotion_eligible') is not False
            or candidate.get('run_manifest', {}).get('promotion_eligible') is not False
            or candidate.get('run_manifest', {}).get('diagnostic_only') is not True):
        raise GateError('DIAGNOSTIC_SCOPE_CHANGED_NO_GENERIC_PROMOTION_RULE_INVENTED')
    return {
        'decision': 'ROLLBACK',
        'reason': 'PREREGISTERED_DIAGNOSTIC_NOT_PROMOTION_ELIGIBLE',
        'performance_based_promotion': False,
        'observed_direction': 'POSITIVE' if delta > 0 else ('NEGATIVE' if delta < 0 else 'ZERO'),
        'meaning': 'RETAIN_PARENT_NOT_A_STATISTICAL_NO_GO_JUDGMENT',
    }

def next_operation(*, state: str, completion_present: bool, graceful_partial: bool, resume_count: int, max_resumptions: int) -> str:
    if state in {'PENDING','RUNNING','COMPLETING','CONFIGURING','SUSPENDED','REQUEUED','RESIZING'}:
        return 'WAIT'
    if state != 'COMPLETED':
        return 'STOP'
    if completion_present:
        return 'AUDIT'
    if graceful_partial and resume_count < max_resumptions:
        return 'RESUME_EXISTING'
    return 'STOP'
