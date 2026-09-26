"""A scoped system-prompt amendment; native schemas and executors remain authoritative."""
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch
import hashlib,json

GUIDANCE='''
REGISTERED REPAIR COMPLETENESS GUIDANCE:
For each proposed repair, assess whether a single action is sufficient to address
the diagnosed failure mechanism or reach the stated public subgoal. A legal next
action alone does not establish that the repair is complete. If a few additional
steps are needed and supported by the supplied evidence, propose the complete
bounded short_option using the existing 1-4 action limit and a faithful public
termination_condition. Do not stop at an initial navigation action when the
evidence supports the remaining steps needed for the stated repair.
Keep the first action exactly in the supplied current admissible menu. Subsequent
steps must be justified by public evidence and remain subject to the native live
menu checks and stop rules. Do not invent object locations, hidden state, future
observations or unsupported commands. When only one action is justified, retain
exact_action and describe the limitation in the existing
mechanism_hypotheses[].statement or mechanism_hypotheses[].uncertainty fields;
do not add output fields or force a longer plan. Assess each candidate on
its evidence; do not force A2/A3 disagreement or copy a memory strategy blindly.
Keep all existing memory boundaries, uncertainty rules and JSON schema. This is
a repair hypothesis, not a claim of Benefit, training eligibility or promotion.
'''

def amend(bundle,*,authority_ref,hash_request):
    if bundle['stage_id'] not in ('G-A2','G-A3'):return bundle
    existing=bundle.get('registered_group_prompt_amendment')
    if existing:
        if existing['authority_ref']!=authority_ref:raise ValueError('GROUP_PROMPT_AUTHORITY_DRIFT')
        return bundle
    result=deepcopy(bundle)
    result['provider_request']['input'][0]['content'][0]['text']+=GUIDANCE
    result['request_body_sha256']=hash_request(result['provider_request'])
    result['registered_group_prompt_amendment']={
        'schema_id':'REGISTERED_GROUP_REPAIR_COMPLETENESS_PROMPT_V1','authority_ref':authority_ref,
        'base_request_body_sha256':bundle['request_body_sha256'],
        'base_runtime_manifest_sha256':bundle['runtime_manifest_sha256'],
        'input_projection_unchanged':True,'output_schema_unchanged':True,
        'stage_output_token_budget_unchanged':True,'option_executor_unchanged':True}
    return result

@contextmanager
def rendering_scope(core,authority_ref):
    original=core.rr.render_stage_request
    def render(**kwargs):
        return amend(original(**kwargs),authority_ref=authority_ref,
            hash_request=lambda value:core.domain_hash('COGNITIVE_RUNTIME_PROVIDER_REQUEST_V1',value))
    # The historical logical-call builder captures this function in core.api;
    # execution imports it through orchestrator. Both must hash the same body.
    with patch.dict(core.api,{'render_stage_request':render}),\
         patch.object(core.rr,'render_stage_request',render),\
         patch.object(core.orch,'render_stage_request',render),\
         patch.object(core.runner,'render_stage_request',render):yield

@contextmanager
def installed(a,identity,root):
    import adapter
    from exact_bindings import read_ref,immutable_json
    native=adapter.run_group_tail
    authority_path=Path(root)/'AUTHORITY.json'
    authority_ref={'path':str(authority_path),'sha256':hashlib.sha256(authority_path.read_bytes()).hexdigest()}
    activation=a['group_prompt_activation']
    def read(ref):
        return read_ref({**ref,'file_sha256':ref.get('file_sha256',ref.get('sha256'))})
    frozen_index=read(activation['index_ref'])
    if frozen_index['round_index']!=activation['round_index'] or read(frozen_index['request'])['request_sha256']!=activation['request_sha256']:
        raise ValueError('GROUP_PROMPT_ACTIVATION_AUTHORITY_DRIFT')
    def group(binding,values,core,prepared,accesses,out):
        request=read(binding['refs']['request'])
        index_path=Path(a['owner_root'])/'request_bindings'/(request['request_sha256']+'.json')
        index=json.loads(index_path.read_bytes())
        if index['round_index']<activation['round_index']:
            return native(binding,values,core,prepared,accesses,out)
        # Native owner governs same-round mechanical retries and later-round
        # scientific changes. Do not turn the first attempt into a retry ban.
        if read(index['request'])!=request:
            raise ValueError('GROUP_PROMPT_REGISTERED_REQUEST_MISMATCH')
        immutable_json(Path(out)/'registered_group_prompt'/identity/'REGISTERED_GROUP_PROMPT.json',{
            'schema_id':'REGISTERED_ROUND_GROUP_PROMPT_V1','authority_ref':authority_ref,
            'package_manifest_sha256':identity,'request_sha256':request['request_sha256'],
            'round_id':request['round_id'],'round_index':index['round_index'],
            'stages':['G-A2','G-A3'],'historical_requests_rewritten':False})
        with rendering_scope(core,authority_ref):
            return native(binding,values,core,prepared,accesses,out)
    immutable_json(Path(a['owner_root'])/'runtime_extensions'/identity/'GROUP_PROMPT_INSTALLED.json',{
        'schema_id':'REGISTERED_GROUP_PROMPT_INSTALLED_V1','authority_ref':authority_ref,
        'package_manifest_sha256':identity,'activation':activation,
        'actual_provider_use_claimed':False})
    with patch.object(adapter,'run_group_tail',group):yield
