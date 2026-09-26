"""Propagate verified campaign transport policy without changing scientific inputs."""
from pathlib import Path
from functools import wraps
from contextlib import contextmanager
from unittest.mock import patch
import json, math, time

STAGES={'L-A0','L-A1','G-A2','G-A3','C','X','R-PRE-PRIMARY-V2','R-POST-PRIMARY-V1'}

def remaining_attempts(restarts,consumed):
    if type(restarts) is not int or type(consumed) is not int or restarts<0 or consumed<1:
        raise ValueError('TRANSPORT_BUDGET_INVALID')
    remaining=1+restarts-consumed
    if remaining<1:raise ValueError('FROZEN_TRANSPORT_BUDGET_EXHAUSTED')
    return remaining

def bound_scope(binding,expected_campaign_ref):
    from exact_bindings import read_ref
    from pchsi.round_control.campaign_authority import CampaignStartupAuthorityV1
    ref=binding.get('campaign_startup_authority')
    if ref!=expected_campaign_ref:raise ValueError('CAMPAIGN_RETRY_AUTHORITY_CHANGED')
    campaign=CampaignStartupAuthorityV1.from_dict(read_ref(ref))
    return {'round_id':binding['round_id'],'parent_policy_id':binding['parent_policy_id'],
        'output_root':binding['output_root'],'max_infrastructure_attempt_restarts':campaign.max_infrastructure_attempt_restarts,
        'campaign_authority_ref':ref,'campaign_authority_sha256':campaign.authority_sha256}

def executor_with_scope(native,scope,observe=None):
    @wraps(native)
    def execute(**kwargs):
        if kwargs['stage_id'] not in STAGES:raise ValueError('UNREGISTERED_TRANSPORT_STAGE')
        if kwargs['round_id']!=scope['round_id'] or kwargs['policy_version']!=scope['parent_policy_id']:
            raise ValueError('TRANSPORT_ROUND_POLICY_MISMATCH')
        if not Path(kwargs['output_root']).resolve().is_relative_to(Path(scope['output_root']).resolve()):
            raise ValueError('TRANSPORT_OUTPUT_OUTSIDE_BOUND_ROUND')
        limit=scope['max_infrastructure_attempt_restarts']
        chosen=kwargs.get('max_infrastructure_attempt_restarts',limit)
        if type(chosen) is not int or chosen<0 or chosen>limit:raise ValueError('TRANSPORT_BUDGET_EXPANSION')
        if observe:observe(kwargs,None)
        result=native(**{**kwargs,'max_infrastructure_attempt_restarts':chosen})
        if observe:observe(kwargs,result)
        return result
    return execute

@contextmanager
def install_executor(scope,observe=None):
    from pchsi.cognitive_runtime import orchestrator,registry_runner
    wrapped=executor_with_scope(orchestrator.execute_one,scope,observe)
    with patch.object(orchestrator,'execute_one',wrapped),patch.object(registry_runner,'execute_one',wrapped):yield

@contextmanager
def retry_pacing(orchestrator,frozen_transport,*,offset_root=None,consumed=0,sleep=time.sleep):
    """Historical P2 delays; successor continues the old attempt ordinal."""
    delays=tuple(frozen_transport.BACKOFF_SECONDS)
    if not delays or any(type(x) not in (int,float) or not math.isfinite(x) or x<=0 for x in delays):
        raise ValueError('REGISTERED_P2_BACKOFF_INVALID')
    native=orchestrator.execute_via_existing_p2;counts={}
    def paced(bundle,call_dir,*,client_request_id):
        call_dir=Path(call_dir);key=(str(call_dir),client_request_id);index=counts.get(key,0)
        offset=consumed if offset_root is not None and call_dir.parent==Path(offset_root) else 0
        ordinal=offset+index
        if index:
            prior=json.loads((call_dir/('attempt_%03d.json'%(index-1))).read_bytes())
            if prior.get('logical_call_id')!=client_request_id or prior.get('transport_attempt_index')!=index-1 or prior.get('retry_class') not in ('SAFE_PRE_SEND','SAFE_PROVIDER_REJECTION'):
                raise ValueError('NATIVE_SAFE_RETRY_RECEIPT_REQUIRED')
        if ordinal:
            if ordinal>len(delays):raise ValueError('NO_REGISTERED_P2_BACKOFF_FOR_RETRY')
            sleep(delays[ordinal-1])
        counts[key]=index+1
        return native(bundle,call_dir,client_request_id=client_request_id)
    with patch.object(orchestrator,'execute_via_existing_p2',paced):yield
