from __future__ import annotations
import contextlib, copy, hashlib, importlib.util, io, json, os, subprocess, sys, tempfile, unittest, zipfile
from pathlib import Path
from unittest.mock import patch

HERE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(HERE))
import freeze_select as f
import run_freeze as r

class ApprovalBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.files=f.read_review(HERE/'tests/fixtures/SELECT_PREFLIGHT_REVIEW.zip','e8263e5a9604a85d831187938b6938f721f76e9163da6f5025398d1c32d4db27')
        self.data=f.validate_review(self.files)
        self.raw=(HERE/'decisions/current_protocol_decision.json').read_bytes()
        self.d=json.loads(self.raw)
    def test_missing_cells_not_allowed_as_failure(self):
        self.d['missingness_policy']['missing_infrastructure_cells_must_not_be_scored_as_failure']=False
        with self.assertRaisesRegex(ValueError,'MISSINGNESS'):
            f.make_protocol(self.data,self.d,'d'*64,'a'*40,'b'*40,'c'*64)
    def test_missingness_cannot_enable_auto_retry(self):
        self.d['missingness_policy']['automatic_policy_change_or_retry_authorized']=True
        with self.assertRaisesRegex(ValueError,'MISSINGNESS'):
            f.make_protocol(self.data,self.d,'d'*64,'a'*40,'b'*40,'c'*64)
    def test_measurement_does_not_inflate_seed_denominator(self):
        self.d['measurement']['seed_replicates_are_not_independent_tasks']=False
        with self.assertRaisesRegex(ValueError,'MEASUREMENT'):
            f.make_protocol(self.data,self.d,'d'*64,'a'*40,'b'*40,'c'*64)
    def test_freeze_receipt_does_not_overwrite_proposal_flags(self):
        protocol=f.make_protocol(self.data,self.d,'d'*64,'a'*40,'b'*40,'c'*64)
        self.assertTrue(protocol['protocol_frozen'])
        self.assertFalse(protocol['grid']['protocol_frozen'])
        self.assertFalse(protocol['grid']['execution_authorized'])
        self.assertEqual(protocol['model_binding'],self.data['model'])

    def test_current_primary_uses_existing_resolver(self):
        cfg={'authority_context':{'phase':'HUMAN_PRIMARY_STRONG_SHADOW','takeover_evaluation':None}}
        r.authorize(self.d,cfg)
        self.d['decision_actor']='STRONG'
        with self.assertRaisesRegex(ValueError,'NOT_REGISTERED_PRIMARY'):r.authorize(self.d,cfg)
    def test_no_approval_returns_before_commit_or_live(self):
        cfg=json.loads((HERE/'current_request.json').read_bytes())
        # External HPC filesystem is substituted only at its read boundary.
        with patch.object(r,'verify_delivery'), patch.object(r,'dependencies',return_value=(None,)*5), \
             patch.object(f,'read_review',return_value=self.files), patch.object(f,'freeze_code') as commit, \
             patch.object(r,'verify_server_inputs') as verify, patch.object(sys,'argv',['run_freeze.py']), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(r.main(),20)
        commit.assert_not_called();verify.assert_not_called()
    def test_bad_approval_never_commits(self):
        with patch.object(r,'verify_delivery'), patch.object(r,'dependencies',return_value=(None,)*5), \
             patch.object(f,'read_review',return_value=self.files), patch.object(f,'freeze_code') as commit, \
             patch.object(sys,'argv',['run_freeze.py','--approve-decision','0'*64]):
            with self.assertRaisesRegex(ValueError,'DECISION_APPROVAL'):r.main()
        commit.assert_not_called()
    def test_unavailable_real_regression_dependency_fails_without_reconstruction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);code=root/'code';c=code/'configs/memory/package_b_failure_memory_dependency_v1.json';c.parent.mkdir(parents=True)
            c.write_text(json.dumps({'active_snapshot_external_directory':str(root/'absent'),'a9_dependency_audit_external_path':str(root/'a9')}))
            with self.assertRaisesRegex(ValueError,'FULL_REGRESSION_SNAPSHOT_MISSING'):
                r.regression_dependencies(code,'a'*40,root)
            self.assertFalse((root/'absent').exists())

class OriginalArtifactAndArchiveTests(unittest.TestCase):
    def test_original_artifact_index_builder_and_no_clobber(self):
        import pchsi
        repo=Path(pchsi.__file__).resolve().parents[2]
        train=repo/'scripts/engineering_snapshots/training_pipeline/round_generic_training_stage_v2_1_hardening_build'
        sys.path.insert(0,str(train))
        from round_training.receipts import build_input_artifact_index
        from round_training.common import require_domain_sha
        with tempfile.TemporaryDirectory() as td:
            out=Path(td);f.write_once(out/'x.json',b'{}\n')
            value=build_input_artifact_index(round_id='R',stage_id='S',refs=[{'logical_name':'X','path':str(out/'x.json'),'sha256':f.sha(b'{}\n'),'retention_class':'SCIENTIFIC_CONFIG'}])
            require_domain_sha(value,schema_id=value['schema_id'],sha_field='artifact_index_sha256')
            z=f.publish_review(out,{'x.json':b'{}\n','INPUT_ARTIFACT_INDEX.json':f.cb(value)})
            self.assertEqual(f.publish_review(out,{'x.json':b'{}\n','INPUT_ARTIFACT_INDEX.json':f.cb(value)}),z)
            with self.assertRaises(ValueError):f.publish_review(out,{'x.json':b'{"tampered":true}\n'})
    def test_new_shell_fail_fast_and_live_commands_absent(self):
        for path in [HERE/'RUN_ALL.py',HERE/'run_freeze.py',HERE/'freeze_select.py']:
            text=path.read_text()
            for forbidden in ('set -e','set -u','pipefail','sbatch','srun','adapter.step(','PeftModel.from_pretrained','vllm serve'):
                self.assertNotIn(forbidden,text)
    def test_reuse_default_native_make_target_not_payloads(self):
        source=(HERE/'run_freeze.py').read_text()
        self.assertIn("['make','-C','native/s1_backend_probe','all']",source)
        self.assertNotIn("'probe-payloads'",source)

if __name__=='__main__':unittest.main()
