"""Synthetic objects; real frozen producer/native hash and schedule implementations."""
from __future__ import annotations
import copy
from dataclasses import replace
import hashlib
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = Path('/data/run01/scwb204/sdar_repro/badcase/pchsi_scripts')
OLD = Path(os.environ.get('STAGE4E_HASH_TEST_OLD', str(SCRIPTS/'STAGE4E_AUTOMATIC_AUDIT_CLOSEOUT_AND_SOURCE_PUBLICATION_V1_1_ORIGIN_AND_ARRAY_FIX')))
REPO = Path(os.environ.get('STAGE4E_HASH_TEST_REPO', '/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-stage4e-clean-human-r1-integration-v1'))
sys.path[:0] = [str(ROOT),str(OLD),str(REPO/'src')]
from stage4e import canonical, semantic_sha, GateError, write_exact
from pchsi.evaluation.canonical_evidence import canonical_json_bytes
from pchsi.evaluation.distillation_governance import canonical_model_sha256
from pchsi.evaluation.condition_run_schedule import ConditionRunScheduleV1, ConditionRunScheduleCellV1, ConditionRunPurpose, condition_cell_id
from pchsi.evaluation.distillation_access import DistillationAccessClass
from pchsi.evaluation.select_result_audit import derive_expected_select_cells_from_master_schedules


def schedule(label='T0', tasks=3, seeds=(17,31)):
    cells=tuple(ConditionRunScheduleCellV1(condition_cell_id(policy_condition_id=label,manifest_index=i,seed=s),i,f'SYNTHETIC-TASK-{i}',s) for s in seeds for i in range(tasks))
    return ConditionRunScheduleV1('CONDITION_RUN_SCHEDULE_V1',1,'SYNTHETIC-'+label,'a'*64,'b'*64,ConditionRunPurpose.P4_HARNESS_OFF_SELECT,DistillationAccessClass.SELECT_SUMMARY_ONLY,seeds,'seed-major',len(cells),'SYNTHETIC_'+label,'unique_task',cells)


def registration(models):
    identity={'schema_id':'STAGE4D_EXISTING_SELECT_LIVE_BINDING_IDENTITY_V1','schema_version':1,'artifacts':{name:semantic_sha(model.to_dict()) for name,model in models.items()}}
    return identity,semantic_sha(identity)


def bridge():
    import native_hash_bridge
    return native_hash_bridge


