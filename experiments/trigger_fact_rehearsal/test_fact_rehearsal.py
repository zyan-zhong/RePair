"""Regression boundaries for changing redundant supervision, not teacher answers."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from fact_practice import spans
from fact_rehearsal import rehearse


def row(view, stage, labels):
    return {'view': view, 'stage': stage, 'row_id': view + stage,
            'input_ids': [0] + labels[1:], 'labels': labels,
            'target_tokens': sum(v != -100 for v in labels[1:])}


def sample(i, labels):
    return {'row_index': i, 'labels': labels,
            'target_tokens': sum(v != -100 for v in labels[1:])}


class RehearsalTests(unittest.TestCase):
    def setUp(self):
        self.full = [-100, 11, 12, 13, 14]
        self.focus = [-100, -100, 12, 13, -100]
        self.dataset = {'rows': [row('RESEARCH', 'L-A0', self.full),
                                 row('ACTION', 'POLICY', self.full),
                                 row('RESEARCH', 'R-POST', self.full)],
                        'groups': [[sample(0, self.full), sample(1, self.full),
                                    sample(2, self.full)] for _ in range(4)]}

    def test_focus_starts_only_after_complete_positive_lr_exposure(self):
        before = deepcopy(self.dataset)
        result, proof = rehearse(self.dataset, {0: self.focus}, [1, 2, 3])
        self.assertEqual(result['groups'][0], before['groups'][0])
        self.assertEqual(result['groups'][1], before['groups'][1])
        self.assertEqual(result['groups'][2][0]['labels'], self.focus)
        self.assertEqual(result['groups'][3][0]['labels'], self.focus)
        self.assertEqual(proof['changed_visits'], 2)
        self.assertEqual(self.dataset, before)
        self.assertEqual(result['rows'], before['rows'])

    def test_policy_and_nonlocal_role_samples_stay_identical(self):
        result, _ = rehearse(self.dataset, {0: self.focus}, [1, 2, 3])
        for a, b in zip(self.dataset['groups'], result['groups'], strict=True):
            self.assertEqual(a[1:], b[1:])

    def test_fragmented_full_target_must_finish_before_focusing(self):
        d = deepcopy(self.dataset)
        d['groups'][1][0] = sample(0, [-100, 11, -100, -100, -100])
        result, _ = rehearse(d, {0: self.focus}, [1, 2, 3])
        self.assertEqual(result['groups'][2][0], d['groups'][2][0])
        self.assertEqual(result['groups'][3][0]['labels'], self.focus)

    def test_missing_positive_coverage_is_rejected(self):
        d = deepcopy(self.dataset)
        for g in d['groups'][1:]:
            g[0] = sample(0, self.focus)
        with self.assertRaisesRegex(ValueError, 'POSITIVE_LR_FULL_RESEARCH_COVERAGE'):
            rehearse(d, {0: self.focus}, [1, 2, 3])

    def test_focus_cannot_substitute_teacher_tokens(self):
        bad = list(self.focus)
        bad[2] = 99
        with self.assertRaisesRegex(ValueError, 'TEACHER_LABEL_SUBSTITUTION'):
            rehearse(self.dataset, {0: bad}, [1, 2, 3])

    def test_focus_cannot_target_policy_or_post(self):
        for i in (1, 2):
            with self.assertRaisesRegex(ValueError, 'LOCAL_RESEARCH_ONLY'):
                rehearse(self.dataset, {i: self.focus}, [1, 2, 3])

    def test_focus_is_intersection_with_existing_sample_mask(self):
        d = deepcopy(self.dataset)
        d['groups'][3][0] = sample(0, [-100, 11, 12, -100, -100])
        result, _ = rehearse(d, {0: self.focus}, [1, 2, 3])
        self.assertEqual(result['groups'][3][0]['labels'], [-100, -100, 12, -100, -100])

    def test_selected_window_and_facts_are_both_in_teacher_spans(self):
        error = {'call_window': {'trigger_call_index': 4},
                 'facts_at_trigger': {'model_call_index': 4, 'literal_action': 'look'}}
        wire = {'local_analysis': {'error_instances': [error]}}
        text = json.dumps(wire, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
        pieces = [json.loads(text[a:b]) for a, b in spans(text)]
        self.assertIn(error['call_window'], pieces)
        self.assertIn(error['facts_at_trigger'], pieces)

    def test_old_native_module_cannot_shadow_entry_fact_practice(self):
        entry = Path(__file__).resolve().parent
        # The old helper models the registered source-root module priority.
        # Its fact-only span would silently omit the selected call window.
        with tempfile.TemporaryDirectory(prefix='repair-old-fact-helper-') as temp:
            (Path(temp) / 'fact_practice.py').write_text(
                'def spans(target): return [(0,1)]\n'
                'def practice_labels(*args): return None\n', encoding='utf8')
            (Path(temp) / 'target_binding.py').write_text('def target_for_row(*args): return None\n', encoding='utf8')
            code = 'import sys\nsys.path[:0]=' + repr([temp, str(entry)]) + '\n' + r'''
from pathlib import Path
import inspect,prepare_rehearsal
expected=Path(sys.argv[1]).resolve()
actual=Path(inspect.getsourcefile(prepare_rehearsal.practice_labels)).resolve()
assert actual==expected, 'OLD_NATIVE_FACT_HELPER_SHADOWED_ENTRY:'+str(actual)
assert Path(inspect.getsourcefile(prepare_rehearsal.target_for_row)).resolve()==expected.with_name('target_binding.py')
'''
            run = subprocess.run([sys.executable, '-B', '-c', code,
                                  str(entry / 'fact_practice.py')], capture_output=True, text=True)
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)


if __name__ == '__main__':
    unittest.main()
