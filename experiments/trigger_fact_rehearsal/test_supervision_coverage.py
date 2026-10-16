import copy, unittest
from supervision_coverage import full_prefix


class CoverageTests(unittest.TestCase):
    def dataset(self):
        return {'rows':[{'view':'ACTION','labels':[-100,1,2]},
                        {'view':'RESEARCH','labels':[-100,3,4]}],
                'groups':[[{'row_index':0,'labels':[-100,1,2],'target_tokens':2},
                           {'row_index':1,'labels':[-100,3,-100],'target_tokens':1}],
                          [{'row_index':1,'labels':[-100,-100,4],'target_tokens':1}],
                          [{'row_index':1,'labels':[-100,3,4],'target_tokens':2}]]}

    def test_row_seen_is_not_full_supervision(self):
        self.assertEqual(full_prefix(self.dataset())['prefix_groups'],2)

    def test_missing_label_position_fails_closed(self):
        d=self.dataset();d['groups']=d['groups'][:1]
        with self.assertRaisesRegex(ValueError,'UNCOVERED_REGISTERED_TARGET_POSITIONS'):
            full_prefix(d)

    def test_altered_teacher_token_is_rejected(self):
        d=self.dataset();d['groups'][0][1]['labels'][1]=5
        with self.assertRaisesRegex(ValueError,'NATIVE_GROUP_LABEL_SUBSTITUTION'):
            full_prefix(d)

    def test_input_order_and_masks_are_preserved(self):
        d=self.dataset();original=copy.deepcopy(d)
        result=full_prefix(d)
        self.assertEqual(d,original)
        self.assertEqual(result['groups'],original['groups'][:2])
        self.assertEqual(result['expected_positions'],4)
        self.assertFalse(result['scientific_method_qualified'])


if __name__=='__main__':unittest.main()
