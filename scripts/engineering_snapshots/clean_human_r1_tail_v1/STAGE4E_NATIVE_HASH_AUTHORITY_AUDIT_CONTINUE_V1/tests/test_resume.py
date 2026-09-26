"""Offline resumption wiring and lock tests. No scheduler or publication call."""
from __future__ import annotations
import ast
import fcntl
import hashlib
import importlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
SCRIPTS=Path('/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts')
OLD=Path(os.environ.get('STAGE4E_HASH_TEST_OLD',str(SCRIPTS/'STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX')))
sys.path[:0]=[str(ROOT),str(OLD)]
from stage4e import GateError


def r():return importlib.import_module('resume')


class ResumeTests(unittest.TestCase):
    def test_unknown_driver_bytes_not_adopted(self):
        with self.assertRaisesRegex(GateError,'ORIGINAL_DRIVER_CHANGED'):
            r().corrected_driver_source((OLD/'stage4e/driver.py').read_bytes()+b'\n')

    def test_driver_adapter_changes_only_audit_subprocess_entry(self):
        raw=(OLD/'stage4e/driver.py').read_bytes()
        out=r().corrected_driver_source(raw)
        self.assertEqual(out.replace(r().AUDIT_COMMAND_NEW,r().AUDIT_COMMAND_OLD,1),raw.decode())
        self.assertEqual((OLD/'stage4e/driver.py').read_bytes(),raw)
        self.assertIn("publish_atomic(repo=repo",out)
        self.assertIn('base_gate(cfg)',out)

    def test_loaded_driver_keeps_old_root_and_original_publication(self):
        from native_hash_bridge import load_corrected_audit
        audit=load_corrected_audit(OLD)
        driver=r().load_corrected_driver(OLD,audit)
        self.assertEqual(driver.ROOT,OLD)
        self.assertIs(driver.execute_audit,audit.execute_audit)
        self.assertEqual(driver.PUBLIC_RESULTS,importlib.import_module('stage4e.driver').PUBLIC_RESULTS)
        self.assertIs(driver.publish_atomic,importlib.import_module('stage4e.source').publish_atomic)

    def test_original_finalize_launches_corrected_audit_child(self):
        from native_hash_bridge import load_corrected_audit
        driver=r().load_corrected_driver(OLD,load_corrected_audit(OLD))
        captured=[]
        class ChildReached(Exception):pass
        def stop_command(command,**kw):
            captured.append((command,kw));raise ChildReached
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)
            with patch.object(driver,'base_gate',return_value=p),patch.object(driver,'run',side_effect=stop_command):
                with self.assertRaises(ChildReached):driver.finalize({'python':'/test/python'},p,p,p)
        self.assertEqual(captured[0][0],['/test/python',str(ROOT/'resume.py'),'audit-once','--control',str(p),'--repo',str(p)])
        self.assertEqual(captured[0][1]['cwd'],OLD)

    def test_unknown_control_or_repo_never_used(self):
        cfg={'control_root':'/exact/control','integration_repo':'/exact/repo'}
        for control,repo in [('/other',None),(None,'/other')]:
            with self.assertRaisesRegex(GateError,'ROOT_CHANGED'):
                r().validate_requested_paths(cfg,control,repo)
        self.assertEqual(r().validate_requested_paths(cfg,None,None),(Path('/exact/control'),Path('/exact/repo')))

    def test_no_new_scheduler_submission_consolidation_or_model_calls(self):
        source=(ROOT/'resume.py').read_text()
        tree=ast.parse(source)
        calls={getattr(n.func,'attr',getattr(n.func,'id','')) for n in ast.walk(tree) if isinstance(n,ast.Call)}
        for name in ('consolidate','consolidate_shards','follow','execute_shard','run_single_episode','Popen'):
            self.assertNotIn(name,calls)
        for text in ('sbatch','scancel','srun'):
            self.assertNotIn(text,source)

    def test_existing_driver_lock_is_respected_not_deleted(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'driver.lock'
            with r().driver_mutex(p):
                inode=p.stat().st_ino
                with self.assertRaisesRegex(GateError,'DRIVER_ACTIVE'):
                    with r().driver_mutex(p):pass
            self.assertEqual(inode,p.stat().st_ino)
            with r().driver_mutex(p):pass

    def test_driver_lock_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as d:
            q=Path(d)/'real';q.write_text('unchanged')
            p=Path(d)/'driver.lock';p.symlink_to(q)
            with self.assertRaises(OSError):
                with r().driver_mutex(p):pass
            self.assertEqual(q.read_text(),'unchanged')


class CompletionHandoffTests(unittest.TestCase):
    def fixture(self,base):
        import stage4e as core
        from stage4e import audit
        root=base/'execution_root';control=base/'control';control.mkdir();root.mkdir()
        cfg={'execution_root':str(root),'authorization_sha256':r().AUTH_SHA,'binding_sha256':r().BINDING_SHA,'readiness_sha256':'c'*64,'pair_count':1775}
        completion={'schema_id':'STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1','schema_version':1,
            'authorization_sha256':r().AUTH_SHA,'binding_sha256':r().BINDING_SHA,'readiness_receipt_sha256':'c'*64,
            'scientific_execution_complete':True,'t0_condition_cell_count':1775,'t2_condition_cell_count':1775,
            'paired_task_seed_cell_count':1775,'total_condition_cell_count':3550,'result_interpretation_authorized':False,
            'promotion_authorized':False,'next_gate':'STAGE4E_EXISTING_SELECT_RESULT_AUDIT'}
        core.write_exact(root/audit.COMPLETE,completion)
        for label in ('t0','t2'):
            file=root/'execution'/label/'cell_receipts.jsonl';file.parent.mkdir(parents=True);file.write_bytes(b'SYNTHETIC-LEDGER-FOR-HANDOFF-CHECK-ONLY\n')
        from stage4e.array_driver import ledger_shas
        h=core.file_sha(root/audit.COMPLETE)
        core.write_exact(control/'SINGLE_OWNER_CONTINUATION.json',{'array_job_id':'156934','native_shard_statuses_verified':4,'completion_file_sha256':h})
        core.write_exact(root/'parallel_v1/independent_jobs_v1/ARRAY_CONSOLIDATION_RECEIPT.json',{'canonical_completion_file_sha256':h,'canonical_ledger_file_sha256s':ledger_shas(root)})
        return core,audit,cfg,control,root

    def test_exact_existing_completion_handoff_accepted(self):
        with tempfile.TemporaryDirectory() as d:
            core,audit,cfg,c,root=self.fixture(Path(d))
            x=r().verify_completed_handoff(core,audit,cfg,c)
            self.assertEqual(x['total_condition_cell_count'],3550)

    def test_mutated_ledger_stops_before_audit(self):
        with tempfile.TemporaryDirectory() as d:
            core,audit,cfg,c,root=self.fixture(Path(d))
            (root/'execution/t0/cell_receipts.jsonl').write_bytes(b'MUTATED\n')
            with self.assertRaisesRegex(GateError,'CANONICAL_LEDGERS_CHANGED'):
                r().verify_completed_handoff(core,audit,cfg,c)

    def test_partial_completion_still_refused(self):
        import json
        with tempfile.TemporaryDirectory() as d:
            core,audit,cfg,c,root=self.fixture(Path(d))
            p=root/audit.COMPLETE;x=core.read_json(p);x['total_condition_cell_count']=204;p.write_text(json.dumps(x))
            with self.assertRaisesRegex(GateError,'COMPLETION_CONTRACT_MISMATCH'):
                r().verify_completed_handoff(core,audit,cfg,c)

    def test_missing_predecessor_handoff_is_not_invented(self):
        with tempfile.TemporaryDirectory() as d:
            core,audit,cfg,c,root=self.fixture(Path(d));(c/'SINGLE_OWNER_CONTINUATION.json').unlink()
            with self.assertRaisesRegex(GateError,'NOT_REGULAR_FILE'):
                r().verify_completed_handoff(core,audit,cfg,c)

    def test_wrong_experiment_is_not_adopted(self):
        with tempfile.TemporaryDirectory() as d:
            core,audit,cfg,c,root=self.fixture(Path(d));cfg['authorization_sha256']='a'*64
            with self.assertRaisesRegex(GateError,'REGISTERED_EXPERIMENT_CHANGED'):
                r().verify_completed_handoff(core,audit,cfg,c)

if __name__=='__main__':unittest.main()
