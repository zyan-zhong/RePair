from __future__ import annotations
import importlib
import json
from pathlib import Path
import tempfile
import unittest

class Contracts(unittest.TestCase):
    def core(self):
        import stage4e
        self.assertTrue(hasattr(stage4e, 'strict_loads'), 'MISSING_STAGE4E_OUTCOME_GATED_ADAPTERS')
        return stage4e

    def test_strict_duplicate_keys_rejected(self):
        c=self.core()
        with self.assertRaises(ValueError): c.strict_loads('{"a":1,"a":2}')

    def test_nonfinite_json_rejected(self):
        c=self.core()
        for text in ('{"a":NaN}', '{"a":Infinity}'):
            with self.assertRaises(ValueError): c.strict_loads(text)

    def test_no_clobber_and_exact_resume(self):
        c=self.core()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'result.json'
            c.write_exact(p, {'a':1})
            before=p.read_bytes()
            c.write_exact(p, {'a':1})
            self.assertEqual(before,p.read_bytes())
            with self.assertRaises(ValueError): c.write_exact(p, {'a':2})

    def test_symlink_output_rejected(self):
        c=self.core()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'actual';p.write_text('x');q=Path(d)/'link';q.symlink_to(p)
            with self.assertRaises(ValueError): c.write_exact(q, {'a':1})
            self.assertEqual(p.read_text(),'x')

    def test_completion_requires_full_counts_not_just_slurm_zero(self):
        c=self.core()
        for val in ({}, {'scientific_execution_complete':True,'t0_condition_cell_count':1,'t2_condition_cell_count':1}):
            with self.assertRaises(ValueError): c.validate_completion(val, auth_sha='a'*64,binding_sha='b'*64,readiness_sha='c'*64,pair_count=3)
        value={'schema_id':'STAGE4D_FULL_SELECT_EXECUTION_COMPLETE_V1','schema_version':1,
               'authorization_sha256':'a'*64,'binding_sha256':'b'*64,'readiness_receipt_sha256':'c'*64,
               'scientific_execution_complete':True,'t0_condition_cell_count':3,'t2_condition_cell_count':3,
               'paired_task_seed_cell_count':3,'total_condition_cell_count':6,
               'result_interpretation_authorized':False,'promotion_authorized':False,
               'next_gate':'STAGE4E_EXISTING_SELECT_RESULT_AUDIT'}
        c.validate_completion(value,auth_sha='a'*64,binding_sha='b'*64,readiness_sha='c'*64,pair_count=3)
        for key,v in [('t0_condition_cell_count',True),('promotion_authorized',True),('binding_sha256','d'*64)]:
            with self.assertRaises(ValueError): c.validate_completion({**value,key:v},auth_sha='a'*64,binding_sha='b'*64,readiness_sha='c'*64,pair_count=3)

    def test_summary_projection_removes_all_per_task_content(self):
        c=self.core()
        x={'unique_task_count':2,'paired_cell_count':10,'total_condition_cell_count':20,
           'replicate_seeds':[17,31,47,73,101], 'parent_success_cells':2,'candidate_success_cells':3,
           'both_success_cells':1,'both_failure_cells':6,'parent_only_success_cells':1,'candidate_only_success_cells':2,
           'mean_task_success_rate_delta':.1,'task_results':[{'task_id':'SECRET_TASK','observation':'SECRET_OBS'}],
           'round_role':'PILOT_ENGINEERING_ROUND_V1','promotion_eligible':True}
        v=c.project_paired_summary(x,round_id='round1',evidence_sha='a'*64)
        self.assertNotIn('SECRET_',json.dumps(v))
        self.assertNotIn('task_results',v)
        self.assertEqual(v['primary_statistical_unit'],'unique_task')
        self.assertEqual(v['mean_task_success_rate_delta'],.1)
        self.assertFalse(v['promotion_eligible'])
        self.assertNotIn('PILOT_ENGINEERING_ROUND_V1',json.dumps(v))

    def test_diagnostic_retention_independent_of_score_direction(self):
        c=self.core()
        for delta in (-1.,0.,1.):
            v=c.diagnostic_disposition(protocol={'promotion_eligible':False},
                candidate={'promotion_eligible':False,'run_manifest':{'diagnostic_only':True,'promotion_eligible':False}},
                delta=delta)
            self.assertEqual(v['decision'],'ROLLBACK')
            self.assertEqual(v['reason'],'PREREGISTERED_DIAGNOSTIC_NOT_PROMOTION_ELIGIBLE')
            self.assertFalse(v['performance_based_promotion'])

    def test_no_guess_for_other_training_arm(self):
        c=self.core()
        with self.assertRaises(ValueError): c.diagnostic_disposition(protocol={'promotion_eligible':True},candidate={'promotion_eligible':True,'run_manifest':{'diagnostic_only':False}},delta=1.)

    def test_failed_or_unknown_job_does_not_authorize_audit_or_retry(self):
        c=self.core()
        for state in ('FAILED','TIMEOUT','NODE_FAIL','UNKNOWN'):
            self.assertEqual(c.next_operation(state=state,completion_present=False,graceful_partial=False,resume_count=0,max_resumptions=1),'STOP')
        self.assertEqual(c.next_operation(state='RUNNING',completion_present=True,graceful_partial=False,resume_count=0,max_resumptions=1),'WAIT')
        self.assertEqual(c.next_operation(state='COMPLETED',completion_present=True,graceful_partial=False,resume_count=0,max_resumptions=1),'AUDIT')
        self.assertEqual(c.next_operation(state='COMPLETED',completion_present=False,graceful_partial=True,resume_count=0,max_resumptions=1),'RESUME_EXISTING')
        self.assertEqual(c.next_operation(state='COMPLETED',completion_present=False,graceful_partial=True,resume_count=1,max_resumptions=1),'STOP')

    def test_inventory_rejects_path_traversal(self):
        c=self.core()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'pkg';root.mkdir();(root/'PACKAGE_FILES.sha256').write_text('a'*64+'  ../outside\n')
            with self.assertRaises(ValueError): c.verify_inventory(root,'PACKAGE_FILES.sha256')

    def test_sha_bytes_and_semantics_not_interchanged(self):
        c=self.core()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'x.json';p.write_text('{"a":1}\n')
            self.assertNotEqual(c.file_sha(p),c.semantic_sha(c.read_json(p)))

if __name__=='__main__': unittest.main()
