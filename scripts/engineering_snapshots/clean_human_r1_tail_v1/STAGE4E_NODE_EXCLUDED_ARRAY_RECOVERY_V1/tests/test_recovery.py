import copy
import importlib
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import recover as m

class RecoveryTests(unittest.TestCase):
    def accounting(self):
        return '\n'.join(f'156877_{i}|{j}|FAILED|1:0|d1n41a18g03|{os.getuid()}|st4d_select_shard' for i,j in enumerate(('156895','156896','156899','156877')))

    def test_exact_failed_nodes_and_unique_physical_ids(self):
        rows=m.parse_failed_accounting(self.accounting(),os.getuid())
        self.assertEqual([v['job_id'] for v in rows],['156895','156896','156899','156877'])
    def test_running_rejected(self):
        with self.assertRaises(m.RecoveryError):m.parse_failed_accounting(self.accounting().replace('FAILED','RUNNING',1),os.getuid())
    def test_wrong_node_rejected(self):
        with self.assertRaises(m.RecoveryError):m.parse_failed_accounting(self.accounting().replace('d1n41a18g03','another',1),os.getuid())
    def test_wrong_owner_rejected(self):
        with self.assertRaises(m.RecoveryError):m.parse_failed_accounting(self.accounting(),os.getuid()+1)
    def test_missing_element_rejected(self):
        with self.assertRaises(m.RecoveryError):m.parse_failed_accounting('\n'.join(self.accounting().splitlines()[:3]),os.getuid())
    def test_duplicate_element_rejected(self):
        with self.assertRaises(m.RecoveryError):m.parse_failed_accounting(self.accounting()+'\n'+self.accounting().splitlines()[0],os.getuid())
    def test_batch_steps_do_not_supply_element(self):
        with self.assertRaises(m.RecoveryError):m.parse_failed_accounting(self.accounting().replace('156877_0|','156877_0.batch|'),os.getuid())
    def test_other_success_rejected(self):
        with self.assertRaises(m.RecoveryError):m.parse_failed_accounting(self.accounting().replace('FAILED|1:0','COMPLETED|0:0',1),os.getuid())
    def test_specific_startup_memory_error(self):
        text='ValueError: Free memory on device (2.17/79.25 GiB) on startup is less than desired GPU memory utilization (0.9, 71.33 GiB).'
        self.assertEqual(m.memory_failure(text)['free_gib'],2.17)
    def test_generic_exit_is_not_memory_evidence(self):
        with self.assertRaises(m.RecoveryError):m.memory_failure('VLLM_EXITED_EARLY:1')
    def test_different_gpu_utilization_rejected(self):
        with self.assertRaises(m.RecoveryError):m.memory_failure('Free memory on device (2.17/79.25 GiB) on startup is less than desired GPU memory utilization (0.8, 63.4 GiB).')
    def test_contradictory_memory_evidence_rejected(self):
        with self.assertRaises(m.RecoveryError):m.memory_failure('Free memory on device (78.0/79.25 GiB) on startup is less than desired GPU memory utilization (0.9, 71.33 GiB).')
    def test_missing_or_empty_shards_allowed(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);m.require_no_shard_outputs(root)
            (root/'parallel_v1/shard_0/execution/t0').mkdir(parents=True)
            m.require_no_shard_outputs(root)
    def test_any_partial_attempt_is_preserved_and_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'parallel_v1/shard_0/execution/t0/attempts/c/attempt.json';p.parent.mkdir(parents=True);p.write_text('{}')
            with self.assertRaises(m.RecoveryError):m.require_no_shard_outputs(root)
            self.assertTrue(p.exists())
    def test_even_empty_receipt_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'parallel_v1/shard_2/execution/t2/cell_receipts.jsonl';p.parent.mkdir(parents=True);p.touch()
            with self.assertRaises(m.RecoveryError):m.require_no_shard_outputs(root)
    def test_symlink_shard_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);(root/'parallel_v1').mkdir();(root/'parallel_v1/shard_0').symlink_to('/tmp')
            with self.assertRaises(m.RecoveryError):m.require_no_shard_outputs(root)
    def test_command_only_adds_registered_exclusion(self):
        cmd=['sbatch','--parsable','--export=NIL','--array=0,1,2,3%4','--chdir=/old','/old/array_shard.sh','/old','/root','a'*64]
        out=m.with_exclusion(cmd)
        self.assertEqual([x for x in out if x!='--exclude=d1n41a18g03'],cmd)
    def test_no_arbitrary_command(self):
        with self.assertRaises(m.RecoveryError):m.with_exclusion(['bash','anything'])
    def test_no_duplicate_or_external_exclusion(self):
        with self.assertRaises(m.RecoveryError):m.with_exclusion(['sbatch','--exclude=other'])
    def test_native_worker_and_science_not_reimplemented(self):
        s=Path(m.__file__).read_text()
        self.assertIn('ad.load_worker_status(',s)
        self.assertIn('ad.consolidate(',s)
        self.assertIn('driver.finalize(',s)
        self.assertNotIn('def execute_shard(',s)
        self.assertNotIn('scancel',s)
        self.assertNotIn('pkill',s)
        self.assertNotIn('shutil.rmtree',s)

