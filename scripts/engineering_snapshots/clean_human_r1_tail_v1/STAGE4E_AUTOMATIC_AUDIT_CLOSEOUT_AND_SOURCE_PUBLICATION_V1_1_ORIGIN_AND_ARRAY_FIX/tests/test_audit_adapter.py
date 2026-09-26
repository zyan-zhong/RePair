from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

class AuditAdapterTests(unittest.TestCase):
    def adapter(self):
        spec=importlib.util.find_spec('stage4e.audit')
        self.assertIsNotNone(spec, 'MISSING_EXISTING_AUDIT_ADAPTER')
        from stage4e import audit
        return audit

    def test_completion_gate_precedes_receipt_read(self):
        a=self.adapter()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,'COMPLETION_MARKER_MISSING'):
                a.completion_gate(Path(d),{'authorization_sha256':'a'*64,'binding_sha256':'b'*64,'readiness_sha256':'c'*64,'pair_count':3})

    def test_exact_order_duplicate_missing_and_boolean_outcomes(self):
        a=self.adapter()
        cells=[{'condition_cell_id':'c0','manifest_index':2,'task_id':'t2','seed':17},
               {'condition_cell_id':'c1','manifest_index':3,'task_id':'t3','seed':17}]
        rows=[{**x,'condition_id':'policy','memory_state':'OFF','harness_state':'OFF','success':False} for x in cells]
        a.check_receipt_grid(rows,cells,condition_id='policy')
        for changed in (rows[:1],rows[::-1],[rows[0],rows[0]],[{**rows[0],'success':None},rows[1]],[{**rows[0],'success':0},rows[1]]):
            with self.assertRaises(ValueError): a.check_receipt_grid(changed,cells,condition_id='policy')

    def test_takeover_not_forged_when_metrics_missing(self):
        a=self.adapter()
        x=a.takeover_pending(round_id='r1',next_parent='PI0_CLEAN',summary_sha='1'*64)
        self.assertFalse(x['strong_execution_authorized'])
        self.assertFalse(x['local_execution_authorized'])
        self.assertEqual(x['routine_human_decisions_required'],0)
        self.assertIn('REGISTERED_TAKEOVER_METRICS',x['unresolved_requirements'])
        self.assertNotIn('task_results',json.dumps(x))

    def test_native_audit_and_aggregator_are_imported_not_reimplemented(self):
        a=self.adapter()
        source=Path(a.__file__).read_text()
        self.assertIn('audit_select_cell_identity_chain(',source)
        self.assertIn('aggregate_paired_results(',source)
        self.assertIn('load_attempt_directory_v1(',source)
        self.assertIn('audit_cell_attempt_state(',source)
        self.assertNotIn('run_single_episode(',source)
        self.assertNotIn('success_rate_delta >',source)

    def test_metadata_only_lineage_does_not_read_unsealed_benchmark(self):
        a=self.adapter()
        with self.assertRaises(ValueError): a.validate_train_reference('/data/run01/scwb204/badcase/benchmarks/output.json')
        with self.assertRaises(ValueError): a.validate_train_reference('/tmp/valid_unseen/trace.json')
        a.validate_train_reference('/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/source.json')

    def test_loader_source_missing_is_a_hard_error(self):
        a=self.adapter()
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError): a.load_native(Path(d))

if __name__=='__main__': unittest.main()
