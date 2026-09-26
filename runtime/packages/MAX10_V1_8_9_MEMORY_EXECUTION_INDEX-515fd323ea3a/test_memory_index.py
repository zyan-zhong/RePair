from pathlib import Path
import json,copy,unittest,ast
from memory_index import validate_execution,registered_call,overlay_source
ROOT=Path(__file__).resolve().parent
class MemoryIndex(unittest.TestCase):
    def setUp(self):
        self.e=json.loads((ROOT/'TEST_EXECUTION.json').read_bytes());self.b={'round_id':self.e['round_id'],'parent_policy_id':self.e['policy_version']}
    def test_native_stale_manifest_does_not_supply_selected_sources(self):
        old=json.loads((ROOT/'TEST_BASELINE_EXECUTION.json').read_bytes());selected=json.loads((ROOT/'TEST_SELECTED.json').read_bytes())
        self.assertTrue(any(not [r for r in old['rows'] if r['source_unit_id']==s['sid'] and r['stage_id']=='L-A1'] for s in selected))
        validate_execution(self.e,self.b)
        for s in selected:
            rows=[r for r in self.e['rows'] if r['source_unit_id']==s['sid'] and r['stage_id']=='L-A1']
            self.assertEqual(len(rows),1);self.assertTrue(registered_call(rows[0],self.e))
    def test_wrong_round_duplicate_slot_and_unregistered_call_rejected(self):
        with self.assertRaises(ValueError):validate_execution(self.e,{**self.b,'round_id':'another'})
        e=copy.deepcopy(self.e);e['rows'].append(e['rows'][0])
        with self.assertRaises(ValueError):validate_execution(e,self.b)
        row=next(r for r in self.e['rows'] if r['status']=='ACCEPTED');row={**row,'call_dir':'/wrong/'+row['logical_call_id']}
        with self.assertRaises(ValueError):registered_call(row,self.e)
    def test_only_registered_reader_and_existing_condition_resolver_change(self):
        text=(ROOT/'TEST_MEMORY_API.txt').read_text();updated=overlay_source(text);ast.parse(updated)
        self.assertIn('_accepted_local(call_dir=call_dir',updated)
        self.assertIn('validate_verifier(plan_ref=',updated)
        self.assertIn('classify_shadow_event_v1(event)',updated)
        with self.assertRaises(ValueError):overlay_source(updated)
if __name__=='__main__':unittest.main(verbosity=2)
