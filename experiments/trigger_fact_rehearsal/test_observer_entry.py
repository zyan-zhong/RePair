import unittest
from observer_entry import bind_authority


class EntryBindingTests(unittest.TestCase):
    def test_default_and_shadow_follow_same_registered_task(self):
        raw = b'#!/bin/bash\nset +euo pipefail\nview_authority=old\nif flag; then\n  view_authority=current\nfi\nexec renderer "$@"\n'
        result = bind_authority(raw, '/registered/current/AUTHORITY.json')
        self.assertEqual(result.count(b'view_authority=/registered/current/AUTHORITY.json'), 2)
        self.assertEqual(result.splitlines()[-1], raw.splitlines()[-1])
        self.assertIn(b'set +euo pipefail\n', result)
        self.assertEqual(bind_authority(result, '/registered/current/AUTHORITY.json'), result)

    def test_unrecognized_entry_is_not_rewritten(self):
        with self.assertRaisesRegex(ValueError, 'REGISTERED_DEFAULT_AND_SHADOW'):
            bind_authority(b'view_authority=only_one\n', '/registered/current')


if __name__ == '__main__':
    unittest.main()
