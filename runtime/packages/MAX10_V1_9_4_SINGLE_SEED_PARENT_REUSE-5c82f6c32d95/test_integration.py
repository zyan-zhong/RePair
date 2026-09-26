import sys,unittest,json,hashlib,tempfile
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent/'src'))
from promotion_v2 import decide,validate_rule
from goal_metric import METRIC_ID

class IntegrationTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup);self.root=Path(self.tmp.name)
  path=Path(__file__).parent/'original_promotion_rule.py'
  self.rule={'schema_id':'FROZEN_TRAIN_SELECT_PROMOTION_RULE_V2','comparison':'success_then_terminal_goal_fraction','secondary_metrics_role':'goal_fraction_tie_break_only',
    'goal_metric_id':METRIC_ID,'frozen_before_outcomes':True,'memory_state':'OFF','harness_state':'OFF','benchmark_feedback_used':False,
    'evidence_access_class':'TRAIN_SELECT','primary_metric':'total_success_cells','expected_task_count':2,'replicate_seeds':[7],
    'decision_rule_id':'test-v2','goal_source_refs':[],'environment_source_refs':[],'integrity_producer_ref':{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}}
  ref={'path':'unused','sha256':'b'*64}
  self.aggregate={'schema_id':'CURRENT_TRAIN_SELECT_AGGREGATE_V1','memory_state':'OFF','harness_state':'OFF','evidence_access_class':'TRAIN_SELECT','primary_statistical_unit':'unique_task',
   'replicates_are_not_independent_tasks':True,'benchmark_feedback_used':False,'round_id':'test','parent_policy_id':'p','candidate_policy_id':'c','request_sha256':'a'*64,
   'frozen_protocol_ref':ref,'identity_audit_ref':ref,'native_paired_results_ref':ref,'unique_task_count':2,'replicate_seeds':[7],'paired_cell_count':2,'total_condition_cell_count':4,
   'parent_success_cells':0,'candidate_success_cells':0,'both_success_cells':0,'both_failure_cells':2,'parent_only_success_cells':0,'candidate_only_success_cells':0,'mean_task_success_rate_delta':0}
  self.rows=[{'ordinal':i,'label':arm,'numerator':n,'denominator':d} for arm,values in [('parent',[(1,2),(0,1)]),('candidate',[(0,1),(2,3)])] for i,(n,d) in enumerate(values)]
 def verdict(self):
  path=self.root/'metric.json';path.write_text(json.dumps({'request_sha256':'a'*64,'metric_id':METRIC_ID,'source_refs':[],'rows':self.rows}))
  self.aggregate['goal_progress_ref']={'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
  return decide(frozen_rule=self.rule,aggregate=self.aggregate)['decision']
 def test_tie_progress_promotes(self):self.assertEqual(self.verdict(),'PROMOTE')
 def test_missing_and_duplicate_cells_fail(self):
  self.rows.pop()
  with self.assertRaises(ValueError):self.verdict()
  self.rows.append(self.rows[-1])
  with self.assertRaises(ValueError):self.verdict()
 def test_native_invalid_not_rollback(self):
  self.aggregate['benchmark_feedback_used']=True
  with self.assertRaises(ValueError):self.verdict()
 def test_rule_must_be_frozen(self):
  self.rule['frozen_before_outcomes']=False
  with self.assertRaises(ValueError):validate_rule(self.rule)

if __name__=='__main__':unittest.main()
