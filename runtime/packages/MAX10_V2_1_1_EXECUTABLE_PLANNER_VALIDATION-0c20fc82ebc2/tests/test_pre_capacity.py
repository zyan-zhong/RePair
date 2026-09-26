import copy
import importlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def api():
    try:
        return importlib.import_module('pre_capacity')
    except ImportError as exc:
        raise AssertionError('Pure PRE capacity library is not implemented') from exc


def fixture():
    return json.loads((ROOT / 'fixtures/R5_PRE_FIXTURE.json').read_bytes())['bundle']


def render(items):
    # Real string nesting, schema and envelope overhead count against the limit.
    return {'input': [{'role': 'system', 'text': 'review every identified record'},
                      {'role': 'user', 'text': json.dumps(items, ensure_ascii=False)}],
            'max_output_tokens': 200, 'schema': {'required': ['fragment_ids', 'reviews']}}


def small_inventory(m, *, shared=False):
    value = '\u96ea\U0001f680"\\\n' * 1000
    ref = {'pointer': '/a', 'path': ['a'], 'canonical_sha256': m.digest(value)}
    ref['record_id'] = m.digest(ref)
    packets = []
    for name in (['short', 'much longer source header ' * 8] if shared else ['short']):
        source = {'public_task_goal': name}
        packet = {'kind': 'SOURCE_REVIEW', 'source': source, 'records': [{'ref': ref, 'value': value}]}
        packet['packet_id'] = m.digest({'kind': packet['kind'], 'source': source, 'records': [ref]})
        packets.append(packet)
    inv = {'schema_id': 'PRE_REVIEW_INVENTORY_V1', 'projection_canonical_sha256': m.digest({'a': value}),
           'expected_records': [ref], 'packets': packets}
    inv['inventory_id'] = m.digest(inv)
    return inv


