from pathlib import Path
import tempfile
import unittest
import os
import json
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import preflight as p
import run_preflight as entry

class IsolationTests(unittest.TestCase):
    def test_exact_overlay_is_idempotent_and_source_is_unchanged(self):
        repo=Path(os.environ['SELECT_TEST_REPO'])
        base=entry.cmd(['git','rev-parse','HEAD'],cwd=repo).decode().strip()
        # Obtain authoritative base bytes from Git, even when the local test
        # worktree already contains the reviewed extension.
        source={}
        for row in entry.cmd(['git','ls-tree','-r','-z','HEAD'],cwd=repo).split(b'\0'):
            if not row:continue
            _,name=row.split(b'\t',1);rel=os.fsdecode(name)
            raw=entry.cmd(['git','show',base+':'+rel],cwd=repo)
            source[str(repo/rel)]=p.sha(raw)
        with tempfile.TemporaryDirectory() as td:
            out=Path(td)
            code,first=entry.isolated_code(repo,out,base,source)
            _,second=entry.isolated_code(repo,out,base,source)
            self.assertEqual(first,second)
            target=code/'src/pchsi/evaluation/raw_policy_prompt.py'
            target.write_bytes(target.read_bytes()+b'\n# unexpected mutation\n')
            with self.assertRaisesRegex(ValueError,'CODE_TREE_FILE_CHANGED'):
                entry.isolated_code(repo,out,base,source)
            # Cleanup only this test worktree, not scientific artifacts.
            entry.cmd(['git','worktree','remove','--force',str(code)],cwd=repo)

if __name__=='__main__':unittest.main()
