import copy, json, unittest, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
from pre_evidence import build_view, enrich_pair_view, require_later_round
from post_context import compact_projection, validate_rejection

class Views(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture=json.loads((ROOT/'TEST_CHAIN.json').read_bytes())
        cls.post=json.loads((ROOT/'TEST_POST.json').read_bytes())
    def test_pre_has_readable_levels_and_task_context(self):
        v=build_view(self.fixture)
        self.assertTrue(v['local_findings']);self.assertTrue(v['group_findings'])
        self.assertTrue(v['component_attributions']);self.assertTrue(v['crosschecks'])
        self.assertEqual(v['capability_profile'],self.fixture['capability'])
        self.assertTrue(all(r['public_task_goal'] and r['task_family'] for r in v['source_contexts']))
        self.assertEqual(v['rollout_census']['scheduled_count'],sum(v['rollout_census'][k] for k in ['success_count','failure_count','infrastructure_invalid_count','protocol_invalid_count']))
    def test_pair_identity_unchanged_and_context_complete(self):
        v=build_view(self.fixture);old=copy.deepcopy(self.fixture['universe'])
        new=enrich_pair_view(old,v)
        for before,after in zip(old['pair_table'],new['pair_table']):
            self.assertEqual(before['A2'],after['A2']);self.assertEqual(before['A3'],after['A3'])
            self.assertEqual(before['source_context'],after['source_context'])
            self.assertTrue(after['task_family'])
        self.assertEqual(old,self.fixture['universe'])
    def test_current_round_and_retry_excluded(self):
        f=self.fixture['binding'];a={'excluded_round_id':f['round_id'],'owner_root':'/registered/owner','activation_after_round_index':1}
        self.assertFalse(require_later_round(f,a,current={'round_index':1}))
        with self.assertRaises(ValueError):require_later_round({**f,'round_id':'new'},a,current={'round_index':1})
        self.assertTrue(require_later_round({**f,'round_id':'new'},a,current={'round_index':2}))
    def test_missing_or_conflicting_context_rejected(self):
        f=copy.deepcopy(self.fixture);f['prepared'][0]['contexts'][0]['public_task_goal']=''
        with self.assertRaises(ValueError):build_view(f)
        f=copy.deepcopy(self.fixture);f['sources'][0]['manifest']['evidence_pack_sha256']='0'*64
        with self.assertRaises(ValueError):build_view(f)
    def test_forbidden_pre_evidence_rejected(self):
        f=copy.deepcopy(self.fixture);f['capability']['current_f0f1_outcomes']={'winner':'F1'}
        with self.assertRaises(ValueError):build_view(f)
    def test_post_reuses_full_verdicts_without_raw_payloads(self):
        p=copy.deepcopy(self.post['projection']);p['environment_result_package']['branch_records'][0]['policy_calls']=[{'raw':'REPEATED_PAYLOAD_SENTINEL'*1000}]
        v=compact_projection(p,self.post['compact_function'])
        self.assertEqual(v['environment_result_package']['state_results'],p['environment_result_package']['state_results'])
        self.assertEqual(v['environment_result_package']['pair_results'],p['environment_result_package']['pair_results'])
        self.assertEqual(v['environment_result_package']['stable_effect_counts'],p['environment_result_package']['stable_effect_counts'])
        self.assertNotIn('REPEATED_PAYLOAD_SENTINEL',json.dumps(v))
        self.assertEqual(v['training_materialization_context'],p['training_materialization_context'])
        self.assertIn('branch_records',p['environment_result_package'])
    def test_recovery_only_exact_confirmed_size_rejection(self):
        p=self.post;validate_rejection(p)
        for field,value in [('bytes_transmission_state','AMBIGUOUS_POST_SEND'),('terminal_attempt_status','SUCCEEDED')]:
            q=copy.deepcopy(p);q['attempt'][field]=value
            with self.assertRaises(ValueError):validate_rejection(q)
        q=copy.deepcopy(p);q['response']['error']['code']='invalid_api_key'
        with self.assertRaises(ValueError):validate_rejection(q)
    def test_registered_worker_overlay_ignores_quoted_anchor(self):
        import ast
        from post_worker import overlay_child
        source=(ROOT/'TEST_CONDITION_CHILD.txt').read_text()
        rewritten=overlay_child(source);ast.parse(rewritten)
        self.assertIn("needle='        return module.main()'",rewritten)
        self.assertIn('\n    module._install_projection=_install_projection\n    return module.main()',rewritten)
        with self.assertRaises(ValueError):overlay_child(rewritten)

if __name__=='__main__':unittest.main(verbosity=2)
