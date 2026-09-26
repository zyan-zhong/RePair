import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from stage4e import GateError
from stage4e import source

class OriginRecoveryTests(unittest.TestCase):
    def fixture(self, root):
        active=root/'active';active.mkdir()
        subprocess.run(['git','init','-b','main',str(active)],check=True,capture_output=True)
        source.git(active,'config','user.name','Test');source.git(active,'config','user.email','test@example.invalid')
        (active/'code.py').write_text('x=1\n');source.git(active,'add','code.py');source.git(active,'commit','-m','base')
        url='ssh://git@ssh.github.com:443/zyan-zhong/phase-critical-harness-guided-self-improvement.git'
        source.git(active,'remote','add','origin',url)
        cfg={'fixed_head':source.git(active,'rev-parse','HEAD'),'fixed_tree':source.git(active,'rev-parse','HEAD^{tree}'),
             'publication_branch':'integration/test','allowed_origin_urls':[url]}
        return active,cfg,url
    def test_ssh443_exact_repository_forms_are_registered(self):
        cfg=json.loads((Path(__file__).resolve().parents[1]/'config.json').read_text())
        stem='zyan-zhong/phase-critical-harness-guided-self-improvement.git'
        for prefix in ('ssh://git@ssh.github.com:443/','ssh://ssh.github.com:443/'):
            self.assertIn(prefix+stem,cfg['allowed_origin_urls'])
    def test_rejected_origin_leaves_no_partial_clone(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);a,c,u=self.fixture(r);dest=r/'dest';c['allowed_origin_urls']=[]
            with self.assertRaisesRegex(GateError,'ORIGIN'):
                source.ensure_isolated_repo(active=a,dest=dest,cfg=c)
            self.assertFalse(dest.exists(),'origin must be validated before cloning')
    def test_recovers_exact_old_v1_partial_clone_without_reset(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);a,c,u=self.fixture(r);dest=r/'dest'
            subprocess.run(['git','clone','--no-hardlinks','--no-checkout',str(a),str(dest)],check=True,capture_output=True)
            source.git(dest,'checkout','-b',c['publication_branch'],c['fixed_head'])
            source.ensure_isolated_repo(active=a,dest=dest,cfg=c)
            self.assertEqual(source.git(dest,'remote','get-url','origin'),u)
            self.assertEqual(source.git(dest,'config','--get','stage4e.anchor'),c['fixed_head'])
            source.verify_active_repo(a,c)
    def test_does_not_adopt_dirty_partial_clone(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);a,c,u=self.fixture(r);dest=r/'dest'
            subprocess.run(['git','clone',str(a),str(dest)],check=True,capture_output=True)
            source.git(dest,'checkout','-b',c['publication_branch']);(dest/'code.py').write_text('changed\n')
            with self.assertRaises(GateError):source.ensure_isolated_repo(active=a,dest=dest,cfg=c)
            self.assertEqual((dest/'code.py').read_text(),'changed\n')
    def test_unapproved_pushurl_is_rejected_before_clone(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);a,c,u=self.fixture(r);dest=r/'dest'
            source.git(a,'remote','set-url','--push','origin','git@github.com:another-owner/other.git')
            with self.assertRaisesRegex(GateError,'ORIGIN'):
                source.ensure_isolated_repo(active=a,dest=dest,cfg=c)
            self.assertFalse(dest.exists())
    def test_allowed_distinct_push_transport_is_preserved(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);a,c,u=self.fixture(r);dest=r/'dest'
            push='https://github.com/zyan-zhong/phase-critical-harness-guided-self-improvement.git'
            c['allowed_origin_urls'].append(push);source.git(a,'remote','set-url','--push','origin',push)
            source.ensure_isolated_repo(active=a,dest=dest,cfg=c)
            self.assertEqual(source.git(dest,'remote','get-url','--push','origin'),push)
    def test_existing_stamped_clone_rechecks_pushurl(self):
        with tempfile.TemporaryDirectory() as d:
            r=Path(d);a,c,u=self.fixture(r);dest=r/'dest'
            source.ensure_isolated_repo(active=a,dest=dest,cfg=c)
            source.git(dest,'remote','set-url','--push','origin','git@github.com:other-owner/other.git')
            with self.assertRaises(GateError):source.ensure_isolated_repo(active=a,dest=dest,cfg=c)
