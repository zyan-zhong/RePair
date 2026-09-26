import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys
from types import SimpleNamespace

import pytest

HERE = Path(__file__).resolve()
PROJECT = HERE.parents[4]
sys.path.insert(0, str(HERE.parents[1]))

import source_binding as binding_module
from source_binding import (SourceBindingError, SourceLayout, inspect_registered_sources,
                            current_memory_inputs, materialize_researcher_view, build_source_binding)

FULL_NATIVE = PROJECT / 'work/v17/native_bba_full'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def put(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf8')
    return {'path': str(path), 'file_sha256': sha(path.read_bytes())}


def test_actual_registered_package_and_locator_mapping():
    result = inspect_registered_sources(SourceLayout.project(PROJECT))
    assert set(result['packages']) == {'q', 'u', 'x', 'h44'}
    assert result['scientific_repo_head'] == 'bba400738a7a53d0402552ecc3576f736ca0eec8'
    assert result['scientific_repo_root'].endswith('/github_exports/pchsi-wt-strong-primary-takeover-prep-v1')
    assert result['train_root'] == '/data/run01/scwb204/.cache/alfworld/json_2.1.1/train'
    assert result['refs']['f0f1_protocol']['file_sha256'] == 'c8f135c4396e54dc925123a078ff228a1901b85422a1aeaab8304a11bb97304d'
    assert result['source_mapping']['experiment_contract'].endswith('configs/analyzer/analyzer_a0_a3_experiment_contract_v1.json')


def test_package_relocation_preserves_original_identity(tmp_path):
    layout = SourceLayout.project(PROJECT)
    original = inspect_registered_sources(layout)
    relocated = tmp_path / 'with spaces'
    shutil.copytree(layout.received, relocated / 'registered_sources')
    for name, ref in original['packages'].items():
        shutil.copytree(ref['root'], relocated / 'reuse' / (Path(ref['root']).name if name != 'h44' else 'h44'))
    result = inspect_registered_sources(SourceLayout.bundle(relocated))
    for name in original['packages']:
        assert result['packages'][name]['manifest']['file_sha256'] == original['packages'][name]['manifest']['file_sha256']
        assert result['packages'][name]['root'] != original['packages'][name]['root']
    assert result['scientific_repo_root'] == original['scientific_repo_root']
    member = Path(result['packages']['q']['root']) / 'v1232q_driver.py'
    member.write_bytes(member.read_bytes() + b'\n# drift\n')
    with pytest.raises(SourceBindingError, match='PACKAGE_MEMBER_SHA'):
        inspect_registered_sources(SourceLayout.bundle(relocated))


def rollout(tmp_path, snapshot='a' * 64):
    memory = {'active_snapshot_sha256': snapshot, 'active_snapshot_directory': str(tmp_path / 'snapshot'),
              'token_budget_contract_sha256': 'b' * 64, 'token_budget_contract_path': str(tmp_path / 'token.json')}
    token = put(tmp_path / 'token.json', {'contract_sha256': 'b' * 64})
    member = put(tmp_path / 'input_capsule/inputs/memory.json', memory)
    request = {'round_id': 'r2', 'parent_policy_id': 'promoted-p1', 'request_sha256': 'c' * 64,
               'round_memory_runtime_authority_sha256': member['file_sha256'],
               'round_start_memory_snapshot_sha256': snapshot, 'token_budget_contract_sha256': 'b' * 64}
    request_ref = put(tmp_path / 'round_evidence/request.json', request)
    return {'schema_id': 'REGISTERED_FRESH_ROLLOUT_MATERIALIZATION_V1', 'root': str(tmp_path),
            'round_id': 'r2', 'request_sha256': 'c' * 64, 'request_path': request_ref['path'],
            'request_file_sha256': request_ref['file_sha256'],
            'input_member_manifest': {'memory': {'member': 'inputs/memory.json', 'sha256': member['file_sha256']}}}


def test_promoted_round_uses_current_memory_directory(tmp_path):
    result = current_memory_inputs(rollout(tmp_path))
    assert result['snapshot_directory'] == str(tmp_path / 'snapshot')
    assert result['request']['parent_policy_id'] == 'promoted-p1'


@pytest.mark.parametrize('field,value,error', [
    ('round_id', 'r1', 'ROLLOUT_REQUEST_IDENTITY'),
    ('request_sha256', 'd' * 64, 'ROLLOUT_REQUEST_IDENTITY'),
    ('round_start_memory_snapshot_sha256', 'd' * 64, 'CURRENT_MEMORY_IDENTITY'),
    ('token_budget_contract_sha256', 'd' * 64, 'CURRENT_MEMORY_IDENTITY'),
])
def test_future_round_mismatch_is_not_rebound(tmp_path, field, value, error):
    result = rollout(tmp_path)
    request = json.loads(Path(result['request_path']).read_bytes())
    request[field] = value
    ref = put(Path(result['request_path']), request)
    result['request_file_sha256'] = ref['file_sha256']
    with pytest.raises(SourceBindingError, match=error):
        current_memory_inputs(result)


def test_capsule_member_escape_rejected(tmp_path):
    result = rollout(tmp_path)
    result['input_member_manifest']['memory']['member'] = '../memory.json'
    with pytest.raises(SourceBindingError, match='MEMBER_ESCAPE'):
        current_memory_inputs(result)


def test_initial_memory_capture_has_locator_but_no_partition_authority():
    import zipfile
    package = PROJECT / 'work/v16/reference/PCHSI_CAMPAIGN_AUTHORITY_DRIVEN_FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_V1_23_2'
    with zipfile.ZipFile(package / 'V123133_MEMORY_AWARE_GENERIC_ROLLOUT_LIVE_SOURCE_CAPSULE.zip') as z:
        memory = json.loads(z.read('FINAL_RUNTIME_IDENTITY_V1.json'))
    assert memory['active_snapshot_directory'].endswith(memory['active_snapshot_sha256'])
    assert memory['token_budget_contract_path'].endswith('/contract/failure_memory_token_budget_contract_v1.json')
    assert not any('partition' in name or 'researcher' in name for name in memory)


def test_native_researcher_builder_preserves_nonempty_records(tmp_path):
    # Real existing native producer; only the already-loaded snapshot is a test fixture.
    native = FULL_NATIVE / 'src'
    sys.path.insert(0, str(native))
    from pchsi.memory import consumer_views as views
    lineage = 'd' * 64
    record = {'memory_lineage_id': lineage, 'fixture_record': 'source-bound fixture'}
    member = SimpleNamespace(record=SimpleNamespace(memory_lineage_id=lineage, to_dict=lambda: record),
        retrieval_key=SimpleNamespace(to_dict=lambda: {'fixture_key': 'k'}),
        fm1_availability=SimpleNamespace(value='FM1_AVAILABLE'), fm2_availability=SimpleNamespace(value='FM2_AVAILABLE'))
    snapshot = SimpleNamespace(snapshot=SimpleNamespace(snapshot_sha256='a' * 64), members=(member,))
    partition = views.MemorySourcePartitionBindingV1(lineage, views.MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE, 'e' * 64)
    result = materialize_researcher_view(snapshot=snapshot, source_partition_by_lineage={lineage: partition},
        expected_snapshot_sha256='a' * 64, output_root=tmp_path, consumer_views=views)
    payload = json.loads(Path(result['path']).read_bytes())
    assert payload['train_side_records'][0]['governed_record'] == record
    assert payload['purpose'] == 'ROUND_RESEARCH_PLANNING'
    assert payload['round_evidence'] == {}
    assert payload['benefit_harm_authority'] is False
    with pytest.raises(SourceBindingError, match='CURRENT_SNAPSHOT_IDENTITY'):
        materialize_researcher_view(snapshot=snapshot, source_partition_by_lineage={lineage: partition},
            expected_snapshot_sha256='f' * 64, output_root=tmp_path, consumer_views=views)
    with pytest.raises(SourceBindingError, match='SOURCE_PARTITION_LOCATOR_MISSING'):
        materialize_researcher_view(snapshot=snapshot, source_partition_by_lineage={},
            expected_snapshot_sha256='a' * 64, output_root=tmp_path, consumer_views=views)


def test_constructor_joins_current_materialization_without_source_choices(tmp_path, monkeypatch):
    """Integration wiring fixture: package bytes are real; remote repo/loader are doubles."""
    result = rollout(tmp_path)
    repo = tmp_path / 'registered_checkout'
    repo.mkdir()
    result['implementation_worktree'] = str(repo)
    actual = inspect_registered_sources(SourceLayout.project(PROJECT))
    actual['scientific_repo_root'] = str(repo)
    monkeypatch.setattr(binding_module, 'inspect_registered_sources', lambda layout: actual)
    for name, relative in binding_module.REPO_REFS.items():
        put(repo / relative, {'schema_id': name})
    put(repo / 'configs/memory/package_b_failure_memory_dependency_v1.json',
        {'active_snapshot_sha256': 'f' * 64, 'token_budget_contract_sha256': 'b' * 64})
    git_reads = []
    def tracked(repo, head, relative):
        git_reads.append(relative)
        if relative.startswith('src/'):
            return {'path': str(repo / relative), 'file_sha256': 'e' * 64}
        return binding_module._ref(repo / relative)
    monkeypatch.setattr(binding_module, '_tracked_ref', tracked)
    native = FULL_NATIVE / 'src'
    sys.path.insert(0, str(native))
    from pchsi.memory import consumer_views as views
    lineage = 'd' * 64
    record = {'memory_lineage_id': lineage, 'fixture': 'current record'}
    member = SimpleNamespace(record=SimpleNamespace(memory_lineage_id=lineage, to_dict=lambda: record),
        retrieval_key=SimpleNamespace(to_dict=lambda: {}), fm1_availability=SimpleNamespace(value='FM1_AVAILABLE'),
        fm2_availability=SimpleNamespace(value='FM2_AVAILABLE'))
    snapshot = SimpleNamespace(snapshot=SimpleNamespace(snapshot_sha256='a' * 64), members=(member,))
    loaded = []
    def loader(**kwargs):
        loaded.append(kwargs)
        return snapshot
    monkeypatch.setattr(binding_module, '_memory_modules', lambda root: (SimpleNamespace(load_calibrated_dev_snapshot_v2=loader), views))
    partition = views.MemorySourcePartitionBindingV1(lineage, views.MemorySourcePartitionV1.TRAIN_MEMORY_SOURCE, 'e' * 64)
    part_ref = put(tmp_path / 'partitions.json', {lineage: partition.to_dict()})
    index = {'round_id': 'r2', 'request_sha256': 'c' * 64, 'refs': {'memory_source_partitions': part_ref}}
    source = build_source_binding(result, layout=SourceLayout.project(PROJECT),
        output_root=tmp_path / 'projection', current_index=index)
    assert source['analyzer_snapshot_directory'] == str(tmp_path / 'snapshot')
    assert loaded[0]['snapshot_directory'] == tmp_path / 'snapshot'
    assert set(source['refs']) == {'f0f1_protocol', 'runtime_manifest', 'experiment_contract',
                                   'role_authority', 'analyzer_token_contract', 'researcher_view',
                                   'memory_source_partitions'}
    assert binding_module._read_ref(source['refs']['memory_source_partitions']) == {lineage: partition.to_dict()}
    assert len(git_reads) == 5
    reused = build_source_binding(result, layout=SourceLayout.project(PROJECT),
        output_root=tmp_path / 'reused', current_index={'refs': {'researcher_view': source['refs']['researcher_view']}})
    assert reused['refs']['researcher_views'] == [source['refs']['researcher_view']]
    with pytest.raises(SourceBindingError, match='RESEARCHER_VIEW_REFS_EMPTY'):
        build_source_binding(result, layout=SourceLayout.project(PROJECT), output_root=tmp_path / 'empty',
                             current_index={'refs': {'researcher_views': []}})
    wrong = json.loads(Path(source['refs']['researcher_view']['path']).read_bytes())
    wrong['snapshot_sha256'] = 'f' * 64
    wrong_ref = put(tmp_path / 'wrong_view.json', wrong)
    with pytest.raises(SourceBindingError, match='RESEARCHER_VIEW_CURRENT_SNAPSHOT_IDENTITY'):
        build_source_binding(result, layout=SourceLayout.project(PROJECT), output_root=tmp_path / 'wrong',
                             current_index={'refs': {'researcher_view': wrong_ref}})
    with pytest.raises(SourceBindingError, match='CURRENT_INDEX_ROUND_IDENTITY'):
        build_source_binding(result, layout=SourceLayout.project(PROJECT), output_root=tmp_path / 'future',
                             current_index={**index, 'round_id': 'r3'})
    with pytest.raises(SourceBindingError, match='SOURCE_PARTITION_LOCATOR_MISSING'):
        build_source_binding(result, layout=SourceLayout.project(PROJECT), output_root=tmp_path / 'missing')


def test_registered_git_object_rejects_working_file_drift(tmp_path, monkeypatch):
    path = tmp_path / 'configs/a.json'
    put(path, {'version': 'wrong working tree'})
    monkeypatch.setattr(binding_module.subprocess, 'run',
        lambda *a, **k: SimpleNamespace(returncode=0, stdout=b'{"version":"registered tracked object"}'))
    with pytest.raises(SourceBindingError, match='REGISTERED_GIT_OBJECT_MISMATCH'):
        binding_module._tracked_ref(tmp_path, 'b' * 40, 'configs/a.json')


def published_native_snapshot(tmp_path, monkeypatch):
    import importlib.util
    monkeypatch.chdir(FULL_NATIVE)
    sys.path.insert(0, str(FULL_NATIVE / 'src'))
    path = FULL_NATIVE / 'tests/memory/package_b_direct_test_helpers.py'
    spec = importlib.util.spec_from_file_location('_v17_native_snapshot_helpers', path)
    helpers = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helpers)
    if sys.platform == 'win32':
        # Windows cannot open directories for POSIX fsync; all scientific builders/loaders stay real.
        from pchsi.memory import dev_descriptive_snapshot_v2
        monkeypatch.setattr(dev_descriptive_snapshot_v2, '_fsync_directory', lambda path: None)
        # Its POSIX os.open flags omit O_BINARY on Windows; preserve canonical bytes in the fixture.
        def binary_write_once(path, raw):
            with Path(path).open('xb') as stream:
                stream.write(raw)
        monkeypatch.setattr(dev_descriptive_snapshot_v2, '_write_once', binary_write_once)
    final, snapshot, contract, token_path, _ = helpers.published_snapshot(tmp_path)
    from pchsi.memory.dev_snapshot_loader import load_calibrated_dev_snapshot_v2
    loaded = load_calibrated_dev_snapshot_v2(snapshot_directory=final,
        expected_snapshot_sha256=snapshot.snapshot_sha256, token_budget_contract_path=token_path,
        expected_token_budget_contract_sha256=contract.contract_sha256)
    return loaded, contract, token_path


