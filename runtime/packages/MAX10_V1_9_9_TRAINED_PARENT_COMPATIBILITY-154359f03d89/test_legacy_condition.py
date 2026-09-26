import unittest
from condition_contract import resolve_condition


class SourceConditionTests(unittest.TestCase):
    def setUp(self):
        self.binding = {'round_id':'round-test', 'parent_policy_id':'parent-next'}
        self.request = dict(self.binding)
        self.accepted = dict(self.binding)
        self.contract = {'profile_id':'registered-profile-next', 'request_kind':'I1', 'serialization_schema_sha256':'abc'}
        self.runtime = {'schema_id':'CLEAN_PI0_LIVE_RUNTIME_BINDING_V2', 'served_model_name':'registered-model', 'continuation_request_contract':dict(self.contract)}
        self.profile = {'schema_id':'ROUND_BOUND_POLICY_EXECUTION_PROFILE_V1', 'policy_version':'parent-next', 'served_model_name':'registered-model', 'continuation_request_contract':dict(self.contract)}

    def resolve(self, explicit=None):
        return resolve_condition(self.binding,self.request,self.runtime,self.profile,self.accepted,explicit)

    def test_missing_legacy_field_uses_current_registered_parent_and_profile(self):
        self.assertEqual(self.resolve(), 'parent-next::registered-profile-next')

    def test_explicit_current_condition_preserved(self):
        self.assertEqual(self.resolve('parent-next::registered-profile-next'),'parent-next::registered-profile-next')

    def test_foreign_explicit_condition_is_not_silently_replaced(self):
        with self.assertRaisesRegex(ValueError,'EXPLICIT_CONDITION'): self.resolve('legacy-parent::old-profile')

    def test_profile_parent_drift_rejected(self):
        self.profile['policy_version']='wrong-parent'
        with self.assertRaisesRegex(ValueError,'PARENT'): self.resolve()

    def test_contract_drift_rejected(self):
        self.runtime['continuation_request_contract']['profile_id']='another-profile'
        with self.assertRaisesRegex(ValueError,'CONTRACT'): self.resolve()

    def test_accepted_pre_round_drift_rejected(self):
        self.accepted['round_id']='another-round'
        with self.assertRaisesRegex(ValueError,'ROUND'): self.resolve()

    def test_missing_profile_does_not_fall_back_to_parent(self):
        self.profile['continuation_request_contract'].pop('profile_id')
        with self.assertRaises(ValueError): self.resolve()

    def test_served_model_drift_rejected(self):
        self.profile['served_model_name']='wrong-model'
        with self.assertRaisesRegex(ValueError,'MODEL'): self.resolve()

if __name__=='__main__': unittest.main()
