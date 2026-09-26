from pathlib import Path
import unittest,tempfile,json
from portfolio_guard import guard_controller,require_complete_portfolio

class PortfolioTests(unittest.TestCase):
    def plan(self):return {'handoff':{'branch_plan':[{'branch_key_sha256':'f0'},{'branch_key_sha256':'f1'}]},
                          'branch_bindings':[{'binding':{'branch_key_sha256':'f0'}},{'binding':{'branch_key_sha256':'f1'}}]}
    def test_whole_portfolio_passes(self):require_complete_portfolio(self.plan())
    def test_persisted_incomplete_plan_cannot_bypass_preparation_on_resume(self):
        p=self.plan();p['branch_bindings'].pop();effects=[]
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);(root/'EXECUTION_PLAN.json').write_text(json.dumps(p))
            with self.assertRaisesRegex(ValueError,'PORTFOLIO'):guard_controller(lambda r:effects.append(r))(root)
        self.assertEqual(effects,[])
    def test_duplicate_binding_cannot_hide_missing_branch(self):
        p=self.plan();p['branch_bindings'][1]=p['branch_bindings'][0]
        with self.assertRaises(ValueError):require_complete_portfolio(p)