def test_initial_partition_uses_actual_native_producer_assignment(tmp_path, monkeypatch):
    loaded, contract, token_path = published_native_snapshot(tmp_path, monkeypatch)
    from pchsi.memory import consumer_views as views
    dependency = {'active_snapshot_sha256': loaded.snapshot.snapshot_sha256,
                  'token_budget_contract_sha256': contract.contract_sha256}
    source = (FULL_NATIVE / 'scripts/memory/run_role_view_smoke_v1.py').read_bytes()
    partitions = binding_module.initial_source_partitions(snapshot=loaded, dependency=dependency,
        native_source=source, consumer_views=views)
    ref = materialize_researcher_view(snapshot=loaded, source_partition_by_lineage=partitions,
        expected_snapshot_sha256=loaded.snapshot.snapshot_sha256, output_root=tmp_path / 'view', consumer_views=views)
    view = json.loads(Path(ref['path']).read_bytes())
    assert len(view['train_side_records']) == len(loaded.members) == 1
    assert view['train_side_records'][0]['governed_record'] == loaded.members[0].record.to_dict()
    assert view['train_side_records'][0]['source_partition_authority_sha256'] == loaded.snapshot.snapshot_sha256
    assert view['train_side_records'][0]['source_partition_authority_scope'] == 'ACCESS_DIAGNOSTIC_ONLY'
    assert partitions[next(iter(partitions))].source_collection_manifest_sha256 is None
    with pytest.raises(SourceBindingError, match='INITIAL_PARTITION_SNAPSHOT_MISMATCH'):
        binding_module.initial_source_partitions(snapshot=loaded,
            dependency={**dependency, 'active_snapshot_sha256': 'f' * 64}, native_source=source, consumer_views=views)


