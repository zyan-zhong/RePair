"""Synthetic control-flow tests plus real Linux flock and original native locking.

No test executes a model, ALFWorld, scheduler write, publication, or live audit.
"""
from __future__ import annotations
import copy
import fcntl
import importlib
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import continue_closeout as m

REUSED_ROOT = Path(os.environ.get('STAGE4E_TEST_PACKAGES_ROOT', str(m.SCRIPTS)))
OLD = REUSED_ROOT / m.OLD_NAME
FULL = REUSED_ROOT / m.FULL_NAME
sys.path[:0] = [str(OLD), str(FULL)]
core = importlib.import_module('stage4e')
live = importlib.import_module('stage4d_full.live')


class LockRegressionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.lock_path = self.root / 'full_select_execution.lock'

    def native(self):
        context = {'legacy': types.SimpleNamespace(load_receipts=lambda p: []), 'bundles': {}}
        with patch.object(live, '_prepare_live_context', return_value=context), \
             patch.object(live, '_canonical_prefix', return_value=0), \
             patch.object(live, 'EXPECTED_PAIR_CELLS', 0), \
             patch.object(live, 'EXPECTED_TOTAL_CELLS', 0):
            return live.consolidate_shards(execution_root=self.root, binding_root=self.root, completed_prefix_count=0)

    def test_original_double_open_reproduces_reported_stop(self):
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with self.assertRaisesRegex(live.Stage4DFullError, 'FULL_SELECT_CONSOLIDATION_ALREADY_ACTIVE'):
                self.native()
        finally:
            os.close(fd)

    def test_fixed_handoff_lets_original_native_function_own_lock(self):
        called = []
        ad = types.SimpleNamespace(consolidate=lambda *args: called.append(self.native()))
        m.consolidate_single_owner(ad, {}, self.root, {})
        self.assertEqual(len(called), 1)
        self.assertTrue(called[0]['complete'])
        fd = os.open(self.lock_path, os.O_RDWR)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(fd)

    def test_real_native_lock_still_blocks_a_separate_process(self):
        checks = []
        code = "import fcntl,os,sys; f=os.open(sys.argv[1],os.O_RDWR); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"
        def load(_):
            result = subprocess.run([sys.executable, '-c', code, str(self.lock_path)], capture_output=True)
            checks.append(result.returncode)
            return []
        context = {'legacy': types.SimpleNamespace(load_receipts=load), 'bundles': {}}
        with patch.object(live, '_prepare_live_context', return_value=context), \
             patch.object(live, '_canonical_prefix', return_value=0), \
             patch.object(live, 'EXPECTED_PAIR_CELLS', 0), \
             patch.object(live, 'EXPECTED_TOTAL_CELLS', 0):
            live.consolidate_shards(execution_root=self.root, binding_root=self.root, completed_prefix_count=0)
        self.assertTrue(checks)
        # The final two count reads are deliberately after native lock release.
        self.assertTrue(all(rc != 0 for rc in checks[:-2]))
        self.assertEqual(checks[-2:], [0, 0])

    def test_driver_mutex_is_still_exclusive_and_file_is_not_deleted(self):
        path = self.root / 'driver.lock'
        with m.driver_mutex(path):
            with self.assertRaisesRegex(m.ContinuationError, 'EXISTING_STAGE4E_DRIVER_ACTIVE'):
                with m.driver_mutex(path):
                    self.fail('entered twice')
        self.assertTrue(path.is_file())
        with m.driver_mutex(path):
            pass

    def test_driver_mutex_does_not_follow_symlink(self):
        (self.root / 'target').touch()
        link = self.root / 'driver.lock'
        link.symlink_to(self.root / 'target')
        with self.assertRaises((m.ContinuationError, OSError)):
            with m.driver_mutex(link):
                self.fail('followed symlink')

    def test_consolidation_failure_is_not_swallowed(self):
        def fail(*args):
            raise ValueError('exact attempt validation failed')
        with self.assertRaisesRegex(ValueError, 'exact attempt'):
            m.consolidate_single_owner(types.SimpleNamespace(consolidate=fail), {}, self.root, {})


class DependencyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.state = self.root / 'parallel_v1/independent_jobs_v1'
        self.state.mkdir(parents=True)
        self.recovery_root = self.state / 'node_recovery_156877_v1'
        self.recovery_root.mkdir()
        core.write_exact(self.recovery_root / 'RECOVERY_AUTHORIZATION.json', {'preserved': True})
        (self.root / 'LAST_JOB_ID.txt').write_text(m.ARRAY_ID + '\n')
        self.cfg = {'execution_root': str(self.root), 'execution_log_root': str(self.root/'logs'),
                    'authorization_sha256': m.AUTH_SHA}
        self.plan = {'plan_sha256': m.PLAN_SHA}
        self.recovery = types.SimpleNamespace(OLD_ROOT=OLD, FAILED_ARRAY='156877',
            with_exclusion=lambda x: [x[0], '--exclude=d1n41a18g03', *x[1:]])
        self.jobs = types.SimpleNamespace(
            submission_command=lambda *args: ['sbatch', '--array=0,1,2,3%4', 'old_array_shard.sh'],
            query_array=lambda *args: ('COMPLETE', 'all four complete'),
            incomplete_shards=lambda statuses: tuple(i for i, s in statuses.items() if not s['complete']))
        self.loads = []
        def load(*args):
            self.loads.append(args[-1]); return {'complete': True}
        self.ad = types.SimpleNamespace(load_worker_status=load)
        core.write_exact(self.state/'SUBMISSION_2.json', {'generation': 2, 'shards': [0,1,2,3],
            'job_id': m.ARRAY_ID, 'plan_sha256': m.PLAN_SHA})
        self.intent = {'generation': 2, 'shards': [0,1,2,3], 'plan_sha256': m.PLAN_SHA,
            'command': ['sbatch','--exclude=d1n41a18g03','--array=0,1,2,3%4','old_array_shard.sh'],
            'authorization_sha256': m.AUTH_SHA,
            'recovery_authorization_file_sha256': core.file_sha(self.recovery_root/'RECOVERY_AUTHORIZATION.json'),
            'predecessor_array_job_id': '156877', 'excluded_nodes': ['d1n41a18g03']}
        core.write_exact(self.state/'SUBMISSION_2.intent.json', self.intent)

    def verify(self):
        return m.verify_completed_recovery(core, self.ad, self.jobs, self.recovery,
            self.cfg, self.state, self.plan, self.recovery_root)

    def test_exact_completed_array_and_four_native_statuses_are_required(self):
        self.assertEqual(self.verify()['array_job_id'], m.ARRAY_ID)
        self.assertEqual(self.loads, [0,1,2,3])

    def test_running_or_unknown_or_failed_array_never_reads_shard_outcomes(self):
        for state in ('WAIT', 'UNKNOWN', 'STOP'):
            with self.subTest(state=state), patch.object(self.jobs, 'query_array', return_value=(state,state)):
                with self.assertRaises(m.ContinuationError): self.verify()
        self.assertEqual(self.loads, [])

    def test_graceful_partial_does_not_trigger_submission(self):
        self.ad.load_worker_status = lambda *args: {'complete': args[-1] != 2}
        with self.assertRaisesRegex(m.ContinuationError, 'SHARDS_NOT_FULLY_COMPLETE'):
            self.verify()

    def test_new_job_pointer_stops(self):
        (self.root/'LAST_JOB_ID.txt').write_text('999999\n')
        with self.assertRaisesRegex(m.ContinuationError, 'JOB_POINTER_CHANGED'): self.verify()

    def test_unexpected_later_submission_stops(self):
        core.write_exact(self.state/'SUBMISSION_3.intent.json', {'unknown':True})
        with self.assertRaisesRegex(m.ContinuationError, 'UNEXPECTED_SUBMISSION'): self.verify()

    def test_submission_array_identity_changed_stops(self):
        p=self.state/'SUBMISSION_2.json';v=core.read_json(p);v['job_id']='1234'
        p.write_bytes(core.canonical(v)+b'\n')
        with self.assertRaisesRegex(m.ContinuationError, 'SUBMISSION_IDENTITY_CHANGED'): self.verify()

    def test_intent_changed_stops(self):
        p=self.state/'SUBMISSION_2.intent.json';v=copy.deepcopy(self.intent);v['excluded_nodes']=[]
        p.write_bytes(core.canonical(v)+b'\n')
        with self.assertRaisesRegex(m.ContinuationError, 'SUBMISSION_INTENT_CHANGED'): self.verify()

    def test_missing_native_status_is_not_assumed_success(self):
        def load(*args): raise FileNotFoundError('missing native status')
        self.ad.load_worker_status = load
        with self.assertRaises(FileNotFoundError): self.verify()


