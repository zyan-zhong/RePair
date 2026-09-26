"""Actual native PRE/schema/materializer boundary, with provider send disabled."""
from pathlib import Path
from unittest.mock import patch
from copy import deepcopy
import json

def verify_native_pre(binding,values,core,authority,root,source_files):
    import bounded_pre
    from exact_bindings import read_ref,immutable_json,file_ref
    from strategy_planner import TEXT_FIELDS
    from pre_capacity import build_review_packets
    projection=read_ref({**authority['source_projection_ref'],'file_sha256':authority['source_projection_ref']['sha256']})
    inventory=build_review_packets(projection)
    contexts={x['source_state_sha256']:x for x in projection['blind_input']['analyzer_evidence_view']['source_contexts']}
    pairs={x['source_state_sha256']:x for x in projection['blind_input']['registered_candidate_universe']['pair_table']}
    schema=json.loads((Path(root)/'REVIEW_SCHEMA.json').read_bytes())
    bound=schema['properties']['reviews']['items']['properties']['diagnosis']['maxLength']
    reviews=[]
    for packet in inventory['packets']:
        state=packet['source'].get('source_state_sha256');source=contexts.get(state);pair=pairs.get(state)
        row={'packet_id':packet['packet_id'],'fragment_id':'test-only','source_state_sha256':state,
            'public_task_goal_exact':source['public_task_goal'] if source else None,
            'diagnosis':'x'*bound,'counterevidence':'x'*bound,'falsifiable_hypothesis':'x'*bound,'plans':[]}
        if pair:
            for condition in ('A2','A3'):
                candidate=pair[condition]['candidate']
                action=candidate['exact_action'] or candidate['option_actions'][0]
                strategy={k:'x'*bound for k in TEXT_FIELDS};strategy['action']=action
                row['plans'].append({'condition':condition,'original_candidate_sha256':candidate['candidate_sha256'],
                    'viable':True,'rationale':'x'*bound,'strategy':strategy,'program':[]})
        reviews.append(row)
    receipt={'schema_id':'TEST_ONLY_MAXIMAL_STRATEGY_REVIEW_FIXTURE','test_only':True,
        'all_source_records_reviewed':False,'source_record_count':len(inventory['expected_records']),
        'reviews':reviews,'calls':[],'raw_evidence_truncated':False}
    destination=Path(root)/'native_pre_boundary'
    immutable_json(destination/'source_reviews/COMPLETE_REVIEW_RECEIPT.json',receipt)
    seen=[]
    class NoSend(Exception):pass
    def no_send(**kwargs):
        seen.append(kwargs['projection']);raise NoSend()
    with patch.object(bounded_pre,'execute_reviews',lambda *args,**kw:(receipt,contexts)),\
         patch.object(core.orch,'execute_one',no_send):
        try:
            bounded_pre.run_pre(deepcopy(binding),values,core,
                read_ref({**source_files['tail'],'file_sha256':source_files['tail']['sha256']}),
                read_ref({**source_files['universe'],'file_sha256':source_files['universe']['sha256']}),
                destination,authority=authority)
        except NoSend:pass
    if len(seen)!=1:raise ValueError('NATIVE_PRE_NO_SEND_BOUNDARY_NOT_REACHED')
    preflight=json.loads((destination/'FINAL_PRE_REQUEST_PREFLIGHT.json').read_bytes())
    # Exercise native training representation validation using explicit test
    # plans, without claiming accepted PRE or manufacturing Benefit evidence.
    import strategy_hooks,subprocess,sys
    from training_binding import strategy_source
    import pre_stage
    derived=json.loads((destination/'DERIVED_STRATEGY_UNIVERSE.json').read_bytes())
    registry=json.loads((destination/'CUE_STRATEGY_REGISTRY.json').read_bytes())
    labels=pre_stage.load_native_labels(core.repo,destination,binding['source_registration'])
    selected=[pair['A3']['candidate'] for pair in derived['pair_table']]
    strategies=[{'source_state_sha256':pair['source_state_sha256'],
        'source_candidate_sha256':pair['A3']['candidate_sha256'],
        'strategy_plan_sha256':pair['A3']['strategy_plan']['strategy_plan_sha256']}
        for pair in derived['pair_table']]
    with strategy_hooks.training_scope(registry):
        representations=strategy_source.validate_pre_strategies(strategies,
            accepted_pre={'selected_candidate_sha256s':[c['candidate_sha256'] for c in selected]},
            selected_candidates=selected,native_labels=labels)
    child=subprocess.run([sys.executable,'-B',str(Path(__file__).with_name('child_preflight.py')),
        '--registry',str(destination/'CUE_STRATEGY_REGISTRY.json')],capture_output=True,timeout=90)
    (Path(root)/'CHILD_INTERFACE_PREFLIGHT.log').write_bytes(child.stdout+child.stderr)
    if child.returncode:raise ValueError('REGISTERED_CHILD_INTERFACE_PREFLIGHT_FAILED:'+child.stderr.decode(errors='replace')[-2000:])
    child_result=json.loads(child.stdout)
    result={'schema_id':'REGISTERED_NATIVE_PRE_MAX_TEXT_NO_SEND_TEST_V1','status':'PASS',
        'source_pairs':len(pairs),'generated_text_character_bound':bound,
        'final_request_bytes':preflight['request_bytes'],'input_wire_limit':preflight['input_wire_limit'],
        'provider_calls':0,'test_artifacts_are_scientific_evidence':False,
        'actual_native_schema_and_candidate_contracts_loaded':True,
        'native_training_representations_validated':len(representations),'child_interfaces':child_result}
    immutable_json(Path(root)/'NATIVE_PRE_BOUNDARY_TEST.json',result)
    return result
