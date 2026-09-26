"""One SHA-registered source replacement after a fully terminal invalid rollout."""
from pathlib import Path
from rollout_adapter.materializer import obj, ref, canonical, put, no_symlink_ancestors


def registration(bundle_root):
    path=Path(bundle_root)/'authority/POST_SUBMIT_SOURCE_RECOVERY_V1.json'
    return obj(ref(path)) if path.is_file() else None


def select_owner(*,bundle_root,formal_root,initial,authority,entry_source_sha256,publish=False):
    proof=registration(bundle_root)
    if proof is None:
        from .pre_submit_recovery import select_owner as original
        return original(bundle_root=bundle_root,formal_root=formal_root,initial=initial,
            authority=authority,entry_source_sha256=entry_source_sha256,publish=publish)
    base=Path(formal_root)/'campaign_owner'
    old=no_symlink_ancestors(proof['predecessor_owner_root'])
    if (proof['schema_id']!='FORMAL_POST_SUBMIT_INVALID_ROLLOUT_SOURCE_RECOVERY_V1'
            or old!=base/'source_recoveries'/proof['predecessor_source_sha256']
            or proof['initial_request_sha256']!=initial['request_sha256']
            or len(entry_source_sha256)!=64
            or any(c not in '0123456789abcdef' for c in entry_source_sha256)):
        raise ValueError('POST_SUBMIT_RECOVERY_REGISTERED_OWNER_REQUIRED')
    expected={'original_delegation':base/'PRE_SUBMIT_SOURCE_RECOVERY.json',
        'owner_binding':old/'OWNER_BINDING.json','intent':old/'attempts/000001/INTENT.json',
        'manifest':old/'attempts/000001/rollout/MATERIALIZED_ROLLOUT.json',
        'submission':old/'attempts/000001/rollout/SUBMISSION_RECEIPT.json',
        'failure':old/'attempts/000001/rollout/RESIDENT_ROLLOUT_OPERATIONAL_STOP.json',
        'terminal':old/'attempts/000001/rollout/round_evidence/PCHSI_V1232K_GLOBAL_TERMINAL_V1.json',
        'handoff':old/'attempts/000001/rollout/round_evidence/ROUND_ROLLOUT_EVIDENCE_HANDOFF_V1.json'}
    if set(proof['refs'])!=set(expected): raise ValueError('POST_SUBMIT_RECOVERY_REF_SET')
    values={}
    for role,path in expected.items():
        r=proof['refs'][role]
        if r['path']!=str(path): raise ValueError('POST_SUBMIT_RECOVERY_EXACT_PATH:'+role)
        values[role]=obj(r)
    binding=values['owner_binding']
    if (binding['initial']!=initial or binding['authority']!=authority
            or binding['native_driver_source_sha256']!=proof['predecessor_source_sha256']
            or values['original_delegation']['successor_owner_root']!=str(old)
            or values['intent']['start']!=initial
            or values['failure']['status']!='SCIENTIFIC_ROLLOUT_INVALID'
            or values['failure']['terminal']!=proof['refs']['terminal']
            or values['manifest']['root']!=str(expected['manifest'].parent)):
        raise ValueError('POST_SUBMIT_RECOVERY_IDENTITY_CHANGED')
    for name in ('CAMPAIGN_TERMINAL.json','transitions','attempts/000002',
                 'attempts/000001/RESULT.json','attempts/000001/DRIVER_ROUND_RESULT.json',
                 'attempts/000001/analyzer','attempts/000001/training','attempts/000001/offoff'):
        p=old/name
        if p.exists() or p.is_symlink(): raise ValueError('POST_SUBMIT_RECOVERY_PROGRESS_PRESENT:'+name)
    from .rollout_recovery import inspect_invalid,prove_inactive
    disposition=inspect_invalid(proof['refs']['manifest'],initial)
    if disposition['retry_class']!='SAFE_LOCAL_RESOURCE_ISOLATION':
        raise ValueError('POST_SUBMIT_RECOVERY_UNCLASSIFIED_FAILURE')
    prove_inactive(values['manifest'])
    successor=no_symlink_ancestors(old/'source_recoveries'/entry_source_sha256)
    delegation={'schema_id':'FORMAL_POST_SUBMIT_SOURCE_DELEGATION_V1',
        'predecessor_owner_root':str(old),'successor_owner_root':str(successor),
        'predecessor_source_sha256':proof['predecessor_source_sha256'],
        'successor_source_sha256':entry_source_sha256,
        'registration_ref':ref(Path(bundle_root)/'authority/POST_SUBMIT_SOURCE_RECOVERY_V1.json'),
        'initial_request_sha256':initial['request_sha256'],
        'invalid_attempt_adopted_before_reentry':True,'recovery_budget_reset':False,
        'valid_rounds_consumed_before_recovery':0,'historical_receipts_overwritten':False}
    target=old/'POST_SUBMIT_SOURCE_RECOVERY.json'
    if target.exists() and obj(ref(target))!=delegation:
        raise ValueError('POST_SUBMIT_RECOVERY_ALREADY_DELEGATED_TO_ANOTHER_SOURCE')
    if publish: put(target,canonical(delegation))
    return successor
