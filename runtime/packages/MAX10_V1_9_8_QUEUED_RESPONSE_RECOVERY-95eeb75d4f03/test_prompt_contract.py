from copy import deepcopy
from prompt_contract import amend,WINDOW_CONTRACT

def test_future_local_amendment_preserves_all_evidence_and_model():
    original={'stage_id':'L-A0','request_body_sha256':'old','runtime_manifest_sha256':'manifest',
        'input_projection':{'evidence':'all'},'provider_request':{'model':'registered','input':[{'content':[{'text':'old prompt'}]},{'content':[{'text':'ALL EVIDENCE'}]}],
        'max_output_tokens':12288,'reasoning':{'effort':'high'},'store':False}}
    before=deepcopy(original)
    changed=amend(original,global_ceiling=32768,authority_ref={'sha256':'registered'},hash_request=lambda r:'new')
    assert original==before
    assert changed['provider_request']['input'][1]==original['provider_request']['input'][1]
    assert changed['input_projection']==original['input_projection']
    assert changed['provider_request']['model']=='registered'
    assert changed['provider_request']['max_output_tokens']==32768
    assert WINDOW_CONTRACT in changed['provider_request']['input'][0]['content'][0]['text']
    assert changed['request_body_sha256']=='new'

def test_group_request_is_not_changed():
    bundle={'stage_id':'G-A2'}
    assert amend(bundle,global_ceiling=32768,authority_ref={},hash_request=lambda _:None) is bundle