if __name__=='__main__':unittest.main()

class SubmissionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core,cls.ad,cls.jobs,cls.driver=m.load_original(Path(os.environ.get('RECOVERY_TEST_STAGE4E_ROOT',str(m.OLD_ROOT))))
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
        self.state=self.root/'state';self.state.mkdir();self.rec=self.state/'recovery';self.rec.mkdir()
        self.core.write_exact(self.rec/'RECOVERY_AUTHORIZATION.json',{'test':'fixture'})
        (self.root/'LAST_JOB_ID.txt').write_text(m.FAILED_ARRAY+'\n')
        self.cfg={'execution_root':str(self.root),'execution_log_root':str(self.root/'logs'),'authorization_sha256':'a'*64,'poll_seconds':0}
        self.plan={'plan_sha256':m.PLAN_SHA}
    def tearDown(self):self.tmp.cleanup()
    def submit(self,gen=2,shards=(0,1,2,3),prev=m.FAILED_ARRAY):
        return m.submit(self.core,self.ad,self.jobs,self.cfg,self.state,self.plan,self.rec,gen,shards,prev)
    def test_success_receipt_is_native_compatible_and_excluded(self):
        with patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,'2000\n','')) as run:
            out=self.submit()
        self.assertEqual(out,{'generation':2,'shards':[0,1,2,3],'job_id':'2000','plan_sha256':m.PLAN_SHA})
        self.assertIn('--exclude=d1n41a18g03',run.call_args.args[0])
        self.assertEqual((self.root/'LAST_JOB_ID.txt').read_text(),'2000\n')
    def test_exact_resume_does_not_resubmit(self):
        with patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,'2000','')):self.submit()
        with patch.object(m,'shell',side_effect=AssertionError('unexpected sbatch')):self.submit()
    def test_failed_submission_leaves_intent_and_cannot_retry(self):
        with patch.object(m,'shell',return_value=subprocess.CompletedProcess([],1,'','rejected')):
            with self.assertRaises(m.RecoveryError):self.submit()
        self.assertTrue((self.state/'SUBMISSION_2.intent.json').exists())
        with patch.object(m,'shell',side_effect=AssertionError('unexpected sbatch')):
            with self.assertRaises(m.RecoveryError):self.submit()
    def test_timeout_never_resubmits(self):
        with patch.object(m,'shell',side_effect=subprocess.TimeoutExpired('sbatch',90)):
            with self.assertRaises(m.RecoveryError):self.submit()
        with patch.object(m,'shell',side_effect=AssertionError('unexpected sbatch')):
            with self.assertRaises(m.RecoveryError):self.submit()
    def test_ambiguous_success_keeps_intent_without_receipt(self):
        with patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,'not a job','')):
            with self.assertRaises(ValueError):self.submit()
        self.assertFalse((self.state/'SUBMISSION_2.json').exists())
    def test_external_job_pointer_prevents_submit(self):
        (self.root/'LAST_JOB_ID.txt').write_text('9999')
        with patch.object(m,'shell',side_effect=AssertionError('unexpected sbatch')):
            with self.assertRaises(m.RecoveryError):self.submit()
    def test_resume_after_partial_generation_does_not_rewind_pointer(self):
        with patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,'2000','')):self.submit()
        with patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,'2001','')):self.submit(3,(2,),'2000')
        with patch.object(m,'shell',side_effect=AssertionError('unexpected sbatch')):self.submit()
        self.assertEqual((self.root/'LAST_JOB_ID.txt').read_text(),'2001\n')
    def test_new_failed_array_never_submits_partial_generation(self):
        with patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,'2000','')),patch.object(self.jobs,'query_array',return_value=('STOP','failure')):
            with self.assertRaisesRegex(m.RecoveryError,'RECOVERY_ARRAY_FAILED'):
                m.follow(self.core,self.ad,self.jobs,self.cfg,self.state,self.plan,self.rec)
        self.assertFalse((self.state/'SUBMISSION_3.intent.json').exists())

class ProofTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core,cls.ad,cls.jobs,cls.driver=m.load_original(Path(os.environ.get('RECOVERY_TEST_STAGE4E_ROOT',str(m.OLD_ROOT))))
    setUp=SubmissionTests.setUp
    tearDown=SubmissionTests.tearDown
    def fixture(self):
        (self.rec/'RECOVERY_AUTHORIZATION.json').unlink()
        from types import SimpleNamespace
        pkg=self.root/'package';pkg.mkdir();(pkg/'PACKAGE_FILES.sha256').write_text('fixture manifest')
        for label in ('t0','t2'):
            path=self.root/'execution'/label/'cell_receipts.jsonl';path.parent.mkdir(parents=True);path.write_text('fixture prefix\n')
        ledger=self.ad.ledger_shas(self.root)
        plan={**self.plan,'completed_prefix_count':102,'canonical_prefix_ledger_file_sha256s':ledger}
        self.core.write_exact(self.state/'PLAN.json',plan)
        self.core.write_exact(self.state/'SUBMISSION_0.json',{'generation':0,'shards':[0,1,2,3],'job_id':m.FAILED_ARRAY,'plan_sha256':m.PLAN_SHA})
        self.cfg['binding_root']=str(self.root/'binding');self.cfg['binding_sha256']='b'*64
        logs=Path(self.cfg['execution_log_root']);logs.mkdir()
        (self.root/'runtime').mkdir()
        for sid,job in enumerate(['156895','156896','156899','156877']):
            (logs/f'full_select_array_156877_{sid}.out').write_text(f'STAGE4D_ARRAY_NODE=d1n41a18g03 JOB={job} ARRAY=156877 SHARD={sid} CUDA_VISIBLE_DEVICES=0\n')
            (logs/f'full_select_array_156877_{sid}.err').write_text('wait_ready\nVLLM_EXITED_EARLY:1\n')
            base=self.root/'runtime'/f'vllm_{job}_shard{sid}'
            base.with_suffix('.out').write_text('Free memory on device (2.17/79.25 GiB) on startup is less than desired GPU memory utilization (0.9, 71.33 GiB).')
            base.with_suffix('.err').write_text('error')
            (base.parent/(base.name+'.command.json')).write_text('[]')
        fakead=SimpleNamespace(ledger_shas=self.ad.ledger_shas,existing_modules=lambda cfg:(SimpleNamespace(canonical_completed_prefix=lambda **kw:102),None,None,None))
        return pkg,plan,fakead
    def test_all_four_proof_checks_create_append_only_evidence(self):
        pkg,plan,ad=self.fixture()
        with patch.object(m,'ROOT',pkg),patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,RecoveryTests.accounting(self),'')):
            value=m.preflight(self.core,ad,self.cfg,self.state,plan,self.rec)
            self.assertEqual(len(value['failed_workers']),4)
            self.assertEqual(len(value['evidence_file_sha256s']),22)
            self.assertFalse(value['scientific_authorization_changed'])
            m.preflight(self.core,ad,self.cfg,self.state,plan,self.rec)
    def test_other_shard_log_required_not_assumed_from_first_two(self):
        pkg,plan,ad=self.fixture();(self.root/'runtime/vllm_156899_shard2.out').write_text('Different error')
        with patch.object(m,'ROOT',pkg),patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,RecoveryTests.accounting(self),'')):
            with self.assertRaises(m.RecoveryError):m.preflight(self.core,ad,self.cfg,self.state,plan,self.rec)
        self.assertFalse((self.rec/'RECOVERY_AUTHORIZATION.json').exists())
    def test_canonical_prefix_changed_refuses_before_accounting(self):
        pkg,plan,ad=self.fixture();(self.root/'execution/t0/cell_receipts.jsonl').write_text('changed')
        with patch.object(m,'ROOT',pkg),patch.object(m,'shell',side_effect=AssertionError('not reached')):
            with self.assertRaises(m.RecoveryError):m.preflight(self.core,ad,self.cfg,self.state,plan,self.rec)
    def test_any_scientific_completion_marker_blocks_recovery(self):
        pkg,plan,ad=self.fixture();(Path(self.cfg['execution_log_root'])/'full_select_array_156877_3.err').write_text('wait_ready VLLM_EXITED_EARLY:1 STAGE4D_SELECT_CELL_COMPLETE')
        with patch.object(m,'ROOT',pkg),patch.object(m,'shell',return_value=subprocess.CompletedProcess([],0,RecoveryTests.accounting(self),'')):
            with self.assertRaises(m.RecoveryError):m.preflight(self.core,ad,self.cfg,self.state,plan,self.rec)

class FinalFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.core,cls.ad,cls.jobs,cls.driver=m.load_original(Path(os.environ.get('RECOVERY_TEST_STAGE4E_ROOT',str(m.OLD_ROOT))))
    def test_graceful_partial_resumes_only_incomplete_shard(self):
        from types import SimpleNamespace
        calls=[]
        def sub(*args):
            generation,shards,prev=args[-3:];calls.append((generation,shards,prev));return {'job_id':str(2000+generation-2)}
        def status(cfg,state,plan,job,shard):
            complete=(shard!=2 or job=='2001')
            return {'assigned_pair_count':5,'t0_cell_count':5 if complete else 2,'t2_cell_count':5 if complete else 2,'complete':complete}
        ad=SimpleNamespace(load_worker_status=status)
        with patch.object(m,'submit',side_effect=sub),patch.object(self.jobs,'query_array',return_value=('COMPLETE','complete')):
            m.follow(self.core,ad,self.jobs,{'poll_seconds':0},Path('/not-used'),{},Path('/not-used'))
        self.assertEqual(calls,[(2,(0,1,2,3),'156877'),(3,(2,),'2000')])
    def test_actual_source_archival_is_idempotent_and_has_no_remote_write(self):
        with tempfile.TemporaryDirectory() as d:
            repo=Path(d)/'repo';repo.mkdir()
            def git(*args):
                return subprocess.run(['git','-C',str(repo),*args],check=True,text=True,capture_output=True).stdout.strip()
            git('init','-q');git('config','user.email','fixture@example.invalid');git('config','user.name','Fixture')
            git('commit','--allow-empty','-m','fixture')
            m.archive_source(self.core,self.driver,repo)
            head=git('rev-parse','HEAD')
            m.archive_source(self.core,self.driver,repo)
            self.assertEqual(git('rev-parse','HEAD'),head)
            self.assertEqual(git('status','--porcelain'),'')
            self.assertEqual(git('remote'),'')
