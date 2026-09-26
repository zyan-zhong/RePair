from __future__ import annotations
import copy, importlib.util, json, os, tempfile, unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
class EntryTests(unittest.TestCase):
    def test_preparation_api_exists(self):
        import prepare
        self.assertTrue(callable(getattr(prepare,'materialize_source_previews',None)), 'MISSING_EXISTING_TRAINING_PREPARATION_API')
    def test_no_training_or_shell_fail_fast(self):
        import prepare
        source=(ROOT/'prepare.py').read_text()
        self.assertNotIn('set -e',source)
        self.assertNotIn('subprocess.run(["sbatch"',source)
        self.assertNotIn('model.train()',source)
        self.assertNotIn('optimizer.step()',source)
        self.assertNotIn('OPENAI_API_KEY',source)
    def test_publish_idempotent_and_no_clobber(self):
        import prepare
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'out'
            a=prepare.publish(p,{'a.json':b'{"x":1}'})
            self.assertEqual(a,prepare.publish(p,{'a.json':b'{"x":1}'}))
            (p/'a.json').write_bytes(b'changed')
            with self.assertRaises(ValueError):prepare.publish(p,{'a.json':b'{"x":1}'})
    def test_duplicate_zip_member_rejected(self):
        import prepare,zipfile, warnings
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.zip'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with zipfile.ZipFile(p,'w') as z:
                    z.writestr('same','a');z.writestr('same','b')
            with self.assertRaisesRegex(ValueError,'DUPLICATE'):prepare.load_zip(p,prepare.sha(p.read_bytes()))
    def test_archive_traversal_rejected(self):
        import prepare,zipfile
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.zip'
            with zipfile.ZipFile(p,'w') as z:z.writestr('../x','a')
            with self.assertRaisesRegex(ValueError,'PATH'):prepare.load_zip(p,prepare.sha(p.read_bytes()))
    def test_draft_batch_rule_no_padding(self):
        import prepare
        p=prepare.batch_proposal(13,1,1,17)
        self.assertEqual(p['optimizer_steps'],13)
        self.assertFalse(p['sample_padding_allowed'])
        self.assertFalse(p['drop_last'])
        with self.assertRaisesRegex(ValueError,'DIVISIBLE'):prepare.batch_proposal(13,1,4,17)
    def test_arbitrary_population_is_derived(self):
        import prepare
        self.assertEqual(prepare.batch_proposal(8,2,4,31)['optimizer_steps'],4)
    def test_target_hindsight_not_in_renderer_input(self):
        import prepare
        x={'schema_id':'POLICY_SEMANTIC_TRAINING_ROW_V1','arm_id':'T2',
           'diagnostic_only':True,'verified_positive':False,'promotion_eligible':False,
           'terminal_effect':'NEUTRAL','policy_visible_context':{'source_prompt_text':'RAW_POLICY_PROMPT_V1\nunit','source_prompt_bound':True,'admissible_commands':['look']},
           'target_action':'look','row_sha256':'a'*64,'source_state_sha256':'b'*64}
        r=prepare.renderer_module().build_t2_source_adapter_row(x,0)
        self.assertEqual(set(r['input']),{'prompt_text','prompt_sha256'})
        self.assertEqual(r['target']['action_json'],'{"action":"look"}')
        x['verified_positive']=True
        with self.assertRaises(Exception):prepare.renderer_module().build_t2_source_adapter_row(x,0)

class RealArtifactTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import prepare
        c=json.loads((ROOT/'current_round.json').read_text())
        cls.archive=Path(os.environ.get('PCHSI_TEST_F0F1_ARCHIVE',c['f0f1_review']))
        cls.cfg=c
    def test_actual_f0f1_source_previews(self):
        import prepare
        docs=prepare.load_zip(self.archive,self.cfg['f0f1_review_sha256'])
        result=prepare.materialize_source_previews(docs)
        self.assertEqual(len(result['semantics']),13)
        self.assertEqual(len(result['renderer_sources']),13)
        self.assertEqual(result['counts']['repeated_f0_contexts_checked'],65)
        self.assertEqual(len({r['source_state_sha256'] for r in result['semantics']}),13)
        self.assertTrue(all(not r['verified_positive'] and not r['promotion_eligible'] for r in result['semantics']))
        self.assertEqual(result['runtime']['continuation_request_contract']['request_kind'],'I1')
    def test_changed_source_prompt_rejected(self):
        import prepare
        docs=prepare.load_zip(self.archive,self.cfg['f0f1_review_sha256'])
        p=next(n for n in docs if '/F0/' in n and n.endswith('BRANCH_EVIDENCE_V1.json'))
        b=json.loads(docs[p]);b['policy_calls'][0]['policy_call']['prompt_text']+='future result'
        docs[p]=json.dumps(b).encode()
        with self.assertRaises(ValueError):prepare.materialize_source_previews(docs)
    def test_changed_frozen_candidate_rejected(self):
        import prepare
        docs=prepare.load_zip(self.archive,self.cfg['f0f1_review_sha256'])
        p=next(n for n in docs if n.startswith('frozen_sources/candidates/'))
        c=json.loads(docs[p]);c['exact_action']='look';docs[p]=json.dumps(c).encode()
        with self.assertRaises(ValueError):prepare.materialize_source_previews(docs)

