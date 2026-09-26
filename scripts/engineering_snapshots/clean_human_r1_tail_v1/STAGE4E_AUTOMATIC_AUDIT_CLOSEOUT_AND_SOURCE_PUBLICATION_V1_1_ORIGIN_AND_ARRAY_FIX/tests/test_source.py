from __future__ import annotations
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

class SourceTests(unittest.TestCase):
    def source(self):
        self.assertIsNotNone(importlib.util.find_spec('stage4e.source'),'MISSING_ISOLATED_SOURCE_PUBLICATION')
        from stage4e import source
        return source
    def test_symbol_map_reports_path_line_and_dynamic_limits(self):
        s=self.source()
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'m.py';p.write_text('import os\nclass C:\n    def f(self):\n        return os.getcwd()\n')
            x=s.inspect_python(p)
            self.assertEqual(x['symbols'][1]['name'],'C.f')
            self.assertEqual(x['symbols'][1]['line'],3)
            self.assertIn('os.getcwd',[c['expression'] for c in x['calls']])
            self.assertFalse(x['dynamic_call_resolution_complete'])

    def test_source_filter_does_not_include_logs_or_dataset_or_weights(self):
        s=self.source()
        for name in ('runtime.out','x.err','trace.jsonl','adapter.safetensors','secret.env','RUNTIME_READINESS.json'):
            self.assertFalse(s.is_snapshot_source(name))
        for name in ('slurm_template.sh','stage4d_full/live.py','tests/test_core.py','README_CN.md'):
            self.assertTrue(s.is_snapshot_source(name))

    def test_secret_value_detected_not_variable_name(self):
        s=self.source()
        s.reject_secret(b'key=os.environ.get("OPENAI_API_KEY")','x.py')
        with self.assertRaises(ValueError):s.reject_secret(b'OPENAI_API_KEY="sk-'+b'x'*40+b'"','x.py')

    def test_native_file_digest_changes_on_source_mutation(self):
        s=self.source()
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=root/'x.py';p.write_text('x=1\n')
            a=s.source_inventory(root,['x.py'])
            p.write_text('x=2\n');b=s.source_inventory(root,['x.py'])
            self.assertNotEqual(a,b)

    def test_fast_forward_only_rejects_divergent_history(self):
        s=self.source()
        with tempfile.TemporaryDirectory() as d:
            r=Path(d)/'repo';r.mkdir()
            def g(*args):return subprocess.check_output(['git','-C',str(r),*args],stderr=subprocess.DEVNULL,text=True).strip()
            g('init','-b','main');g('config','user.email','test@example.invalid');g('config','user.name','Test')
            (r/'x').write_text('a');g('add','x');g('commit','-m','base');base=g('rev-parse','HEAD')
            (r/'x').write_text('b');g('commit','-am','left');left=g('rev-parse','HEAD')
            g('checkout','-b','other',base);(r/'x').write_text('c');g('commit','-am','right');right=g('rev-parse','HEAD')
            s.require_ancestor(r,base,left)
            with self.assertRaises(ValueError):s.require_ancestor(r,left,right)
            self.assertEqual(g('rev-parse','HEAD'),right)

    def test_publisher_uses_atomic_push_without_force_or_main_checkout(self):
        s=self.source();text=Path(s.__file__).read_text()
        self.assertIn("'--atomic'",text)
        self.assertNotIn("'--force'",text)
        self.assertNotIn("'--force-with-lease'",text)
        self.assertNotIn("'reset', '--hard'",text)
        self.assertNotIn("'add', '-A'",text)

if __name__=='__main__':unittest.main()