class CapacityTests(unittest.TestCase):
    def test_r5_all_original_fields_roundtrip_and_no_proposal_group_retained(self):
        m = api(); original = fixture()['input_projection']; before = copy.deepcopy(original)
        inventory = m.build_review_packets(original)
        sources = [p for p in inventory['packets'] if p['kind'] == 'SOURCE_REVIEW']
        self.assertEqual(len(sources), 28)
        toilet = next(p for p in sources if p['source']['source_state_sha256'].startswith('fc98'))
        groups = [r['value'] for r in toilet['records'] if '/group_findings/' in r['ref']['pointer']]
        self.assertEqual(len(groups), 2)
        self.assertTrue(any(not g['artifact']['source_conditioned_proposals'] for g in groups))
        remote = next(p for p in sources if p['source']['source_state_sha256'].startswith('3f3375'))
        self.assertEqual(remote['source']['public_task_goal'], 'put some remotecontrol on sofa.')
        plan = m.pack_review_packets(inventory, render=render, context_limit=1050000, max_output=24576)
        self.assertEqual(m.restore_projection(plan), original)
        self.assertEqual(original, before)
        self.assertGreater(len(plan['batches']), 1)
        self.assertTrue(all(b['wire_bytes'] <= 1025424 for b in plan['batches']))

    def test_source_menu_misassociation_fails(self):
        m = api(); p = fixture()['input_projection']
        p['blind_input']['registered_candidate_universe']['pair_table'][0]['source_context']['admissible_commands'].reverse()
        with self.assertRaisesRegex(ValueError, 'SOURCE_MENU'):
            m.build_review_packets(p)

    def test_missing_g_target_fails_instead_of_dropping_it(self):
        m = api(); p = fixture()['input_projection']
        p['blind_input']['registered_candidate_universe']['pair_table'][0]['A2']['group_result_sha256s'] = ['f' * 64]
        with self.assertRaisesRegex(ValueError, 'GROUP_TARGET'):
            m.build_review_packets(p)

    def test_source_membership_wrong_task_fails(self):
        m = api(); p = fixture()['input_projection']
        p['blind_input']['analyzer_evidence_view']['group_membership'][0]['membership_records'][0]['task_id'] = 'foreign'
        with self.assertRaisesRegex(ValueError, 'MEMBERSHIP_SOURCE'):
            m.build_review_packets(p)

    def test_every_record_and_unmatched_status_covered(self):
        m = api(); inventory = m.build_review_packets(fixture()['input_projection'])
        expected = {r['pointer'] for r in inventory['expected_records']}
        observed = {r['ref']['pointer'] for p in inventory['packets'] for r in p['records']}
        self.assertEqual(expected, observed)
        global_packet = next(p for p in inventory['packets'] if p['kind'] == 'GLOBAL_REVIEW')
        statuses = [r for r in global_packet['records'] if '/method_statuses/' in r['ref']['pointer']]
        self.assertEqual(len(statuses), 3)

    def test_huge_unicode_record_and_goal_fragment_without_loss(self):
        m = api(); p = fixture()['input_projection']
        p['blind_input']['prior_closed_round_research_memory'] = {
            'very_long': '\u96ea\U0001f680"\\\n' * 3000, 'empty_list': [], 'empty_dict': {},
            'nested': [True, None, 0, {'0': 'numeric string key'}]}
        p['blind_input']['analyzer_evidence_view']['source_contexts'][0]['public_task_goal'] = 'goal\u96ea' * 1000
        inventory = m.build_review_packets(p)
        plan = m.pack_review_packets(inventory, render=render, context_limit=6200, max_output=200)
        self.assertEqual(m.restore_projection(plan), p)
        self.assertTrue(all(b['wire_bytes'] <= 6000 for b in plan['batches']))
        self.assertTrue(any('text_span' in part for batch in plan['batches'] for item in batch['items'] for part in item['parts']))

    def test_actual_wire_envelope_not_payload_only_is_measured(self):
        m = api(); inventory = m.build_review_packets(fixture()['input_projection'])
        oversized_envelope = lambda items: {'fixed': 'x' * 2000, 'items': items}
        with self.assertRaisesRegex(ValueError, 'ENVELOPE'):
            m.pack_review_packets(inventory, render=oversized_envelope, context_limit=1000, max_output=200)

    def test_deterministic_ids_and_incomplete_duplicate_coverage_rejected(self):
        m = api(); inventory = m.build_review_packets(fixture()['input_projection'])
        a = m.pack_review_packets(inventory, render=render, context_limit=1050000, max_output=24576)
        b = m.pack_review_packets(inventory, render=render, context_limit=1050000, max_output=24576)
        self.assertEqual(a, b)
        ids = a['expected_fragment_ids']
        m.verify_review_coverage(a, ids)
        with self.assertRaisesRegex(ValueError, 'COVERAGE'):
            m.verify_review_coverage(a, ids[:-1])
        with self.assertRaisesRegex(ValueError, 'COVERAGE'):
            m.verify_review_coverage(a, ids + ids[:1])

    def test_fragment_tampering_is_detected(self):
        m = api(); inventory = m.build_review_packets(fixture()['input_projection'])
        plan = m.pack_review_packets(inventory, render=render, context_limit=1050000, max_output=24576)
        plan['batches'][0]['items'][0]['parts'][0]['value'] = 'corrupted'
        with self.assertRaises(ValueError):
            m.restore_projection(plan)

    def test_exact_wire_limit_and_one_byte_less(self):
        m = api(); inventory = small_inventory(m)
        initial = m.pack_review_packets(inventory, render=render, context_limit=100000, max_output=200)
        size = initial['batches'][0]['wire_bytes']
        exact = m.pack_review_packets(inventory, render=render, context_limit=size + 200, max_output=200)
        self.assertEqual(len(exact['expected_fragment_ids']), 1)
        smaller = m.pack_review_packets(inventory, render=render, context_limit=size + 199, max_output=200)
        self.assertGreater(len(smaller['expected_fragment_ids']), 1)
        self.assertTrue(all(b['wire_bytes'] <= size - 1 for b in smaller['batches']))
        self.assertEqual(m.restore_projection(smaller), m.restore_projection(exact))

    def test_shared_oversized_record_with_different_fragment_boundaries(self):
        m = api(); inventory = small_inventory(m, shared=True)
        plan = m.pack_review_packets(inventory, render=render, context_limit=2400, max_output=200)
        self.assertEqual(m.digest(m.restore_projection(plan)), inventory['projection_canonical_sha256'])

    def test_coverage_manifest_cannot_be_shrunk_after_planning(self):
        m = api(); inventory = small_inventory(m)
        plan = m.pack_review_packets(inventory, render=render, context_limit=2400, max_output=200)
        plan['expected_fragment_ids'].pop()
        with self.assertRaisesRegex(ValueError, 'PLAN_IDENTITY'):
            m.verify_review_coverage(plan, plan['expected_fragment_ids'])

    def test_rendered_parts_carry_readable_original_locations(self):
        m = api(); inventory = small_inventory(m)
        plan = m.pack_review_packets(inventory, render=render, context_limit=2400, max_output=200)
        for batch in plan['batches']:
            for item in batch['items']:
                for part in item['parts']:
                    self.assertEqual(part.get('record_pointer'), '/a')

    def test_near_capacity_goal_falls_back_to_context_reference(self):
        m = api(); inventory = small_inventory(m); packet = inventory['packets'][0]
        packet['source']['public_task_goal'] = 'g' * 1580
        packet['packet_id'] = m.digest({'kind': packet['kind'], 'source': packet['source'],
                                        'records': [r['ref'] for r in packet['records']]})
        inventory['inventory_id'] = m.digest({k: v for k, v in inventory.items() if k != 'inventory_id'})
        plan = m.pack_review_packets(inventory, render=render, context_limit=2400, max_output=200)
        self.assertEqual(m.digest(m.restore_projection(plan)), inventory['projection_canonical_sha256'])


if __name__ == '__main__':
    unittest.main()
