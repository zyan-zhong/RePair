import subprocess
from pathlib import Path
import tempfile
import unittest
from stage4e.source import publish_atomic,git,ensure_isolated_repo,verify_active_repo
from stage4e import GateError

class GitPublicationIntegrationTests(unittest.TestCase):
    def fixture(self,root):
        bare=root/'remote.git';repo=root/'source'
        subprocess.run(['git','init','--bare',str(bare)],capture_output=True,check=True)
        subprocess.run(['git','init','-b','main',str(repo)],capture_output=True,check=True)
        git(repo,'config','user.name','Test');git(repo,'config','user.email','test@example.invalid')
        (repo/'x.txt').write_text('base\n');git(repo,'add','x.txt');git(repo,'commit','-m','base')
        git(repo,'remote','add','origin',str(bare));git(repo,'push','origin','main')
        return bare,repo
    def test_isolated_clone_and_atomic_publication_leave_active_unchanged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);remote,active=self.fixture(root);repo=root/'isolated'
            cfg={'fixed_head':git(active,'rev-parse','HEAD'),'fixed_tree':git(active,'rev-parse','HEAD^{tree}'),
                 'publication_branch':'integration/test','allowed_origin_urls':[str(remote)]}
            ensure_isolated_repo(active=active,dest=repo,cfg=cfg)
            (repo/'new.txt').write_text('new\n');git(repo,'add','new.txt');git(repo,'commit','-m','new')
            value=publish_atomic(repo=repo,branch=cfg['publication_branch'],include_main=True,approved_urls=[str(remote)])
            self.assertEqual(value['status'],'REMOTE_VERIFIED');self.assertTrue(value['main_updated'])
            verify_active_repo(active,cfg);self.assertFalse((active/'new.txt').exists())
    def test_divergence_refuses_main_and_does_not_publish_branch(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);remote,active=self.fixture(root);repo=root/'isolated'
            cfg={'fixed_head':git(active,'rev-parse','HEAD'),'fixed_tree':git(active,'rev-parse','HEAD^{tree}'),
                 'publication_branch':'integration/test','allowed_origin_urls':[str(remote)]}
            ensure_isolated_repo(active=active,dest=repo,cfg=cfg)
            (repo/'a').write_text('a');git(repo,'add','a');git(repo,'commit','-m','a')
            (active/'b').write_text('b');git(active,'add','b');git(active,'commit','-m','b');git(active,'push','origin','main')
            with self.assertRaisesRegex(GateError,'NON_FAST_FORWARD'):
                publish_atomic(repo=repo,branch=cfg['publication_branch'],include_main=True,approved_urls=[str(remote)])
            self.assertFalse(git(active,'ls-remote','origin','refs/heads/integration/test'))