class NativeDigestTests(unittest.TestCase):
    def test_two_existing_canonical_functions_differ_only_by_lf(self):
        model=schedule()
        self.assertEqual(canonical_json_bytes(model.to_dict()),canonical(model.to_dict())+b'\n')
        self.assertNotEqual(semantic_sha(model.to_dict()),canonical_model_sha256(model))

    def test_original_mapping_reproduces_exact_server_failure(self):
        models={key:schedule(key) for key in ('T0','T2')}
        with self.assertRaisesRegex(ValueError,'SELECT authorized schedule hash mismatch'):
            derive_expected_select_cells_from_master_schedules(schedules=models,authorized_schedule_sha256={k:semantic_sha(m.to_dict()) for k,m in models.items()})

    def test_bound_bridge_satisfies_actual_native_validator_for_full_grid(self):
        models={k:schedule(k,355,(17,31,47,73,101)) for k in ('T0','T2')}
        identity,binding_sha=registration({k+'_CONDITION_RUN_SCHEDULE_V1.json':m for k,m in models.items()})
        digests={k:bridge().registered_native_hash(m,identity,k+'_CONDITION_RUN_SCHEDULE_V1.json',binding_sha,{'canonical_model_sha256':canonical_model_sha256}) for k,m in models.items()}
        cells=derive_expected_select_cells_from_master_schedules(schedules=models,authorized_schedule_sha256=digests)
        self.assertEqual(len(cells),3550)
        self.assertEqual(len({c.condition_cell_id for c in cells}),3550)
        self.assertEqual([sum(c.schedule_name==k for c in cells) for k in ('T0','T2')],[1775,1775])

    def test_changed_model_not_self_authorized(self):
        m=schedule();name='T0_CONDITION_RUN_SCHEDULE_V1.json';i,sha=registration({name:m})
        with self.assertRaisesRegex(GateError,'MODEL_NOT_BOUND'):
            bridge().registered_native_hash(replace(m,output_namespace='MUTATED'),i,name,sha,{'canonical_model_sha256':canonical_model_sha256})

    def test_changed_identity_and_hashes_not_self_authorized(self):
        m=schedule();name='T0_CONDITION_RUN_SCHEDULE_V1.json';i,sha=registration({name:m});i['artifacts'][name]='0'*64
        with self.assertRaisesRegex(GateError,'BINDING_IDENTITY_CHANGED'):
            bridge().registered_native_hash(m,i,name,sha,{'canonical_model_sha256':canonical_model_sha256})

    def test_missing_registered_name_rejected(self):
        m=schedule();i,sha=registration({'other':m})
        with self.assertRaisesRegex(GateError,'UNREGISTERED_ARTIFACT'):
            bridge().registered_native_hash(m,i,'T0_CONDITION_RUN_SCHEDULE_V1.json',sha,{'canonical_model_sha256':canonical_model_sha256})

    def test_duplicate_json_keys_and_nonfinite_still_rejected(self):
        from stage4e import strict_loads
        for raw in (b'{"x":1,"x":2}',b'{"x":NaN}'):
            with self.assertRaises(GateError):strict_loads(raw)

    def test_runtime_uses_same_bridge_not_manifest_digest(self):
        spec=importlib.util.spec_from_file_location('_real_native_runtime_fixture',REPO/'tests/evaluation/test_p4_select_execution_compat_v1.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        _server,runtime=m._select_policy_runtime_for_final_audit()
        name='T2_SELECT_POLICY_RUNTIME_MANIFEST_V1.json';i,sha=registration({name:runtime})
        got=bridge().registered_native_hash(runtime,i,name,sha,{'canonical_model_sha256':canonical_model_sha256})
        self.assertEqual(got,canonical_model_sha256(runtime));self.assertNotEqual(got,i['artifacts'][name])

    def test_mutated_runtime_model_name_rejected(self):
        spec=importlib.util.spec_from_file_location('_real_native_runtime_fixture2',REPO/'tests/evaluation/test_p4_select_execution_compat_v1.py')
        m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
        _server,runtime=m._select_policy_runtime_for_final_audit()
        name='T2_SELECT_POLICY_RUNTIME_MANIFEST_V1.json';i,sha=registration({name:runtime})
        with self.assertRaisesRegex(GateError,'MODEL_NOT_BOUND'):
            bridge().registered_native_hash(replace(runtime,served_model_name='WRONG'),i,name,sha,{'canonical_model_sha256':canonical_model_sha256})

    def test_native_cross_condition_grid_mismatch_still_rejected(self):
        models={'T0':schedule('T0',3),'T2':schedule('T2',2)}
        i,sha=registration({k+'_CONDITION_RUN_SCHEDULE_V1.json':m for k,m in models.items()})
        d={k:bridge().registered_native_hash(m,i,k+'_CONDITION_RUN_SCHEDULE_V1.json',sha,{'canonical_model_sha256':canonical_model_sha256}) for k,m in models.items()}
        with self.assertRaisesRegex(ValueError,'same task/seed grid'):
            derive_expected_select_cells_from_master_schedules(schedules=models,authorized_schedule_sha256=d)

    def test_native_duplicate_cell_check_not_removed(self):
        models={'T0':schedule('T0'),'T2':schedule('T0')}
        i,sha=registration({k+'_CONDITION_RUN_SCHEDULE_V1.json':m for k,m in models.items()})
        d={k:bridge().registered_native_hash(m,i,k+'_CONDITION_RUN_SCHEDULE_V1.json',sha,{'canonical_model_sha256':canonical_model_sha256}) for k,m in models.items()}
        with self.assertRaisesRegex(ValueError,'duplicate SELECT scientific cell identity'):
            derive_expected_select_cells_from_master_schedules(schedules=models,authorized_schedule_sha256=d)

    def test_old_bytes_and_native_checker_never_modified(self):
        b=bridge();p=OLD/'stage4e/audit.py';before=p.read_bytes()
        patched=b.corrected_audit_source(before)
        self.assertEqual(p.read_bytes(),before)
        self.assertIn("native['derive_expected_select_cells_from_master_schedules']",patched)
        self.assertIn('audit_select_cell_identity_chain(',patched)
        self.assertEqual(patched.count('_registered_native_hash('),2)
        b.verify_native_sources(REPO)

    def test_unknown_audit_source_rejected(self):
        with self.assertRaisesRegex(GateError,'ORIGINAL_AUDIT_CHANGED'):
            bridge().corrected_audit_source((OLD/'stage4e/audit.py').read_bytes()+b'\n')

    def test_same_digests_after_canonical_storage_roundtrip(self):
        from stage4e import read_json
        model=schedule();name='T0_CONDITION_RUN_SCHEDULE_V1.json';i,sha=registration({name:model})
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/name;write_exact(path,model.to_dict())
            restored=ConditionRunScheduleV1.from_dict(read_json(path))
            got=bridge().registered_native_hash(restored,i,name,sha,{'canonical_model_sha256':canonical_model_sha256})
            self.assertEqual(got,hashlib.sha256(path.read_bytes()).hexdigest())


if __name__=='__main__':unittest.main()
