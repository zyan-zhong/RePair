"""Native partition and operational recovery; not live scientific results."""
import pytest
from continuity_binding.api import read_ref, write_once
from offoff_binding.parallel import check_worker_resume
from offoff_binding.native import ARRAY_CONFIG
from test_binding import fixture


def test_exact_original_stage4d_partition_covers_full_355_by_5_grid(tmp_path):
    native = fixture(tmp_path)['native']
    policy = read_ref(native.sources[str(native.root/ARRAY_CONFIG)])['array_policy']
    module = native.parallel()
    rows = module.partition_ordinals(module.remaining_ordinals(completed_prefix_count=0,total_pairs=355*5),
                                     shard_count=policy['shards'])
    assert [len(row) for row in rows] == [444,444,444,443]
    assert sorted(n for row in rows for n in row) == list(range(1775))
    assert policy['worker_budget_seconds'] == 11700 and policy['max_partial_resumptions'] == 1


def test_resume_requires_explicit_graceful_partial_and_never_restarts_ambiguous_worker(tmp_path):
    ref = write_once(tmp_path/'binding.json', {'fixture':'parallel'})
    kwargs = dict(root=tmp_path,parallel_ref=ref,shard_id=0,assigned=444,maximum=1)
    assert check_worker_resume(**kwargs,resumption_ordinal=0) is None
    write_once(tmp_path/'WORKER_STARTED_000.json', {'fixture':'started'})
    with pytest.raises(ValueError,match='AMBIGUOUS_WORKER'):
        check_worker_resume(**kwargs,resumption_ordinal=0)
    status = {'schema_id':'CURRENT_NATIVE_OFFOFF_SHARD_STATUS_V1','parallel_ref':ref,'shard_id':0,
        'resumption_ordinal':0,'assigned_pair_count':444,'parent_cell_count':300,'candidate_cell_count':300,
        'graceful_partial':True,'complete':False}
    status_ref = write_once(tmp_path/'SHARD_STATUS_000.json',status)
    assert check_worker_resume(**kwargs,resumption_ordinal=0) == status_ref
    assert check_worker_resume(**kwargs,resumption_ordinal=1) is None
    write_once(tmp_path/'WORKER_STARTED_001.json', {'fixture':'started resumption'})
    with pytest.raises(ValueError,match='AMBIGUOUS_WORKER'):
        check_worker_resume(**kwargs,resumption_ordinal=1)
    with pytest.raises(ValueError,match='BUDGET_EXHAUSTED'):
        check_worker_resume(**kwargs,resumption_ordinal=2)


def test_completed_shard_cannot_spend_another_execution_attempt(tmp_path):
    ref = write_once(tmp_path/'binding.json', {'fixture':'parallel'})
    write_once(tmp_path/'SHARD_STATUS_000.json',{'schema_id':'CURRENT_NATIVE_OFFOFF_SHARD_STATUS_V1',
        'parallel_ref':ref,'shard_id':0,'resumption_ordinal':0,'assigned_pair_count':3,
        'parent_cell_count':3,'candidate_cell_count':3,'graceful_partial':False,'complete':True})
    with pytest.raises(ValueError,match='RESUME_ONLY_GRACEFUL_PARTIAL'):
        check_worker_resume(root=tmp_path,parallel_ref=ref,shard_id=0,assigned=3,maximum=1,resumption_ordinal=1)
