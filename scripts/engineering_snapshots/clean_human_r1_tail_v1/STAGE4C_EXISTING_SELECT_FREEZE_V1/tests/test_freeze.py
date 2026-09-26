from __future__ import annotations
import copy, hashlib, importlib.util, json, os, subprocess, tempfile, unittest, zipfile
from pathlib import Path

HERE=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('sf',HERE/'freeze_select.py')
if spec is not None and (HERE/'freeze_select.py').exists():
    sf=importlib.util.module_from_spec(spec);spec.loader.exec_module(sf)
else:sf=None
REVIEW=HERE/'tests/fixtures/SELECT_PREFLIGHT_REVIEW.zip'
SHA='e8263e5a9604a85d831187938b6938f721f76e9163da6f5025398d1c32d4db27'

class APITests(unittest.TestCase):
    def test_required_api(self):
        self.assertTrue(sf is not None and callable(getattr(sf,'validate_review',None)), 'MISSING_FREEZE_CONSUMER_API')

class EvidenceTests(unittest.TestCase):
    def setUp(self):
        self.files=sf.read_review(REVIEW,SHA)
        self.data=sf.validate_review(self.files)
        self.decision=json.loads((HERE/'decisions/current_protocol_decision.json').read_bytes())
    def test_real_uploaded_packet(self):
        self.assertEqual(self.data['grid']['task_count'],355)
        self.assertEqual(self.data['grid']['condition_episodes'],3550)
    def test_actual_grid_is_exact_cartesian_product(self):
        bad=copy.deepcopy(self.data['grid']);bad['pairs'][0]['seed']=998
        with self.assertRaisesRegex(ValueError,'GRID_PAIR'):
            sf.validate_grid(bad)
    def test_duplicate_task_crosswalk_rejected(self):
        bad=copy.deepcopy(self.data['grid']);bad['index_crosswalk'][1]=bad['index_crosswalk'][0]
        with self.assertRaises(ValueError):sf.validate_grid(bad)
    def test_arbitrary_population_no_sampling(self):
        g=copy.deepcopy(self.data['grid']);g['index_crosswalk']=g['index_crosswalk'][:2]
        g['task_count']=2;g['replicate_seeds']=[7,9];g['pairs']=[{k:r[k] for k in ('task_id','select_local_index','source_index')}|{'seed':s} for s in [7,9] for r in g['index_crosswalk']]
        g['paired_cells']=4;g['condition_episodes']=8
        self.assertEqual(sf.validate_grid(g)['condition_episodes'],8)
    def test_internal_file_hash_tamper_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'x.zip'
            with zipfile.ZipFile(f,'w') as z:
                for n,raw in self.files.items():z.writestr(n,raw+b' ' if n=='MODEL_BINDING_PROPOSAL.json' else raw)
            with self.assertRaisesRegex(ValueError,'ARCHIVE_MEMBER_HASH'):
                sf.read_review(f,hashlib.sha256(f.read_bytes()).hexdigest())
    def test_wrong_package_sha_rejected(self):
        with self.assertRaisesRegex(ValueError,'SOURCE_REVIEW_SHA'):
            sf.read_review(REVIEW,'0'*64)
    def test_approval_is_exact_bytes_not_latest(self):
        raw=(HERE/'decisions/current_protocol_decision.json').read_bytes()
        with self.assertRaisesRegex(ValueError,'DECISION_APPROVAL'):
            sf.approve_decision(raw,'0'*64,SHA,self.files)
        sf.approve_decision(raw,hashlib.sha256(raw).hexdigest(),SHA,self.files)
    def test_changed_candidate_identity_is_rejected(self):
        changed=dict(self.files);m=copy.deepcopy(self.data['model']);m['candidate_adapter_bundle_sha256']='0'*64
        changed['MODEL_BINDING_PROPOSAL.json']=json.dumps(m).encode()
        with self.assertRaisesRegex(ValueError,'CANDIDATE'):
            sf.validate_review(changed)
    def test_no_promotion_or_live_from_freeze(self):
        protocol=sf.make_protocol(self.data,self.decision,SHA,'a'*40,'b'*40,'c'*64)
        self.assertFalse(protocol['evaluation_execution_authorized'])
        self.assertFalse(protocol['promotion_eligible'])
        self.assertFalse(protocol['archive_provenance_complete'])
        self.assertEqual(protocol['budget_ceiling']['policy_attempts'],213000)
        self.assertEqual(protocol['budget_ceiling']['environment_steps'],106500)
    def test_unsupported_interface_cannot_substitute(self):
        d=copy.deepcopy(self.decision);d['interface_profile_id']='I2_EXECUTION_PROFILE_V1'
        with self.assertRaises(ValueError):sf.make_protocol(self.data,d,SHA,'a'*40,'b'*40,'c'*64)
    def test_original_proposal_not_mutated(self):
        before=copy.deepcopy(self.data)
        sf.make_protocol(self.data,self.decision,SHA,'a'*40,'b'*40,'c'*64)
        self.assertEqual(self.data,before)
    def test_shared_domain_and_hash_reused(self):
        p=sf.make_protocol(self.data,self.decision,SHA,'a'*40,'b'*40,'c'*64)
        self.assertEqual(p['protocol_sha256'],sf.domain_hash(p['schema_id'],p,'protocol_sha256'))

class GitTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.repo=self.root/'r';self.repo.mkdir()
        self.git('init','-q');self.git('config','user.name','Test');self.git('config','user.email','test@example.invalid')
        for n,v in [('one.txt','base\n'),('two.txt','keep\n')]: (self.repo/n).write_text(v)
        self.git('add','.');self.git('commit','-qm','base')
        self.base=self.git('rev-parse','HEAD').strip()
        (self.repo/'one.txt').write_text('patched\n');(self.repo/'test.txt').write_text('test\n')
        self.scope={'one.txt':{'before_file_sha256':hashlib.sha256(b'base\n').hexdigest(),'after_file_sha256':hashlib.sha256(b'patched\n').hexdigest()},'test.txt':{'before_file_sha256':None,'after_file_sha256':hashlib.sha256(b'test\n').hexdigest()}}
        self.expected=sf.expected_tree(self.repo,self.base,self.scope)
    def tearDown(self):self.tmp.cleanup()
    def git(self,*a):
        p=subprocess.run(['git',*a],cwd=self.repo,text=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        if p.returncode:raise RuntimeError(p.stderr)
        return p.stdout
    def test_exact_commit_preserves_parent_and_resume(self):
        out=self.root/'o';out.mkdir();mainref=self.git('symbolic-ref','HEAD').strip()
        # The production input is a detached worktree. Reproduce this boundary.
        self.git('checkout','--detach','-q')
        got=sf.freeze_code(self.repo,self.base,self.expected,self.scope,out)
        self.assertEqual(self.git('rev-parse',got['head']+'^').strip(),self.base)
        self.assertEqual(self.git('rev-parse',mainref).strip(),self.base)
        again=sf.freeze_code(self.repo,self.base,self.expected,self.scope,out)
        self.assertEqual(got,again)
        listed=self.git('bundle','list-heads',str(out/'SELECT_CODE_HISTORY.bundle'))
        self.assertIn(got['head']+' '+got['ref'],listed)
    def test_modified_unrelated_file_rejected(self):
        (self.repo/'two.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'WORKTREE_BYTES'):sf.check_tree(self.repo,self.expected,self.base)
    def test_skip_worktree_does_not_hide_change(self):
        self.git('update-index','--skip-worktree','two.txt');(self.repo/'two.txt').write_text('hidden')
        with self.assertRaises(ValueError):sf.check_tree(self.repo,self.expected,self.base)
    def test_extra_untracked_file_rejected(self):
        (self.repo/'extra').write_text('no')
        with self.assertRaisesRegex(ValueError,'WORKTREE_EXTRA'):sf.check_tree(self.repo,self.expected,self.base)
    def test_symlink_input_rejected(self):
        (self.repo/'two.txt').unlink();(self.repo/'two.txt').symlink_to(self.repo/'one.txt')
        with self.assertRaisesRegex(ValueError,'SYMLINK'):sf.check_tree(self.repo,self.expected,self.base)
    def test_staged_resume_does_not_duplicate(self):
        self.git('checkout','--detach','-q');self.git('add','one.txt')
        out=self.root/'o';out.mkdir();got=sf.freeze_code(self.repo,self.base,self.expected,self.scope,out)
        self.assertEqual(got,sf.freeze_code(self.repo,self.base,self.expected,self.scope,out))
    def test_ref_conflict_stops(self):
        self.git('checkout','--detach','-q')
        # A pre-existing freeze ref may only be reused when it exactly names the new commit.
        ref=sf.freeze_ref(self.expected);self.git('update-ref',ref,self.base)
        out=self.root/'o';out.mkdir()
        with self.assertRaisesRegex(ValueError,'FREEZE_REF_CONFLICT'):
            sf.freeze_code(self.repo,self.base,self.expected,self.scope,out)
    def test_output_no_clobber(self):
        p=self.root/'x';sf.write_once(p,b'one');sf.write_once(p,b'one')
        with self.assertRaises(ValueError):sf.write_once(p,b'two')

if __name__=='__main__':unittest.main()