class ScopeTests(unittest.TestCase):
    def test_existing_packages_and_manifest_verification_are_reused(self):
        recovery, c, ad, jobs, driver = m.load_dependencies(REUSED_ROOT)
        self.assertEqual(recovery.PLAN_SHA, m.PLAN_SHA)
        self.assertTrue(Path(ad.__file__).is_relative_to(OLD))
        self.assertEqual(c.file_sha(recovery.ROOT/'PACKAGE_FILES.sha256'), m.RECOVERY_MANIFEST_SHA)

    def test_no_model_execution_no_new_stage5_code_no_lock_deletion(self):
        text=Path(m.__file__).read_text()
        for token in ('subprocess.run(', 'os.unlink(', '.unlink(', 'shutil.rmtree(', 'os.replace(',
                      'follow(', 'recovery.submit(', 'driver.follow(', 'execute_shard('):
            self.assertNotIn(token, text)
        self.assertIn('ad.consolidate(cfg, state, plan)', text)
        self.assertIn('driver.finalize(cfg, control, repo, active)', text)
        self.assertNotIn('flock(lock_fd', text)



class MainControlFlowTests(unittest.TestCase):
    """Only the transition control is synthetic; controller locking uses real flock."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name); self.control=self.root/'control';self.control.mkdir()
        self.state=self.root/'parallel_v1/independent_jobs_v1'; self.state.mkdir(parents=True)
        rr=self.state/'node_recovery_156877_v1';rr.mkdir()
        for path in (self.control/'SOURCE_PREPARATION.json', self.state/'PLAN.json', rr/'RECOVERY_AUTHORIZATION.json'):
            core.write_exact(path, {})
        self.cfg={'execution_root': str(self.root), 'control_root': str(self.control)}
        self.events=[]
        self.rcv=types.SimpleNamespace(RECOVERY_REL='node_recovery_156877_v1',
            preflight=lambda *args:self.events.append('proof'))
        self.ad=types.SimpleNamespace(STATE_REL='parallel_v1/independent_jobs_v1',
            freeze_plan=lambda *args:{'plan_sha256':m.PLAN_SHA})
        self.driver=types.SimpleNamespace(COMPLETE='COMPLETE.json',
            base_gate=lambda *args:self.events.append('base'),
            prepare=lambda *args:(self.root/'active',self.root/'repo'),
            finalize=lambda *args:self.events.append('finalize'))
        def consolidate(*args):
            self.events.append('consolidate'); core.write_exact(self.root/'COMPLETE.json',{'done': True})
        self.ad.consolidate=consolidate
        self.proxy=types.SimpleNamespace(**{name:getattr(core,name) for name in (
            'regular','write_exact','file_sha')})
        self.proxy.verify_inventory=lambda *args:{}
        self.proxy.read_json=lambda path:self.cfg
        (self.root/'PACKAGE_FILES.sha256').write_text('test inventory\n')
        self.check=lambda *args: {'array_job_id':m.ARRAY_ID}

    def runmain(self, *args):
        audit=importlib.import_module('stage4e.audit')
        with patch.object(m,'ROOT',self.root), \
             patch.object(m,'load_dependencies',return_value=(self.rcv,self.proxy,self.ad,None,self.driver)), \
             patch.object(m,'verify_completed_recovery',side_effect=self.check), \
             patch.object(m,'archive_adapter',side_effect=lambda *a:self.events.append('archive')), \
             patch.object(audit,'completion_gate',side_effect=lambda *a:self.events.append('completion_gate')):
            return m.main(list(args))

    def test_completed_flow_runs_original_consolidation_before_audit_publication(self):
        self.assertEqual(self.runmain(),0)
        self.assertEqual(self.events,['base','proof','consolidate','completion_gate','archive','finalize'])
        self.assertTrue((self.control/'SINGLE_OWNER_CONTINUATION.json').exists())

    def test_check_only_never_consolidates_archives_or_publishes(self):
        self.assertEqual(self.runmain('--check-only'),0)
        self.assertEqual(self.events,['base','proof'])
        self.assertFalse((self.control/'SINGLE_OWNER_CONTINUATION.json').exists())

    def test_dependency_failure_never_consolidates_or_publishes(self):
        def fail(*args): raise m.ContinuationError('not complete')
        self.check=fail
        with self.assertRaises(m.ContinuationError): self.runmain()
        self.assertEqual(self.events,['base','proof'])

    def test_already_published_only_calls_original_remote_reverification(self):
        core.write_exact(self.control/'FINAL_PUBLICATION_RECEIPT.json',{'exists':True})
        self.assertEqual(self.runmain(),0)
        self.assertEqual(self.events,['base','proof','finalize'])

    def test_native_consolidation_error_never_enters_result_audit(self):
        def fail(*args): raise ValueError('original validation rejected data')
        self.ad.consolidate=fail
        with self.assertRaises(ValueError): self.runmain()
        self.assertEqual(self.events,['base','proof'])

if __name__=='__main__': unittest.main()