def test_full_registered_capture_has_exact_repo_config_bytes():
    layout = SourceLayout.project(PROJECT)
    sources = inspect_registered_sources(layout)
    repo, git_repo = binding_module.resolve_scientific_repo(sources, layout, str(FULL_NATIVE))
    assert repo == FULL_NATIVE
    for relative in binding_module.REPO_REFS.values():
        ref = binding_module._tracked_ref(repo, sources['scientific_repo_head'], relative, git_repo=git_repo)
        assert Path(ref['path']).is_file()


@pytest.mark.parametrize('initial', [False, True])
def test_full_constructor_real_source_loader_and_view_builder(tmp_path, monkeypatch, initial):
    loaded, contract, token_path = published_native_snapshot(tmp_path, monkeypatch)
    result = rollout(tmp_path / 'round')
    result['implementation_worktree'] = str(FULL_NATIVE)
    memory_path = Path(result['root']) / 'input_capsule/inputs/memory.json'
    memory = json.loads(memory_path.read_bytes())
    memory.update(active_snapshot_sha256=loaded.snapshot.snapshot_sha256,
                  active_snapshot_directory=str(loaded.snapshot_directory),
                  token_budget_contract_path=str(token_path), token_budget_contract_sha256=contract.contract_sha256)
    memory_ref = put(memory_path, memory)
    result['input_member_manifest']['memory']['sha256'] = memory_ref['file_sha256']
    request = json.loads(Path(result['request_path']).read_bytes())
    request.update(round_start_memory_snapshot_sha256=loaded.snapshot.snapshot_sha256,
                   token_budget_contract_sha256=contract.contract_sha256,
                   round_memory_runtime_authority_sha256=memory_ref['file_sha256'])
    result['request_file_sha256'] = put(Path(result['request_path']), request)['file_sha256']
    dependency = {'active_snapshot_sha256': loaded.snapshot.snapshot_sha256,
                  'token_budget_contract_sha256': contract.contract_sha256}
    if initial:
        # Bind a test snapshot as the initial authority; loader, source verification and producer stay real.
        fixture_ref = put(tmp_path / 'fixture_dependency.json', dependency)
        tracked = binding_module._tracked_ref
        def with_test_snapshot(repo, head, relative, **kwargs):
            result = tracked(repo, head, relative, **kwargs)
            if relative == 'configs/memory/package_b_failure_memory_dependency_v1.json':
                return fixture_ref
            return result
        monkeypatch.setattr(binding_module, '_tracked_ref', with_test_snapshot)
        partitions = None
    else:
        from pchsi.memory import consumer_views as views
        partitions = binding_module.initial_source_partitions(snapshot=loaded, dependency=dependency,
            native_source=(FULL_NATIVE / 'scripts/memory/run_role_view_smoke_v1.py').read_bytes(), consumer_views=views)
    binding = build_source_binding(result, layout=SourceLayout.project(PROJECT), output_root=tmp_path / 'view',
                                   source_partition_by_lineage=partitions)
    view = json.loads(Path(binding['refs']['researcher_view']['path']).read_bytes())
    assert view['snapshot_sha256'] == loaded.snapshot.snapshot_sha256
    assert view['train_side_records'][0]['governed_record'] == loaded.members[0].record.to_dict()
    assert binding['scientific_repo_root'] == str(FULL_NATIVE)
