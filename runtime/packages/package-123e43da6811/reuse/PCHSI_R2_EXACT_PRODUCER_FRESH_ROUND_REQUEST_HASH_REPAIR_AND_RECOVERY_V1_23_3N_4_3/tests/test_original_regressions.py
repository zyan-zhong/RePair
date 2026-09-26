"""Regression reproductions execute the exact reviewed statement blocks."""
import ast
from dataclasses import dataclass, replace
from pathlib import Path
import os

ROOT=Path(__file__).resolve().parents[1]
SOURCE_ROOT=Path(os.environ.get('R2_TEST_PRODUCER',str(ROOT/'producer')))

@dataclass(frozen=True)
class Cell:
    scheduled_cell_id:str='cell'
@dataclass(frozen=True)
class Row:
    cell:Cell=Cell()
    attempt_ordinal:int=0
    execution_attempt_id:str='cell-a000'

def run_original_attempt_block(ordinal):
    text=(SOURCE_ROOT/'shard_worker.py').read_text()
    # Exercise the original ordinal validation/rebinding independently of GPU work.
    if 'schedule_for_attempt(' in text:
        import sys
        sys.path.insert(0,str(ROOT/'producer'))
        from fresh_round_contract import schedule_for_attempt
        return schedule_for_attempt((Row(),),ordinal,lambda *,scheduled_cell_id,attempt_ordinal:f'{scheduled_cell_id}-a{attempt_ordinal:03d}')
    tree=ast.parse(text)
    candidates=[n for n in ast.walk(tree) if isinstance(n,ast.Try) and any(isinstance(s,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fresh_attempt_ordinal' for t in s.targets) for s in n.body)]
    block=candidates[0].body
    start=next(i for i,s in enumerate(block) if isinstance(s,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='fresh_attempt_ordinal' for t in s.targets))
    end=next(i for i,s in enumerate(block[start+1:],start+1) if isinstance(s,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='assigned' for t in s.targets))
    env={'shard_plan':{'fresh_execution_attempt_ordinal':ordinal},'schedule':(Row(),),'dataclass_replace':replace,'execution_attempt_id':lambda *,scheduled_cell_id,attempt_ordinal:f'{scheduled_cell_id}-a{attempt_ordinal:03d}'}
    exec(compile(ast.Module(body=block[start:end],type_ignores=[]),'reviewed_attempt_block','exec'),env)
    return env['schedule']

def test_native_zero_ordinal_is_accepted_before_service_launch():
    assert run_original_attempt_block(0)[0].execution_attempt_id=='cell-a000'

def test_historical_positive_ordinal_preserved():
    assert run_original_attempt_block(2)[0].execution_attempt_id=='cell-a002'

def test_worker_and_finalizer_share_attempt_identity_binding():
    w=(SOURCE_ROOT/'shard_worker.py').read_text()
    f=(SOURCE_ROOT/'global_finalize.py').read_text()
    assert 'schedule_for_attempt(' in w and 'schedule_for_attempt(' in f

def test_finalizer_consumes_current_request_not_legacy_capsule_round():
    text=(SOURCE_ROOT/'global_finalize.py').read_text()
    assert 'request_from_plan(' in text
    assert 'validate_request_against_capsule(' in text
