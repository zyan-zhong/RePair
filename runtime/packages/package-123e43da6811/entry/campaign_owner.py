"""Receipt-driven campaign ownership; scientific work remains in native drivers.

This module does not decide repair eligibility, training labels or promotion.
It consumes validated native outcomes and delegates counters/stopping to the
captured/current pchsi governor. Installing this module alone does NOT constitute
production readiness: a source-sealed native driver must also be linked.
"""
from __future__ import annotations

from contextlib import contextmanager
from dataclasses import fields
import errno
import fcntl
import hashlib
import json
import os
from pathlib import Path
from typing import Any, Protocol

from pchsi.round_control.campaign_authority import CampaignStartupAuthorityV1
from pchsi.round_control.rollout_collection import RoundRolloutCollectionRequestV1
from pchsi.round_control.scientific_round_governance import (
    advance_scientific_round_governance, new_scientific_round_governance,
)


class EntryError(RuntimeError):
    """A typed operational stop; it never asks a human for a scientific decision."""


class NativeRoundDriver(Protocol):
    source_identity_sha256: str
    def preflight(self) -> None: ...
    def execute_round(self, start: dict[str, Any], attempt_root: Path) -> dict[str, Any]: ...
    def recover_round(self, start: dict[str, Any], attempt_root: Path) -> dict[str, Any] | None: ...
    def validate_result(self, start: dict[str, Any], result: dict[str, Any]) -> None: ...
    def build_next(self, start: dict[str, Any], result: dict[str, Any], governance: Any) -> dict[str, Any]: ...


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':'), allow_nan=False).encode('utf-8')


def _digest(value: Any) -> str:
    return hashlib.sha256(b'FORMAL_CAMPAIGN_OWNER_OPERATIONAL_V1\0' + _canonical(value)).hexdigest()


def _sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for data in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(data)
    return h.hexdigest()


def _hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or len(value) != 64 or any(c not in '0123456789abcdef' for c in value):
        raise EntryError('SHA256_REQUIRED:' + label)
    return value


