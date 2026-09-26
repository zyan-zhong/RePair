import sys,unittest,subprocess,os,json
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent/'src'))
from goal_metric import compile_goal, completion, compare

def atom(p,*args,neg=False):return {'kind':'NegatedAtom' if neg else 'Atom','predicate':p,'args':list(args)}
def both(*parts):return {'kind':'Conjunction','parts':list(parts)}
def exists(params,*parts):return {'kind':'ExistentialCondition','parameters':[{'name':n,'type':t} for n,t in params],'parts':[both(*parts)]}

class MetricTest(unittest.TestCase):
 def setUp(self):
  self.goal=exists([('?x','obj')],atom('type','?x','apple'),atom('clean','?x'),atom('placed','?x'))
  self.static={('type',('a','apple')),('type',('b','apple'))}
  self.spec=compile_goal(self.goal,{'obj':['a','b']},self.static,{'clean','placed'})
 def test_shared_witness_not_independent_subgoals(self):
  self.assertEqual(completion(self.spec,{('clean',('a',)),('placed',('b',))}), (1,2))
 def test_complete_and_empty(self):
  self.assertEqual(completion(self.spec,{('clean',('b',)),('placed',('b',))}),(2,2))
  self.assertEqual(completion(self.spec,set()),(0,2))
 def test_inequality_requires_two_distinct_objects(self):
  g=exists([('?x','obj'),('?y','obj')],atom('=','?x','?y',neg=True),atom('placed','?x'),atom('placed','?y'))
  s=compile_goal(g,{'obj':['a','b']},set(),{'placed'})
  self.assertEqual(completion(s,{('placed',('a',))}),(1,2))
 def test_missing_static_binding_fails(self):
  with self.assertRaises(ValueError):compile_goal(self.goal,{'obj':['a']},set(),{'clean','placed'})
 def test_unsupported_goal_fails(self):
  with self.assertRaises(ValueError):compile_goal({'kind':'Disjunction','parts':[]},{},set(),{'a'})
 def test_dynamic_negation(self):
  s=compile_goal(atom('open','box',neg=True),{},set(),{'open'})
  self.assertEqual(completion(s,set()),(1,1))
  self.assertEqual(completion(s,{('open',('box',))}),(0,1))
 def test_compilation_stable_across_spawn_hash_seeds(self):
  goal=exists([('?x','obj'),('?y','obj')],atom('=','?x','?y',neg=True),atom('placed','?x'),atom('placed','?y'))
  code='import sys,json;sys.path.insert(0,'+repr(str(Path(__file__).parent/'src'))+');from goal_metric import compile_goal;print(json.dumps(compile_goal('+repr(goal)+",{'obj':['a','b']},set(),{'placed'}),sort_keys=True))"
  outputs=[subprocess.check_output([sys.executable,'-c',code],env={**os.environ,'PYTHONHASHSEED':seed}) for seed in ('1','2','7')]
  self.assertEqual(len(set(outputs)),1)
 def test_success_primary_and_exact_tie(self):
  self.assertEqual(compare(4,5,[(1,1)],[(0,1)]),'PROMOTE')
  self.assertEqual(compare(5,4,[(0,1)],[(1,1)]),'ROLLBACK')
  self.assertEqual(compare(4,4,[(1,2),(0,1)],[(0,1),(2,3)]),'PROMOTE')
  self.assertEqual(compare(4,4,[(1,2)],[(2,4)]),'ROLLBACK')
 def test_missing_progress_cannot_promote_tie(self):
  with self.assertRaises(ValueError):compare(4,4,[(0,1)],[])
  with self.assertRaises(ValueError):compare(4,4,[(0,0)],[(1,1)])

if __name__=='__main__':unittest.main()
