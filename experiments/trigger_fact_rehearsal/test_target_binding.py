"""Current conditional teacher takes precedence over historical shared lineage."""
import hashlib
import json
import unittest
from target_binding import target_for_row

sha = lambda s: hashlib.sha256(s.encode()).hexdigest()


class TargetBindingTests(unittest.TestCase):
    def setUp(self):
        self.old = {'path': 'old', 'sha256': 'old'}
        self.new = {'path': 'new', 'sha256': 'new'}
        self.raw = '{ "revision": 2 }'
        self.view = '{"revision":2}'
        self.docs = {'old': {'target_text': '{"revision":1}'},
                     'new': {'target_text': self.raw, 'supervision_admitted': True},
                     'approval': {'decision': 'APPROVED', 'row_ids': ['r']}}
        self.row = {'row_id': 'r', 'training_admitted': True,
                    'shared_scientific_target_ref': self.old,
                    'conditional_teacher_target_ref': self.new, 'target': self.raw}
        self.checked = lambda r: self.docs[r['path']]
        self.proof = {'row_id': 'r', 'raw_teacher_target_ref': self.new,
                      'raw_text_sha256': sha(self.raw), 'view_text_sha256': sha(self.view),
                      'all_scientific_values_and_array_order_equal': True, 'native_emittable': True}

    def test_conditional_execution_target_precedes_old_shared_target(self):
        text, ref = target_for_row(self.row, self.checked, {})
        self.assertEqual(text, self.raw)
        self.assertEqual(ref, self.new)

    def test_approved_execution_view_requires_exact_existing_proof(self):
        self.row.update(target=self.view, target_representation='APPROVED_LOSSLESS_NATIVE_JSON_EXECUTION_VIEW',
                        raw_teacher_target_ref=self.new,
                        execution_view_approval_ref={'path': 'approval', 'sha256': 'approval'})
        text, ref = target_for_row(self.row, self.checked, {'r': self.proof})
        self.assertEqual(text, self.view)
        self.assertEqual(ref, self.new)

    def test_changed_conditional_target_without_approval_is_rejected(self):
        self.row['target'] = '{"revision":3}'
        with self.assertRaisesRegex(ValueError, 'CONDITIONAL_EXECUTION_TARGET_BINDING'):
            target_for_row(self.row, self.checked, {})

    def test_unregistered_shared_target_substitution_is_rejected(self):
        self.row.pop('conditional_teacher_target_ref')
        with self.assertRaisesRegex(ValueError, 'SHARED_EXECUTION_TARGET_BINDING'):
            target_for_row(self.row, self.checked, {})

    def test_approved_view_cannot_change_scientific_values(self):
        self.row.update(target='{"revision":3}', target_representation='APPROVED_LOSSLESS_NATIVE_JSON_EXECUTION_VIEW',
                        raw_teacher_target_ref=self.new,
                        execution_view_approval_ref={'path': 'approval', 'sha256': 'approval'})
        self.proof['view_text_sha256'] = sha(self.row['target'])
        with self.assertRaisesRegex(ValueError, 'APPROVED_VIEW_SCIENTIFIC_VALUE_CHANGE'):
            target_for_row(self.row, self.checked, {'r': self.proof})

    def test_historical_source_flag_does_not_override_active_dataset_admission(self):
        self.docs['new']['supervision_admitted'] = False
        text, ref = target_for_row(self.row, self.checked, {})
        self.assertEqual(text, self.raw)
        self.assertEqual(ref, self.new)

    def test_nonadmitted_execution_row_is_rejected(self):
        self.row['training_admitted'] = False
        with self.assertRaisesRegex(ValueError, 'EXECUTION_ROW_NOT_ADMITTED'):
            target_for_row(self.row, self.checked, {})


if __name__ == '__main__':
    unittest.main()