if __name__=='__main__':unittest.main()

class BoundPostReadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import prepare
        cfg=json.loads((ROOT/'current_round.json').read_text())
        cls.package=Path(os.environ.get('PCHSI_TEST_STAGE3X',cfg['existing_post_package']))
        cls.post=prepare.module_from(cls.package/'post_round.py','_test_original_post')
        cls.cfg=cfg
    def fixture(self):
        # Schema fixture only. Never represented as the user's real Strong answer.
        import prepare
        human=json.loads((self.package/'preview/HUMAN_POST_DRAFT.json').read_text())
        from pchsi.cognitive_runtime.researcher import finalize_api_post_shadow
        sh={k:v for k,v in human.items() if k not in ('schema_id','schema_version','post_record_sha256')}
        sh['lesson']='SYNTHETIC_TEST_RESPONSE_NOT_A_REAL_MODEL_OUTPUT'
        shadow=finalize_api_post_shadow(sh)
        facts=json.loads((self.package/'preview/POST_FACTS.json').read_text())
        files={'human/HUMAN_RESEARCHER_POST_V1.json':prepare.cb(human),
               'HUMAN_POST_DRAFT.json':prepare.cb(human),
               'HUMAN_APPROVAL.json':prepare.cb({'approved_post_record_sha256':human['post_record_sha256']}),
               'SHADOW_CALL_INTENT.json':prepare.cb({'test_only':True}),
               'SHADOW_CALL_RECEIPT.json':prepare.cb({'intent_sha256':prepare.sha(prepare.cb({'test_only':True})),
                   'result':{'status':'ACCEPTED','call_dir':'/synthetic/strong_calls/test_only'}}),
               'strong_calls/test_only/validated_artifact.json':prepare.cb(shadow),
               'POST_FACTS.json':prepare.cb(facts),
               'POST_FIELD_COMPARISON.json':prepare.cb(self.post.compare_posts(human,shadow))}
        return files,{'manifest':{'execution_manifest_sha256':facts['execution_manifest_sha256']},
                      'result':{'result_package_sha256':facts['result_package_sha256']}}
    def test_reuses_original_shadow_validation_and_comparison(self):
        import prepare
        files,data=self.fixture();r=prepare.inspect_registered_post(files,self.post,data)
        self.assertFalse(r['field_adjudication_performed'])
        self.assertFalse(r['training_authorized'])
        self.assertIn('SYNTHETIC',r['shadow']['lesson'])
    def test_shadow_not_accepted_rejected(self):
        import prepare
        files,data=self.fixture();r=json.loads(files['SHADOW_CALL_RECEIPT.json']);r['result']['status']='AMBIGUOUS'
        files['SHADOW_CALL_RECEIPT.json']=prepare.cb(r)
        with self.assertRaisesRegex(ValueError,'SHADOW_NOT_ACCEPTED'):prepare.inspect_registered_post(files,self.post,data)
    def test_post_result_mismatch_rejected(self):
        import prepare
        files,data=self.fixture();data['result']['result_package_sha256']='a'*64
        with self.assertRaisesRegex(ValueError,'POST_RESULT_BINDING'):prepare.inspect_registered_post(files,self.post,data)
    def test_comparison_tampering_rejected(self):
        import prepare
        files,data=self.fixture();r=json.loads(files['POST_FIELD_COMPARISON.json']);r['fields'][0]['exact_equal']=not r['fields'][0]['exact_equal']
        files['POST_FIELD_COMPARISON.json']=prepare.cb(r)
        with self.assertRaisesRegex(ValueError,'POST_COMPARISON_CHANGED'):prepare.inspect_registered_post(files,self.post,data)