def _pairs(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise EntryError('DUPLICATE_JSON_KEY:' + key)
        value[key] = item
    return value


def _read(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise EntryError('REGULAR_RECEIPT_REQUIRED:' + str(path))
    def bad_constant(value):
        raise EntryError('NONFINITE_JSON:' + value)
    obj = json.loads(path.read_text(encoding='utf-8'), object_pairs_hook=_pairs,
                     parse_constant=bad_constant)
    if not isinstance(obj, dict):
        raise EntryError('OBJECT_RECEIPT_REQUIRED:' + str(path))
    return obj


def _sync_dir(path: Path):
    fd = os.open(path, os.O_RDONLY | getattr(os, 'O_DIRECTORY', 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def _write_once(path: Path, obj: dict) -> None:
    """Publish a fully fsynced file using link/no-overwrite semantics.

    A process crash may leave a temporary file, never an authoritative truncated
    JSON. Existing receipts may be adopted only when bytes are exactly equal.
    """
    raw = _canonical(obj) + b'\n'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.is_symlink() or path.read_bytes() != raw:
            raise EntryError('IMMUTABLE_RECEIPT_CONFLICT:' + str(path))
        return
    import tempfile
    fd, temporary = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    tmp = Path(temporary)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(tmp, path)
            _sync_dir(path.parent)
        except FileExistsError:
            if path.is_symlink() or path.read_bytes() != raw:
                raise EntryError('IMMUTABLE_RECEIPT_CONFLICT:' + str(path))
    finally:
        tmp.unlink(missing_ok=True)


@contextmanager
def campaign_lock(root: Path):
    root.mkdir(parents=True, exist_ok=True)
    lock_path = root / '.campaign_writer.lock'
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, 'O_NOFOLLOW', 0), 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EACCES):
                raise EntryError('CAMPAIGN_WRITER_ALREADY_ACTIVE') from exc
            raise
        yield
    finally:
        # Unlock affects this open-file description only.
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def _check_driver(driver):
    names = ('preflight', 'execute_round', 'recover_round', 'validate_result', 'build_next')
    missing = [name for name in names if not callable(getattr(driver, name, None))]
    if missing:
        raise EntryError('NATIVE_DRIVER_INTERFACE_INCOMPLETE:' + ','.join(missing))
    _hex(getattr(driver, 'source_identity_sha256', None), 'native_driver_identity')


def _check_start(start: dict):
    if not isinstance(start, dict):
        raise EntryError('NATIVE_ROUND_REQUEST_INVALID:OBJECT_REQUIRED')
    try:
        native = RoundRolloutCollectionRequestV1(
            **{f.name:start[f.name] for f in fields(RoundRolloutCollectionRequestV1)}
        )
        if native.to_dict() != start:
            raise ValueError('native serialization/key-set mismatch')
    except (KeyError, ValueError, TypeError) as exc:
        raise EntryError('NATIVE_ROUND_REQUEST_INVALID:' + str(exc)) from exc
    _canonical(start)


def _check_result(start: dict, result: dict, driver):
    if not isinstance(result, dict):
        raise EntryError('NATIVE_RESULT_MUST_BE_OBJECT')
    for name in ('round_id','execution_attempt_id','request_sha256','parent_policy_id',
                 'parent_policy_artifact_sha256','round_start_memory_snapshot_sha256'):
        if result.get(name) != start[name]:
            raise EntryError('NATIVE_RESULT_START_IDENTITY_MISMATCH:' + name)
    if type(result.get('human_scientific_decision_count')) is not int or result['human_scientific_decision_count'] != 0:
        raise EntryError('HUMAN_SCIENTIFIC_DECISION_FORBIDDEN')
    if result.get('benchmark_feedback_used') is not False:
        raise EntryError('BENCHMARK_FEEDBACK_FORBIDDEN')
    if result.get('invalid_attempt_adaptive_evidence_reuse') is not False:
        raise EntryError('INVALID_ATTEMPT_EVIDENCE_REUSE_FORBIDDEN')
    outcome = result.get('outcome')
    if outcome not in {'PROMOTED','ROLLED_BACK','NO_TRAINING_UPDATE','PROTOCOL_INFRA_INVALID'}:
        raise EntryError('NATIVE_OUTCOME_NOT_SUPPORTED')
    next_id = result.get('next_parent_policy_id')
    if not isinstance(next_id, str) or not next_id:
        raise EntryError('NEXT_PARENT_IDENTITY_MISSING')
    _hex(result.get('next_parent_policy_artifact_sha256'), 'next_parent_policy_artifact_sha256')
    if outcome != 'PROMOTED' and (
        next_id != start['parent_policy_id'] or
        result['next_parent_policy_artifact_sha256'] != start['parent_policy_artifact_sha256']
    ):
        raise EntryError('PARENT_CHANGED_WITHOUT_PROMOTION')
    if outcome == 'PROMOTED' and result['next_parent_policy_artifact_sha256'] == start['parent_policy_artifact_sha256']:
        raise EntryError('PROMOTION_WITH_UNCHANGED_POLICY_ARTIFACT')
    ref = result.get('terminal_ref')
    if not isinstance(ref, dict) or not isinstance(ref.get('path'), str):
        raise EntryError('NATIVE_TERMINAL_REF_MISSING')
    path = Path(ref['path'])
    _hex(ref.get('sha256'), 'terminal_ref.sha256')
    if not path.is_absolute() or path.is_symlink() or not path.is_file() or _sha(path) != ref['sha256']:
        raise EntryError('NATIVE_TERMINAL_REF_INTEGRITY_FAILED')
    # Semantic eligibility, verifier/PRE/POST lineage, native-label gate, checkpoint
    # reload and OFF/OFF acceptance are checked by the linked native driver.
    driver.validate_result(dict(start), dict(result))


def _check_next(start: dict, result: dict, nxt: dict):
    _check_start(nxt)
    if nxt['request_sha256'] == start['request_sha256']:
        raise EntryError('NEXT_REQUEST_NOT_FRESH')
    if result['outcome'] == 'PROTOCOL_INFRA_INVALID':
        mutable = {'execution_attempt_id', 'request_sha256'}
        if {k:v for k,v in start.items() if k not in mutable} != {k:v for k,v in nxt.items() if k not in mutable}:
            raise EntryError('INFRA_RETRY_CHANGED_SCIENTIFIC_START')
        if nxt['execution_attempt_id'] == start['execution_attempt_id']:
            raise EntryError('INFRA_RETRY_ATTEMPT_ID_NOT_FRESH')
    else:
        if nxt['round_id'] == start['round_id']:
            raise EntryError('NEXT_ROUND_ID_NOT_FRESH')
        if nxt['parent_policy_id'] != result['next_parent_policy_id'] or nxt['parent_policy_artifact_sha256'] != result['next_parent_policy_artifact_sha256']:
            raise EntryError('NEXT_ROUND_PARENT_AUTHORITY_MISMATCH')


def _transition(*, state, start, result, retry_used):
    nxt_state = advance_scientific_round_governance(state, outcome=result['outcome'])
    stop_reason = nxt_state.stop_reason if nxt_state.stop else None
    next_retry = retry_used
    if result['outcome'] == 'PROTOCOL_INFRA_INVALID':
        if result.get('retry_class') not in {'SAFE_PRE_SEND','SAFE_PROVIDER_REJECTION','SAFE_LOCAL_RESOURCE_ISOLATION'}:
            stop_reason = 'INFRASTRUCTURE_RETRY_NOT_AUTHORIZED_NO_BLIND_RESEND'
        elif retry_used >= state.max_infrastructure_attempt_restarts:
            stop_reason = 'INFRASTRUCTURE_RESTART_BUDGET_EXHAUSTED'
        else:
            next_retry = retry_used + 1
    else:
        next_retry = 0
    return nxt_state, next_retry, stop_reason


def run_campaign(*, state_root: Path, authority: CampaignStartupAuthorityV1,
                 initial: dict, driver: NativeRoundDriver) -> dict:
    """Run/recover a campaign. Unit-test success is not a production release.

    The native driver must be source-sealed and release-approved by the caller.
    A STARTED operation without an adoptable native terminal is never re-executed.
    Only its already-written terminal can be adopted after restart.
    """
    _check_driver(driver)
    _check_start(initial)
    if not isinstance(authority, CampaignStartupAuthorityV1):
        raise EntryError('NATIVE_CAMPAIGN_AUTHORITY_REQUIRED')
    # Reconstruct with the native validator to reject a tampered dataclass instance.
    authority = CampaignStartupAuthorityV1.from_dict(authority.to_dict())
    root = Path(state_root).resolve()
    with campaign_lock(root):
        driver.preflight()
        binding = {'schema_id':'FORMAL_CAMPAIGN_OWNER_BINDING_V1',
                   'authority':authority.to_dict(), 'initial':initial,
                   'native_driver_source_sha256':driver.source_identity_sha256}
        _write_once(root/'OWNER_BINDING.json', binding)
        state = new_scientific_round_governance(authority=authority)
        start = dict(initial)
        retries = 0
        previous = _digest(binding)
        ordinal = 0
        stop_reason = None
        history = sorted((root/'transitions').glob('*.json')) if (root/'transitions').exists() else []
        for ordinal, path in enumerate(history, start=1):
            if path.name != f'{ordinal:06d}.json':
                raise EntryError('TRANSITION_SEQUENCE_GAP')
            event = _read(path)
            event_hash = event.get('event_sha256')
            payload = {k:v for k,v in event.items() if k != 'event_sha256'}
            if event_hash != _digest(payload) or payload.get('previous_event_sha256') != previous:
                raise EntryError('TRANSITION_HASH_CHAIN_INVALID')
            if payload.get('start') != start or payload.get('governance_before') != state.to_dict():
                raise EntryError('TRANSITION_START_OR_GOVERNANCE_DRIFT')
            expected_intent = {'schema_id':'FORMAL_CAMPAIGN_OWNER_ROUND_INTENT_V1','start':start,
                               'previous_event_sha256':previous,
                               'native_driver_source_sha256':driver.source_identity_sha256}
            intent_path = root/'attempts'/f'{ordinal:06d}'/'INTENT.json'
            if not intent_path.is_file() or _read(intent_path) != expected_intent:
                raise EntryError('TRANSITION_OWNER_INTENT_MISSING_OR_MISMATCH')
            result = _read(root/'attempts'/f'{ordinal:06d}'/'RESULT.json')
            if _digest(result) != payload.get('result_sha256'):
                raise EntryError('TRANSITION_RESULT_HASH_MISMATCH')
            _check_result(start,result,driver)
            new_state, next_retries, expected_stop = _transition(state=state,start=start,result=result,retry_used=retries)
            if payload.get('governance_after') != new_state.to_dict() or payload.get('stop_reason') != expected_stop or payload.get('restarts_used_after') != next_retries:
                raise EntryError('TRANSITION_NATIVE_GOVERNANCE_REPLAY_MISMATCH')
            nxt = payload.get('next_start')
            if expected_stop is None:
                _check_next(start,result,nxt)
                start = nxt
            elif nxt is not None:
                raise EntryError('STOP_TRANSITION_CANNOT_START_NEXT_ROUND')
            if stop_reason is not None:
                raise EntryError('EVENT_AFTER_TERMINAL_STOP')
            state, retries, previous, stop_reason = new_state, next_retries, event_hash, expected_stop
        if (root/'CAMPAIGN_TERMINAL.json').exists() and stop_reason is None:
            raise EntryError('TERMINAL_WITHOUT_STOP_TRANSITION')
        from .progress import update
        update(root,stage='STARTING',valid_rounds=state.valid_rounds_consumed,
               max_rounds=state.max_valid_rounds,invalid_attempts=state.invalid_attempt_count)
        while stop_reason is None:
            ordinal += 1
            attempt = root/'attempts'/f'{ordinal:06d}'
            attempt.mkdir(parents=True,exist_ok=True)
            intent = {'schema_id':'FORMAL_CAMPAIGN_OWNER_ROUND_INTENT_V1','start':start,
                      'previous_event_sha256':previous,'native_driver_source_sha256':driver.source_identity_sha256}
            intent_path = attempt/'INTENT.json'
            existed = intent_path.exists()
            if not existed and (attempt/'RESULT.json').exists():
                raise EntryError('RESULT_WITHOUT_OWNER_INTENT')
            _write_once(intent_path,intent)
            if (attempt/'RESULT.json').exists():
                result = _read(attempt/'RESULT.json')
            elif existed:
                result = driver.recover_round(dict(start),attempt)
                if result is None:
                    raise EntryError('AMBIGUOUS_STARTED_WITHOUT_TERMINAL_NO_BLIND_RESEND')
            else:
                result = driver.execute_round(dict(start),attempt)
            _check_result(start,result,driver)
            _write_once(attempt/'RESULT.json',result)
            if callable(getattr(driver,'export_result',None)):
                driver.export_result(start,result,attempt)
            new_state,next_retries,stop_reason = _transition(state=state,start=start,result=result,retry_used=retries)
            nxt = None
            if stop_reason is None:
                nxt = driver.build_next(dict(start),dict(result),new_state)
                _check_next(start,result,nxt)
            payload = {'schema_id':'FORMAL_CAMPAIGN_OWNER_TRANSITION_V1',
                       'ordinal':ordinal,'previous_event_sha256':previous,
                       'governance_before':state.to_dict(),'governance_after':new_state.to_dict(),
                       'start':start,'result_sha256':_digest(result),'next_start':nxt,
                       'restarts_used_after':next_retries,'stop_reason':stop_reason}
            previous = _digest(payload)
            _write_once(root/'transitions'/f'{ordinal:06d}.json',dict(payload,event_sha256=previous))
            state,retries = new_state,next_retries
            update(root,stage=('NEXT_ATTEMPT' if stop_reason is None else
                              'STOPPED' if result['outcome']=='PROTOCOL_INFRA_INVALID' else 'COMPLETED'),
                   valid_rounds=state.valid_rounds_consumed,max_rounds=state.max_valid_rounds,
                   invalid_attempts=state.invalid_attempt_count,last_outcome=result['outcome'],
                   stop_reason=stop_reason)
            if nxt is not None:
                start = nxt
        terminal = {'schema_id':'FORMAL_CAMPAIGN_OWNER_TERMINAL_V1',
                    'stop_reason':stop_reason,'governance':state.to_dict(),
                    'last_event_sha256':previous,'native_driver_source_sha256':driver.source_identity_sha256,
                    'human_scientific_decision_count':0}
        _write_once(root/'CAMPAIGN_TERMINAL.json',terminal)
        return terminal
