import importlib.util
import os
from pathlib import Path
import json
import tempfile
import unittest
import zipfile
import copy
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import preflight as p

class APITests(unittest.TestCase):
    def test_required_api(self):
        self.assertTrue(callable(getattr(p,'verify_training_evidence',None)), 'MISSING_EXISTING_SELECT_PREFLIGHT_API')

class BoundEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo=Path(os.environ['SELECT_TEST_REPO'])
        cls.old=Path(os.environ['SELECT_TEST_ASSET_ROOT'])
        cls.helpers=p.load_helpers(cls.repo,{
            'handoff':{'path':str(cls.old/'STAGE3Z_EXISTING_PLAN_HANDOFF_V1/handoff.py'), 'sha256':'58e9ab9a34fa0cd795f768d4b5fa87c66cceb001b0e9bb39389cd5cbe6727879'},
            'clean_adapter':{'path':str(cls.old/'STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1/clean_adapter.py'),'sha256':'329c749d39fef22b62d38ad5a212f6ce6c0443ad12b60a3a6733332d651edacc'}})
        cls.t=p.read_packet(ROOT/'tests/fixtures/TRAINING_REVIEW.zip','3be7c71c9e8dc71d0271e542d3074a9b24a211f89b5f44f51b6160b0146e3822',cls.helpers)
        cls.q=p.read_packet(ROOT/'tests/fixtures/PLAN_HANDOFF_REVIEW.zip','ec4b2396208f71dad21bc3b2bdb4b29d05a3c2d3ecdf17ab14695a6ac99d8596',cls.helpers)
        cls.formal=cls.old/'STAGE4A_EXISTING_TRAINER_CLEAN_INIT_V1/tests/fixtures/formal_train.py'
    def test_real_completed_training_chain(self):
        a=p.verify_training_evidence(self.t,self.q,self.helpers,self.formal)
        self.assertEqual(a['optimizer_step_count'],13)
        self.assertEqual(a['target_loss_token_count'],176)
        self.assertNotEqual(a['initial_parameters'],a['final_parameters'])
        self.assertFalse(a['promotion_eligible'])
    def test_tampered_terminal_receipt_rejected(self):
        t=dict(self.t); v=json.loads(t['TRAINING_RESULT.json']);v['stage_receipt']['terminal_status']='STARTED'
        t['TRAINING_RESULT.json']=json.dumps(v).encode()
        with self.assertRaises(Exception):p.verify_training_evidence(t,self.q,self.helpers,self.formal)
    def test_no_missing_ledger_accepted(self):
        t={k:v for k,v in self.t.items() if not k.endswith('training_step_ledger.jsonl')}
        with self.assertRaises(Exception):p.verify_training_evidence(t,self.q,self.helpers,self.formal)
    def test_candidate_alias_cannot_replace_adapter_identity(self):
        t=dict(self.t);v=json.loads(t['CANDIDATE_HANDOFF.json']);v['run_manifest']['adapter_bundle_sha256']='a'*64
        t['CANDIDATE_HANDOFF.json']=json.dumps(v).encode()
        with self.assertRaises(Exception):p.verify_training_evidence(t,self.q,self.helpers,self.formal)
    def test_pool_reference_counts_follow_upstream_not_local_defaults(self):
        refs=p.pool_references(self.q)
        self.assertEqual(set(refs),{'TRAIN_UPDATE','TRAIN_SELECT','TRAIN_AUDIT'})
        self.assertEqual(refs['TRAIN_SELECT']['expected_count'],355)
    def test_grid_arbitrary_population_not_355_hardcoded(self):
        rows=[{'id':'t'+str(i),'index':i+4,'gamefile_sha256':str(i)*64,'split':'train','train_pool':'TRAIN_SELECT'} for i in range(3)]
        a=p.draft_task_seed_grid(rows,(17,31))
        self.assertEqual(a['paired_cells'],6);self.assertEqual(a['condition_episodes'],12)
        self.assertFalse(a['execution_authorized']);self.assertFalse(a['protocol_frozen'])
        self.assertEqual(a['index_crosswalk'][0]['source_index'],4)
    def test_no_duplicate_or_wrong_pool(self):
        row={'id':'t','index':4,'gamefile_sha256':'a'*64,'split':'train','train_pool':'TRAIN_SELECT'}
        for rows in ([row,row],[{**row,'train_pool':'TRAIN_UPDATE'}],[{**row,'split':'valid_unseen'}]):
            with self.assertRaises(ValueError):p.draft_task_seed_grid(rows,(17,31))
    def test_candidate_file_byte_check_has_no_model_load(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);raw=b'non-model-fixture';(d/'adapter_model.safetensors').write_bytes(raw)
            m={'files':{'adapter_model.safetensors':{'size_bytes':len(raw),'sha256':p.sha(raw)}}}
            p.verify_adapter_files(d,m)
            (d/'adapter_model.safetensors').write_bytes(b'changed')
            with self.assertRaises(ValueError):p.verify_adapter_files(d,m)
    def test_extra_or_symlink_candidate_file_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            d=Path(td);(d/'x').write_bytes(b'x');m={'files':{'x':{'size_bytes':1,'sha256':p.sha(b'x')}}}
            (d/'extra').write_bytes(b'z')
            with self.assertRaises(ValueError):p.verify_adapter_files(d,m)
    def test_repeat_write_same_bytes_only(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'a.json';p.write_once(f,b'{}');p.write_once(f,b'{}')
            with self.assertRaises(ValueError):p.write_once(f,b'[]')
    def test_no_gpu_submit_model_load_or_live_override(self):
        source=(ROOT/'run_preflight.py').read_text()
        for bad in ('sbatch','srun','AutoModel','PeftModel','--submit'):
            self.assertNotIn(bad,source)


class MetadataTests(unittest.TestCase):
    def test_metadata_tamper_rejected_before_any_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);refs={}
            for j,pool in enumerate(('TRAIN_UPDATE','TRAIN_SELECT','TRAIN_AUDIT')):
                row={'id':pool,'index':j,'schema_id':'ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1','split':'train','train_pool':pool,'gamefile_sha256':str(j)*64,'gamefile_relpath':pool+'/game.tw-pddl'}
                f=root/(pool+'.jsonl');f.write_bytes(json.dumps(row).encode()+b'\n');refs[pool]={'path':str(f),'sha256':p.file_sha(f),'expected_count':1}
            old=BoundEvidenceTests.helpers['handoff']
            census={'proofs':[{'source_task_id':'TRAIN_UPDATE','source_gamefile_sha256':'0'*64,'exact_gamefile':'/root/TRAIN_UPDATE/game.tw-pddl'}],'task_ids':['TRAIN_UPDATE']}
            values=p.load_bound_pool_metadata(refs,old,census,1)
            self.assertEqual(len(values['TRAIN_SELECT']),1)
            Path(refs['TRAIN_SELECT']['path']).write_bytes(b'{}')
            with self.assertRaisesRegex(ValueError,'POOL_FILE_HASH'):
                p.load_bound_pool_metadata(refs,old,census,1)
    def test_unmodified_required_scientific_core_not_in_patch(self):
        scope=json.loads((ROOT/'PATCH_SCOPE.json').read_bytes())
        self.assertEqual(len(scope),4)
        for name in ('policy_request.py','raw_policy_prompt.py','runtime_core.py','alfworld_adapter.py','select_policy_runtime.py'):
            self.assertFalse(any(n.endswith('/'+name) for n in scope))

if __name__=='__main__':unittest.main()
