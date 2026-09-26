import json,hashlib
from copy import deepcopy
from pathlib import Path
from review_boundary import compatible_bundle,complete_review

def test_fresh_and_cached_method_failure_produce_same_correction_request(tmp_path):
    from review_boundary import method_failure
    call=tmp_path/'registered_call';call.mkdir()
    (call/'validation_error.json').write_text(json.dumps({'error_type':'ValueError','message':'GUARDED_PREFIX_TOKEN_BOUNDARY','failure_class':'METHOD_OUTPUT_INVALID'}))
    fresh={'call_dir':str(call),'method_failure_reason':'ValueError:GUARDED_PREFIX_TOKEN_BOUNDARY'}
    cached={**fresh,'method_failure_reason':'METHOD_OUTPUT_INVALID'}
    assert method_failure(fresh)==method_failure(cached)=='ValueError:GUARDED_PREFIX_TOKEN_BOUNDARY'

def test_inherited_successful_source_reviews_still_pass_all_native_checks():
    fixtures=json.loads((Path(__file__).parents[1]/'fixtures/SOURCE_REVIEW_FIXTURES.json').read_bytes())
    for f in fixtures:
        value,_=complete_review(f['response_text'],f['projection'],f['schema'])
        assert {r['fragment_id'] for r in value['reviews']}=={i['fragment_id'] for i in f['projection']['items']}

def test_format_repair_preserves_source_evidence_model_and_budget():
    req=json.loads((Path(__file__).parents[1]/'fixtures/FAILED_REQUEST.json').read_bytes())
    projection=json.loads(req['input'][1]['content'][0]['text']);original=deepcopy(req)
    contract={'schema_id':'REGISTERED_PRE_REVIEW_SERIALIZATION_BOUNDARY_V1','new_method_attempt_limit':2,'context_window_tokens':1050000}
    dh=lambda domain,v:hashlib.sha256((domain+json.dumps(v,sort_keys=True)).encode()).hexdigest()
    value=compatible_bundle({'provider_request':req,'request_body_sha256':'a'*64},projection,1,None,contract,dh)
    assert value['provider_request']['input'][1:]==original['input'][1:]
    for key in ('model','reasoning','max_output_tokens','tools','truncation'):
        assert value['provider_request'][key]==original[key]
    assert req==original
