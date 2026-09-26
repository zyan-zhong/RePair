from __future__ import annotations
import copy, hashlib, importlib.util, json, os, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch
import sys
HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))

class ContractTests(unittest.TestCase):
    def setUp(self):
        import clean_adapter as a
        self.a=a
        with zipfile.ZipFile(HERE/'tests/fixtures/PLAN_HANDOFF_REVIEW.zip') as z:
            self.files={n:z.read(n) for n in z.namelist()}
    def test_required_existing_adapter_interface(self):
        for n in ('validate_packet','validate_profile_without_model_load','input_artifact_refs','execute_training_stage','verify_clean_base','bind_formal_constants','verify_seed_zero_receipt'):
            self.assertTrue(callable(getattr(self.a,n,None)),n)
    def test_actual_approved_packet(self):
        x=self.a.validate_packet(self.files)
        self.assertEqual(x['contract']['budget']['optimizer_steps'],13)
        self.assertEqual(x['contract']['dataset']['one_pass_target_loss_token_count'],176)
        self.assertEqual(x['plan']['interface_profile_id'],'I1_EXECUTION_PROFILE_V1')
    def test_corrupted_plan_is_rejected(self):
        self.files['RESEARCH_PLANNER_TRAINING_PLAN_V1.json']+=b' '
        with self.assertRaisesRegex(ValueError,'FILE_HASH'):self.a.validate_packet(self.files)
    def test_missing_member_is_rejected(self):
        del self.files['PRIMARY_PLAN_APPROVAL_RECEIPT.json']
        with self.assertRaises(ValueError):self.a.validate_packet(self.files)
    def test_unapproved_plan_not_inferred_from_hash(self):
        v=json.loads(self.files['PRIMARY_PLAN_APPROVAL_RECEIPT.json']);v['approval_status']='DRAFT'
        self.files['PRIMARY_PLAN_APPROVAL_RECEIPT.json']=self.a.cb(v)
        ix=json.loads(self.files['FILES.sha256.json']);ix['PRIMARY_PLAN_APPROVAL_RECEIPT.json']=self.a.sha(self.files['PRIMARY_PLAN_APPROVAL_RECEIPT.json']);self.files['FILES.sha256.json']=self.a.cb(ix)
        with self.assertRaisesRegex(ValueError,'APPROVAL'):self.a.validate_packet(self.files)
    def test_nonempty_native_dataset_reused(self):
        x=self.a.validate_packet(self.files)
        self.assertEqual(len(x['native']),13)
        self.assertEqual(sum(sum(v!=-100 for v in n['tokenization']['labels'][1:]) for n in x['native']),176)
    def test_manifest_tamper_not_accepted(self):
        x=self.a.validate_packet(self.files)
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'x').write_bytes(b'abc')
            m={'files':{'x':{'size_bytes':3,'sha256':self.a.sha(b'abc')}},'repository_id':'R','snapshot_revision':'V','project_adapter':None,'lora_enabled':False}
            (p/'manifest').write_bytes(self.a.cb(m))
            b={'snapshot_path':str(p),'manifest_path':str(p/'manifest'),'manifest_sha256':'a'*64,'repository_id':'R','revision':'V'}
            with self.assertRaisesRegex(ValueError,'BASE_MANIFEST_HASH'):self.a.verify_clean_base(b)
    def test_hashes_base_files_and_rejects_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);snap=root/'snap';snap.mkdir();(snap/'config.json').write_bytes(b'{}');(snap/'model.safetensors').write_bytes(b'weight')
            files={p.name:{'size_bytes':p.stat().st_size,'sha256':self.a.sha(p.read_bytes())} for p in snap.iterdir()}
            m={'files':files,'repository_id':'R','snapshot_revision':'V','project_adapter':None,'lora_enabled':False}
            mp=root/'model.json';mp.write_bytes(self.a.cb(m))
            b={'snapshot_path':str(snap),'manifest_path':str(mp),'manifest_sha256':self.a.sha(mp.read_bytes()),'repository_id':'R','revision':'V'}
            self.a.verify_clean_base(b)
            (snap/'model.safetensors').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError,'BASE_FILE'):self.a.verify_clean_base(b)
            (snap/'model.safetensors').unlink();(snap/'model.safetensors').symlink_to(mp)
            with self.assertRaises(ValueError):self.a.verify_clean_base(b)
    def test_no_pilot_adapter_in_base_snapshot(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);(p/'adapter_config.json').write_text('{}');mp=p/'m.json'
            m={'files':{},'repository_id':'R','snapshot_revision':'V','project_adapter':None,'lora_enabled':False};mp.write_bytes(self.a.cb(m))
            b={'snapshot_path':str(p),'manifest_path':str(mp),'manifest_sha256':self.a.sha(mp.read_bytes()),'repository_id':'R','revision':'V'}
            with self.assertRaises(ValueError):self.a.verify_clean_base(b)
    def test_bound_constants_not_pilot_defaults(self):
        from types import SimpleNamespace
        x=self.a.validate_packet(self.files);c=x['contract'];o=x['order'];p=SimpleNamespace()
        self.a.bind_formal_constants(p,c,o)
        self.assertEqual(p.FORMAL_EFFECTIVE_BATCH,1);self.assertEqual(p.FORMAL_OPTIMIZER_STEPS,13)
        c=copy.deepcopy(c);c['budget']['epochs']=2;c['budget']['optimizer_steps']=26;c['budget']['target_loss_token_budget']=352
        self.a.bind_formal_constants(p,c,o);self.assertEqual(p.FORMAL_OPTIMIZER_STEPS,26)
    def test_zero_step_receipt_cannot_claim_training_or_mismatched_seed(self):
        x=self.a.validate_packet(self.files)
        with self.assertRaises(ValueError):self.a.verify_seed_zero_receipt({'training_executed':True},x['plan'],{})

