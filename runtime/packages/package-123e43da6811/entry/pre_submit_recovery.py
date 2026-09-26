"""Append-only source replacement before the first scientific submission.

The caller must hold the ORIGINAL campaign owner lock while publishing and for
the whole successor resident lifetime. No old receipt or materialization changes.
"""
from pathlib import Path
import hashlib
import json


def _read_ref(ref,expected):
    path=Path(ref['path'])
    if path!=expected or any(p.is_symlink() for p in [path,*path.parents]) or not path.is_file():
        raise ValueError('PRE_SUBMIT_RECOVERY_EXACT_REF_REQUIRED')
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=ref['sha256']:
        raise ValueError('PRE_SUBMIT_RECOVERY_REF_CHANGED')
    return json.loads(raw)


def select_owner(*,bundle_root,formal_root,initial,authority,entry_source_sha256,publish=False):
    formal=Path(formal_root)
    old=formal/'campaign_owner'
    registration=Path(bundle_root)/'authority/PRE_SUBMIT_SOURCE_RECOVERY_V1.json'
    if not registration.is_file():
        return old
    raw=registration.read_bytes();proof=json.loads(raw)
    if (proof.get('schema_id')!='FORMAL_PRE_SUBMIT_SOURCE_RECOVERY_V1'
            or proof.get('predecessor_owner_root')!=str(old)
            or proof.get('request_sha256')!=initial['request_sha256']
            or len(entry_source_sha256)!=64
            or any(c not in '0123456789abcdef' for c in entry_source_sha256)):
        raise ValueError('PRE_SUBMIT_RECOVERY_AUTHORITY_INVALID')
    paths={'owner_binding':'OWNER_BINDING.json','intent':'attempts/000001/INTENT.json',
        'materialization':'attempts/000001/rollout/MATERIALIZED_ROLLOUT.json',
        'failure':'attempts/000001/rollout/RESIDENT_ROLLOUT_OPERATIONAL_STOP.json'}
    if set(proof['refs'])!=set(paths):
        raise ValueError('PRE_SUBMIT_RECOVERY_REF_SET_INVALID')
    values={key:_read_ref(proof['refs'][key],old/name) for key,name in paths.items()}
    binding=values['owner_binding'];intent=values['intent'];material=values['materialization'];failure=values['failure']
    predecessor=proof['predecessor_source_sha256']
    failure_rc=failure.get('preflight',{}).get('returncode')
    if (binding.get('initial')!=initial or binding.get('authority')!=authority
            or binding.get('native_driver_source_sha256')!=predecessor
            or intent.get('start')!=initial or intent.get('native_driver_source_sha256')!=predecessor
            or material.get('request_sha256')!=initial['request_sha256']
            or material.get('root')!=str(old/'attempts/000001/rollout')
            or failure.get('status')!='NATIVE_PREFLIGHT_FAILED'
            or type(failure_rc) is not int or failure_rc==0
            or entry_source_sha256==predecessor):
        raise ValueError('PRE_SUBMIT_RECOVERY_IDENTITY_OR_FAILURE_MISMATCH')
    # These are native stage contracts, not a search for assets or candidate paths.
    forbidden=['CAMPAIGN_TERMINAL.json','transitions','attempts/000001/RESULT.json',
        'attempts/000001/DRIVER_ROUND_RESULT.json','attempts/000001/analyzer',
        'attempts/000001/training','attempts/000001/offoff']
    forbidden += ['attempts/000001/rollout/'+name for name in (
        'SUBMISSION_INTENT.json','SUBMISSION_ATTEMPT.json','SUBMISSION_RECEIPT.json',
        'GATE_RELEASE_INTENT.json','GATE_RELEASE_RECEIPT.json',
        'round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json',
        'round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json')]
    for name in forbidden:
        p=old/name
        if p.exists() or p.is_symlink():
            raise ValueError('PRE_SUBMIT_RECOVERY_EXECUTION_TRACE_PRESENT:'+name)
    if {p.name for p in (old/'attempts').iterdir()}!={'000001'}:
        raise ValueError('PRE_SUBMIT_RECOVERY_UNEXPECTED_ATTEMPT')
    successor=old/'source_recoveries'/entry_source_sha256
    if any(p.is_symlink() for p in [successor,*successor.parents]):
        raise ValueError('PRE_SUBMIT_RECOVERY_SUCCESSOR_ALIAS_FORBIDDEN')
    delegation={'schema_id':'FORMAL_PRE_SUBMIT_SOURCE_DELEGATION_V1',
        'recovery_registration_sha256':hashlib.sha256(raw).hexdigest(),
        'predecessor_source_sha256':predecessor,'successor_source_sha256':entry_source_sha256,
        'predecessor_owner_root':str(old),'successor_owner_root':str(successor),
        'request_sha256':initial['request_sha256'],'valid_rounds_consumed_before_recovery':0,
        'scientific_submission_absence_checked':True,'historical_receipts_overwritten':False}
    delegation_path=old/'PRE_SUBMIT_SOURCE_RECOVERY.json'
    if delegation_path.is_symlink():
        raise ValueError('PRE_SUBMIT_RECOVERY_DELEGATION_ALIAS_FORBIDDEN')
    if delegation_path.exists() and json.loads(delegation_path.read_bytes())!=delegation:
        raise ValueError('PRE_SUBMIT_RECOVERY_ALREADY_DELEGATED_TO_ANOTHER_SOURCE')
    if publish:
        from entry.campaign_owner import _write_once
        _write_once(delegation_path,delegation)
    return successor
