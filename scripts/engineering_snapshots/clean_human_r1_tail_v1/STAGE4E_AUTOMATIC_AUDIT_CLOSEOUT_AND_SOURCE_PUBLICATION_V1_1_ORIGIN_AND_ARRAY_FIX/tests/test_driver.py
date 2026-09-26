import importlib
import tempfile
from pathlib import Path
import unittest

class DriverTests(unittest.TestCase):
    def module(self):
        try: return importlib.import_module('stage4e.driver')
        except ModuleNotFoundError: self.fail('MISSING_OUTCOME_GATED_DRIVER')
    def test_accounting_selects_exact_parent_not_steps(self):
        m=self.module()
        raw='156834|RUNNING|0:0\n156834.batch|FAILED|1:0\n'
        self.assertEqual(m.parse_accounting(raw, '156834'), ('RUNNING','0:0'))
    def test_unknown_accounting_never_assumes_success(self):
        m=self.module()
        self.assertIsNone(m.parse_accounting('', '156834'))
        with self.assertRaises(ValueError): m.parse_accounting('156834|COMPLETED|0:0\n156834|FAILED|1:0','156834')
    def test_terminal_nonzero_must_not_trigger_audit(self):
        m=self.module()
        self.assertEqual(m.decide('COMPLETED','1:0',True,False,0,1),'STOP')
    def test_driver_never_publishes_restricted_results(self):
        m=self.module()
        self.assertNotIn('restricted', '|'.join(m.PUBLIC_RESULTS))
        self.assertNotIn('TASK_LEVEL_PAIRED_RESULTS.json',m.PUBLIC_RESULTS)
    def test_resume_receipt_is_parsed_exactly(self):
        m=self.module()
        self.assertEqual(m.parse_submitted_job('STAGE4D_FULL_SELECT_SUBMITTED\nJOB_ID=166000\n'),'166000')
        with self.assertRaises(ValueError):m.parse_submitted_job('STOP=FAILED\n')
    def test_audit_uses_separate_process_and_source_tree(self):
        m=self.module();text=Path(m.__file__).read_text()
        self.assertIn('audit-once',text)
        self.assertIn('verify_active_repo',text)
        self.assertNotIn('git reset',text)
        self.assertNotIn('git switch main',text)