class PublicationTests(unittest.TestCase):
    def setUp(self):
        import run_stage as r
        self.r=r
    def test_write_once_idempotent_and_conflicting_data_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x';self.r.write_once(p,b'a');self.r.write_once(p,b'a')
            with self.assertRaises(ValueError):self.r.write_once(p,b'b')
    def test_no_key_in_submitted_environment(self):
        e=self.r.worker_environment({'OPENAI_API_KEY':'secret','HF_TOKEN':'secret','PATH':'/bin','OUTPUT_ROOT':'bad'})
        self.assertNotIn('OPENAI_API_KEY',e);self.assertNotIn('HF_TOKEN',e)
        self.assertNotIn('OUTPUT_ROOT',e);self.assertEqual(e['HF_HUB_OFFLINE'],'1')
    def test_slurm_wrapper_uses_absolute_script_not_spool_dir(self):
        s=self.r.job_script(Path('/a/pkg/run_stage.py'),Path('/b/request.json'),'smoke')
        self.assertIn('/a/pkg/run_stage.py',s);self.assertNotIn('dirname',s)
        self.assertNotIn('set -',s);self.assertNotIn('pipefail',s)
    def test_submit_requires_capability_and_does_not_duplicate(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);s=d/'job.sh';s.write_text('#!/bin/bash\ntrue\n')
            with patch.object(self.r,'invoke_sbatch',return_value='12345') as f:
                self.r.submit_once(d,'smoke',s,{'partition':'gpu_a800','time':'00:20:00'})
                self.r.submit_once(d,'smoke',s,{'partition':'gpu_a800','time':'00:20:00'})
                self.assertEqual(f.call_count,1)
    def test_intent_without_receipt_stops(self):
        with tempfile.TemporaryDirectory() as d:
            d=Path(d);(d/'smoke.SUBMIT_INTENT.json').write_text('{}');s=d/'job';s.write_text('x')
            with patch.object(self.r,'invoke_sbatch') as f:
                with self.assertRaisesRegex(ValueError,'UNCONFIRMED'):self.r.submit_once(d,'smoke',s,{})
                f.assert_not_called()
    def test_sbatch_has_no_cpu_memory_or_requeue(self):
        args=self.r.sbatch_args(Path('/x/job.sh'),Path('/x/log-%j'),{'partition':'gpu_a800','time':'00:20:00'})
        self.assertIn('--gpus=1',args);self.assertIn('--no-requeue',args)
        for x in args:self.assertFalse(x.startswith(('--mem','--cpus')))

if __name__=='__main__':unittest.main()

class WorkerBootstrapTests(unittest.TestCase):
    def test_sanitized_worker_can_bootstrap_existing_repository(self):
        import subprocess
        import run_stage as r
        from round_training import contracts
        trainer=Path(contracts.__file__).resolve().parents[1]
        repo=next(p for p in trainer.parents if (p/'src/pchsi').is_dir())
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            value=r.tagged({'schema_id':'EXISTING_CLEAN_INITIALIZATION_REQUEST_V1','request':{'repo':str(repo)},
                'package_sha256':'p','runtime':{'source_code_files':{},'source_code_root_sha256':r.a.sha(r.a.cb({}))}},'request_sha256')
            f=root/'request.json';f.write_bytes(r.a.cb(value))
            # Worker environment has no PYTHONPATH. Only network/full-tree
            # preflight and package identity are isolated; the pchsi JSON and
            # original training-contract imports are real.
            code=("import sys;sys.path.insert(0,"+repr(str(HERE))+");import run_stage as r;"
                  "original=r.setup;r.setup=lambda req:original(req,verify=False);"
                  "r.package_identity=lambda:'p';"
                  "r.checked_request(r.Path("+repr(str(f))+"));print('BOOTSTRAP_PASS')")
            env=dict(os.environ);env.pop('PYTHONPATH',None);env['PYTHONDONTWRITEBYTECODE']='1'
            p=subprocess.run([sys.executable,'-B','-c',code],cwd=root,env=env,text=True,capture_output=True,check=False)
            self.assertEqual(p.returncode,0,p.stdout+p.stderr)
            self.assertIn('BOOTSTRAP_PASS',p.stdout)
