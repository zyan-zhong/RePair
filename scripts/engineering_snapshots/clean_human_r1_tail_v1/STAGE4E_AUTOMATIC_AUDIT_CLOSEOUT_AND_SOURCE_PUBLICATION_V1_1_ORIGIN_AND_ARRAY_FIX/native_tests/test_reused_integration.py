"""Real native validators with synthetic data; never a GPU/environment/provider run."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

ROOT=Path(os.environ['STAGE4E_TEST_REPO'])
FULL=Path(os.environ['STAGE4E_TEST_FULL_PACKAGE'])
sys.path.insert(0,str(ROOT/'src'))
sys.path.insert(0,str(ROOT/'scripts/engineering_snapshots/stage0/human_pilot_stage0_offoff_execution_and_closeout_v1_9'))

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,path)
    m=importlib.util.module_from_spec(spec);sys.modules[name]=m;spec.loader.exec_module(m);return m

class NativeIntegrationTests(unittest.TestCase):
    def test_actual_authorization_contract_file_and_signatures(self):
        from stage4e.driver import check_authorization
        m=load(FULL/'stage4d_full/contract.py','_real_stage4d_contract')
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);b=m.EXPECTED_BINDING_ROOT
            auth=m.authorization_payload(binding_root=b,readiness_receipt_sha256=m.EXPECTED_READINESS_RECEIPT_SHA256)
            (r/'STAGE4D_FULL_SELECT_EXECUTION_AUTHORIZATION_V1.json').write_bytes(m.canonical_json_bytes(auth)+b'\n')
            check_authorization(m,b,r,m.EXPECTED_READINESS_RECEIPT_SHA256,m.authorization_sha(auth))
            with self.assertRaises(ValueError):check_authorization(m,b,r,m.EXPECTED_READINESS_RECEIPT_SHA256,'0'*64)
    def test_stage4e_uses_actual_native_identity_chain(self):
        from stage4e.audit import audit_loaded_cell
        from pchsi.evaluation.select_result_audit import audit_select_cell_identity_chain
        fixture=load(ROOT/'tests/evaluation/test_p4_select_execution_compat_v1.py','_native_select_fixture')
        e,p,r,rs,call,trace,episode=fixture._select_final_audit_fixture(response_model_name='P4-R1-Q2-BAD-TRAIN17')
        loaded=SimpleNamespace(episode_artifact=episode,policy_calls=(call,),traces=(SimpleNamespace(provenance=trace),),
                               attempt_bundle=SimpleNamespace(attempt_bundle_sha256='a'*64))
        row={'execution_attempt_id':episode.execution_attempt_id,'attempt_bundle_sha256':'a'*64,
             'success':episode.success,'termination_reason':episode.termination_reason}
        audit_loaded_cell(native={'audit_select_cell_identity_chain':audit_select_cell_identity_chain},loaded=loaded,
            row=row,expected=e,condition=p,runtime=r,runtime_sha=rs,request_sha=None)
        with self.assertRaises(ValueError):
            audit_loaded_cell(native={'audit_select_cell_identity_chain':audit_select_cell_identity_chain},loaded=loaded,
              row={**row,'success':True},expected=e,condition=p,runtime=r,runtime_sha=rs,request_sha=None)
    def test_existing_i1_wire_checks_real_evaluator_artifacts(self):
        m=load(ROOT/'tests/evaluation/test_select_i1_explicit_binding.py','_native_i1_fixture')
        with tempfile.TemporaryDirectory() as d:
            m.test_audit_checks_original_prompt_factory_and_request_bytes(Path(d))
    def test_native_aggregator_then_clean_projection(self):
        from stage0.result_audit import aggregate_paired_results
        from stage4e import project_paired_summary
        p=({'manifest_index':0,'task_id':'synthetic-train','seed':17,'success':False},)
        c=({**p[0],'success':True},)
        r=aggregate_paired_results(parent_receipts=p,candidate_receipts=c,expected_task_count=1,expected_seeds=(17,))
        value=project_paired_summary(r,round_id='synthetic-clean',evidence_sha='a'*64)
        self.assertEqual(value['mean_task_success_rate_delta'],1.0)
        self.assertNotIn('PILOT_ENGINEERING_ROUND',str(value));self.assertNotIn('task_results',value)
    def test_native_disposition_and_next_round_keep_parent(self):
        from pchsi.round_control.promotion import freeze_promotion_decision
        from pchsi.round_control.next_round import freeze_next_round_creation
        d=freeze_promotion_decision(round_id='r',decision='ROLLBACK',decision_rule_id='DIAGNOSTIC_NOT_ELIGIBLE',
            evidence_access_class='TRAIN_SELECT',evidence_sha256='a'*64,parent_policy_id='pi0',candidate_policy_id='t2')
        n=freeze_next_round_creation(closed_round_id='r',next_round_id='r2',promotion_decision=d)
        self.assertEqual(d.next_parent_policy_id,'pi0')
        self.assertEqual(n.to_dict()['next_parent_policy_id'],'pi0')
