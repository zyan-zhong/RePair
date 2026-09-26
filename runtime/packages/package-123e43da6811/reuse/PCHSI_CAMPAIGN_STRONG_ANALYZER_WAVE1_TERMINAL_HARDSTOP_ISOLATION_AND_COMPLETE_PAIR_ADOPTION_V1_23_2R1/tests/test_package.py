from pathlib import Path
import importlib.util, json
P=Path(__file__).resolve().parents[1]

def load():
 s=importlib.util.spec_from_file_location('drv',P/'v1232r1_driver.py'); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m

def fake_call(tmp_path, *, lid='c'*64, status='AMBIGUOUS_POST_SEND', failure='UNEXPECTED_BRIDGE_EXCEPTION'):
 d=tmp_path/lid; d.mkdir()
 (d/'logical_call.json').write_text(json.dumps({'logical_call_id':lid,'stage_id':'L-A1','condition_id':'A1','terminal_method_status':status}))
 (d/'attempt_000.json').write_text(json.dumps({'logical_call_id':lid,'retry_class':'NO_RETRY','retry_authority':'FROZEN_RUNTIME_POLICY','terminal_attempt_status':'AMBIGUOUS_POST_SEND','bytes_transmission_state':'MAY_HAVE_BEEN_SENT'}))
 (d/'method_result.json').write_text(json.dumps({'status':status,'failure_class':failure,'counts_as_method_failure':False,'hard_stop':True}))
 return d

def test_terminal_hard_stop_final_isolation_accepts(tmp_path):
 m=load(); d=fake_call(tmp_path)
 rows=[{'source_unit_id':'s1','stage_id':'L-A0','condition_id':'A0','hard_stop':False,'status':'ACCEPTED'},
       {'source_unit_id':'s2','stage_id':'L-A1','condition_id':'A1','hard_stop':True,'status':'AMBIGUOUS_POST_SEND','method_failure_reason':'UNEXPECTED_BRIDGE_EXCEPTION','logical_call_id':'c'*64,'call_dir':str(d)}]
 units=[{'source_unit_id':'s1','stage_id':'L-A0','condition_id':'A0'}, {'source_unit_id':'s2','stage_id':'L-A1','condition_id':'A1'}]
 v=m.audit_terminal_hard_stop_isolation(wave={'hard_stop_count':1},rows=rows,units=units,complete_source_ids=['s1'])
 assert v['hard_stop_is_final_frozen_unit'] is True
 assert v['hard_stop_source_quarantined_from_complete_pair_corpus'] is True
 assert v['prior_complete_pairs_remain_adoptable'] is True
 assert v['retry_class']=='NO_RETRY'

def test_nonfinal_hard_stop_rejected(tmp_path):
 m=load(); d=fake_call(tmp_path)
 rows=[{'source_unit_id':'s2','stage_id':'L-A1','condition_id':'A1','hard_stop':True,'status':'AMBIGUOUS_POST_SEND','method_failure_reason':'UNEXPECTED_BRIDGE_EXCEPTION','logical_call_id':'c'*64,'call_dir':str(d)},
       {'source_unit_id':'s3','stage_id':'L-A0','condition_id':'A0','hard_stop':False,'status':'ACCEPTED'}]
 units=[{'source_unit_id':'s2','stage_id':'L-A1','condition_id':'A1'}, {'source_unit_id':'s3','stage_id':'L-A0','condition_id':'A0'}]
 try: m.audit_terminal_hard_stop_isolation(wave={'hard_stop_count':1},rows=rows,units=units,complete_source_ids=[])
 except RuntimeError as e: assert 'NOT_FINAL' in str(e)
 else: raise AssertionError('expected failure')

def test_hard_stop_source_cannot_be_complete(tmp_path):
 m=load(); d=fake_call(tmp_path)
 rows=[{'source_unit_id':'s2','stage_id':'L-A1','condition_id':'A1','hard_stop':True,'status':'AMBIGUOUS_POST_SEND','method_failure_reason':'UNEXPECTED_BRIDGE_EXCEPTION','logical_call_id':'c'*64,'call_dir':str(d)}]
 units=[{'source_unit_id':'s2','stage_id':'L-A1','condition_id':'A1'}]
 try: m.audit_terminal_hard_stop_isolation(wave={'hard_stop_count':1},rows=rows,units=units,complete_source_ids=['s2'])
 except RuntimeError as e: assert 'CANNOT_BE_COMPLETE' in str(e)
 else: raise AssertionError('expected failure')

def test_no_provider_or_rollout_reexecution_path():
 t=(P/'v1232r1_driver.py').read_text()
 assert 'run_registry(' not in t
 assert 'execute_one(' not in t
 assert 'sbatch' not in t and 'srun' not in t
 assert "strong_local_logical_call_reexecution_count':0" in t

def test_complete_pair_policy_frozen():
 t=(P/'v1232r1_driver.py').read_text()
 for x in ['replacement_source_count','top_up_source_count','resource_budget_expansion','outcome_adaptive_selection_used','automatic_retry_count']:
  assert x in t
 assert 'ONLY_EXISTING_A0_ACCEPTED_PLUS_A1_ACCEPTED_COMPLETE_PAIRS_ENTER_WAVE2' in t

def test_canonical_grouping_symbols_plural():
 t=(P/'v1232r1_driver.py').read_text()
 assert 'build_group_synthesis_inputs' in t
 assert 'build_group_synthesis_input(' not in t
 assert "build_group_manifests'](local_results=local_results,mechanical_signatures=mechanical)" in t

def test_source_context_shape_array():
 t=(P/'v1232r1_driver.py').read_text()
 assert "write_new_value(gr/'source_contexts.json',members)" in t

def test_no_strict_shell():
 t=(P/'RUN_V1232R1.sh').read_text()
 assert 'set -e' not in t and 'set -u' not in t and 'pipefail' not in t
