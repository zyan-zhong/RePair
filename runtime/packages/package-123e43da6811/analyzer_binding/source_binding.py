"""Deterministic internal constructor for the existing Analyzer operation binding.

Source registration is code identity, never a scientific or startup authority.
No directory enumeration, receipt traversal, latest lookup or provider calls.
"""
from __future__ import annotations

from dataclasses import dataclass
import ast
from functools import partial
import hashlib
import importlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import sys


class SourceBindingError(ValueError):
    pass


SOURCE_PLAN_SHA256 = '1b96fb79bd3ba1316f659b608cdc4f021b8d12ea8c35540b3fe2e93fc7cb4aeb'
PACKAGES = {
    'q': ('PCHSI_CAMPAIGN_ROLLOUT_HANDOFF_STRONG_ANALYZER_RUNTIME_REGISTRY_AUTHORITY_RECONCILIATION_V1_23_2Q',
          '695753e9709459677f3470f7f40779af93f97da9d222fe5fcc7101e92ca85d34'),
    'u': ('PCHSI_CAMPAIGN_STRONG_ANALYZER_G_TERMINAL_ADOPTION_CPX_DYNAMIC_PAIR_UNIVERSE_V1_23_2U',
          '59f20089e0f79c91445ec5e6837fa799550f0965836774016a688d1809f5e7e9'),
    'x': ('PCHSI_CAMPAIGN_DYNAMIC_STRONG_PLANNER_PRE_RESUME_STABLE_MEMORY_CENSUS_AND_AUTONOMOUS_INFRA_RECOVERY_V1_23_2X',
          '513463745197b1593241bfc580e30e7a4189032c5c212d497d9332f3550093be'),
    'h44': ('PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4',
            '90fa3251f41adfe4150f99a015d220a72acee24f9ab3185d9c6edc0123068088'),
}
REPO_REFS = {
    'runtime_manifest': 'configs/cognitive_runtime/unified_cognitive_runtime_manifest_v1.json',
    'experiment_contract': 'configs/analyzer/analyzer_a0_a3_experiment_contract_v1.json',
    'role_authority': 'docs/project/strong_primary_takeover_v1/stage6ao/ROLE_SCOPED_STRONG_PRIMARY_FRESH_ROUND_AUTHORITY_V1.json',
}


@dataclass(frozen=True)
class SourceLayout:
    """Installation locations supplied by the entry, never operator runner choices."""
    received: Path
    reference: Path
    h44: Path
    native_capture_receipt: Path | None = None
    native_git_cache: Path | None = None

    @classmethod
    def project(cls, project_root):
        root = Path(project_root).absolute()
        return cls(root / 'work/v16/received', root / 'work/v16/reference',
                   root / 'work/reference_g2' / PACKAGES['h44'][0],
                   root / 'work/v17/NATIVE_BBA_FULL_SOURCE_RECEIPT_V2.json',
                   root / 'work/v17/registered_git_cache')

    @classmethod
    def bundle(cls, bundle_root):
        root = Path(bundle_root).absolute()
        return cls(root / 'registered_sources', root / 'reuse', root / 'reuse/h44')


def _digest(raw):
    return hashlib.sha256(raw).hexdigest()


def _canonical(value):
    return (json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False,
                       separators=(',', ':')) + '\n').encode('utf8')


def _json(raw):
    def pairs(items):
        out = {}
        for key, value in items:
            if key in out:
                raise SourceBindingError('DUPLICATE_JSON_KEY:' + key)
            out[key] = value
        return out
    def invalid(value):
        raise SourceBindingError('NONFINITE_JSON:' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)


def _exact(path, *, directory=False):
    path = Path(path)
    if not path.is_absolute() or '..' in path.parts:
        raise SourceBindingError('EXACT_ABSOLUTE_PATH_REQUIRED:' + str(path))
    for node in (path, *path.parents):
        if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
            raise SourceBindingError('PATH_ALIAS_FORBIDDEN:' + str(node))
    if not (path.is_dir() if directory else path.is_file()):
        raise SourceBindingError('REGISTERED_SOURCE_BYTES_UNAVAILABLE:' + str(path))
    return path


def _raw(path, expected=None):
    raw = _exact(path).read_bytes()
    if expected is not None and _digest(raw) != expected:
        raise SourceBindingError('SOURCE_FILE_SHA:' + str(path))
    return raw


def _ref(path, expected=None):
    return {'path': str(path), 'file_sha256': _digest(_raw(path, expected))}


def _read_ref(ref):
    return _json(_raw(ref['path'], ref['file_sha256']))


def _member(value):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        raise SourceBindingError('MEMBER_ESCAPE:' + str(value))
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts or str(path) != value:
        raise SourceBindingError('MEMBER_ESCAPE:' + value)
    return path


def _one(rows, description):
    if len(rows) != 1:
        raise SourceBindingError('REGISTERED_SOURCE_NOT_UNIQUE:' + description)
    return rows[0]


def _verify_package(root, manifest_sha):
    root = _exact(root, directory=True)
    manifest = _ref(root / 'PACKAGE_FILES.sha256', manifest_sha)
    seen = set()
    for line in _raw(manifest['path']).decode('utf8').splitlines():
        if not line.strip():
            continue
        expected, relative = line.split(maxsplit=1)
        relative = str(_member(relative.lstrip('*')))
        if relative in seen:
            raise SourceBindingError('DUPLICATE_PACKAGE_MEMBER:' + relative)
        seen.add(relative)
        if _digest(_raw(root / relative)) != expected:
            raise SourceBindingError('PACKAGE_MEMBER_SHA:' + relative)
    return {'root': str(root), 'manifest': manifest}


def inspect_registered_sources(layout):
    """Resolve finite registered locators; does not assert live bytes are present."""
    plan = _json(_raw(layout.received / 'SOURCE_PLAN.json', SOURCE_PLAN_SHA256))
    def anchor(relative):
        row = _one([r for r in plan['anchors'] if r['archive_path'] == relative], relative)
        return _json(_raw(layout.received / relative, row['sha256']))
    capture = anchor('anchors/evidence/FORMAL_MAX10_EXECUTION_ENTRY_SOURCE_CAPTURE_V1.json')
    gate2 = anchor('anchors/evidence/GATE2_SOURCE_CAPTURE_MANIFEST_V2.json')
    repository = _one([r for r in gate2['manifest'] if r['kind'] == 'git_relevant_sources_archive'], 'scientific_repo')
    packages = {}
    for name, (package, manifest_sha) in PACKAGES.items():
        registration = _one([r for r in capture['historical_packages'] if r['package'] == package], name)
        if name != 'h44':
            row = _one([r for r in plan['sources'] if r['archive_path'] == 'registered_packages/' + package + '.zip'], name)
            if row['sha256'] != registration['zip_sha256']:
                raise SourceBindingError('PACKAGE_REGISTRATION_CONFLICT:' + name)
        else:
            row = _one([r for r in gate2['manifest'] if r['kind'] == 'exact_package:h44'], name)
            if row['sha256'] != registration['zip_sha256']:
                raise SourceBindingError('PACKAGE_REGISTRATION_CONFLICT:h44')
        root = layout.h44 if name == 'h44' else layout.reference / package
        packages[name] = _verify_package(root, manifest_sha)
        packages[name]['archive_sha256'] = registration['zip_sha256']
    h44 = Path(packages['h44']['root'])
    deployment = _json(_raw(h44 / 'assets/deployment_authorities.json'))
    protocol = Path(packages['x']['root']) / 'assets/configs/planner_bound_f0f1_replication_protocol_v2.json'
    repo = repository['source_path']
    return {'packages': packages, 'scientific_repo_root': repo,
            'scientific_repo_head': capture['repo']['head'], 'scientific_repo_tree': capture['repo']['tree'],
            'train_root': deployment['train_root'],
            'refs': {'f0f1_protocol': _ref(protocol)},
            'source_mapping': {k: str(PurePosixPath(repo) / v) for k, v in REPO_REFS.items()},
            'source_plan_file_sha256': SOURCE_PLAN_SHA256,
            'scientific_execution_started': False}


def current_memory_inputs(result):
    """Use only this rollout's exact capsule member; never the bootstrap snapshot."""
    if result.get('schema_id') != 'REGISTERED_FRESH_ROLLOUT_MATERIALIZATION_V1':
        raise SourceBindingError('ROLLOUT_MATERIALIZATION_SCHEMA')
    root = _exact(result['root'], directory=True)
    request_ref = {'path': result['request_path'], 'file_sha256': result['request_file_sha256']}
    request = _read_ref(request_ref)
    if any(request.get(k) != result.get(k) for k in ('round_id', 'request_sha256')):
        raise SourceBindingError('ROLLOUT_REQUEST_IDENTITY')
    row = result['input_member_manifest']['memory']
    ref = _ref(root / 'input_capsule' / _member(row['member']), row['sha256'])
    if ref['file_sha256'] != request['round_memory_runtime_authority_sha256']:
        raise SourceBindingError('CURRENT_MEMORY_FILE_IDENTITY')
    memory = _read_ref(ref)
    for name, request_name in [('active_snapshot_sha256', 'round_start_memory_snapshot_sha256'),
                               ('token_budget_contract_sha256', 'token_budget_contract_sha256')]:
        if memory.get(name) != request.get(request_name):
            raise SourceBindingError('CURRENT_MEMORY_IDENTITY:' + name)
    for name in ('active_snapshot_directory', 'token_budget_contract_path'):
        if not isinstance(memory.get(name), str) or not memory[name]:
            raise SourceBindingError('CURRENT_MEMORY_SOURCE_LOCATOR_MISSING:/' + name)
    return {'request': request, 'memory': memory, 'memory_runtime': ref,
            'snapshot_directory': memory['active_snapshot_directory'],
            'token_contract_path': memory['token_budget_contract_path']}


def _write_once(path, value):
    path = Path(path).absolute()
    for node in (path, *path.parents):
        if node.is_symlink() or (hasattr(node, 'is_junction') and node.is_junction()):
            raise SourceBindingError('OUTPUT_ALIAS_FORBIDDEN:' + str(node))
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = _canonical(value)
    try:
        with path.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    except FileExistsError:
        if _raw(path) != raw:
            raise SourceBindingError('IMMUTABLE_VIEW_CONFLICT:' + str(path))
    return _ref(path)


def materialize_researcher_view(*, snapshot, source_partition_by_lineage,
                               expected_snapshot_sha256, output_root, consumer_views,
                               aggregate_context=None, current_request=None):
    """Call the native producer with intact loaded records and native partition bindings."""
    if snapshot.snapshot.snapshot_sha256 != expected_snapshot_sha256:
        raise SourceBindingError('CURRENT_SNAPSHOT_IDENTITY')
    missing = [m.record.memory_lineage_id for m in snapshot.members
               if m.record.memory_lineage_id not in source_partition_by_lineage]
    if missing:
        raise SourceBindingError('SOURCE_PARTITION_LOCATOR_MISSING:/source_partition_by_lineage/' + ','.join(missing))
    if aggregate_context is not None:
        from analyzer_binding.aggregate_context import validate_previous_select_context
        if current_request is None:
            raise SourceBindingError('SELECT_CONTEXT_CURRENT_REQUEST_REQUIRED')
        aggregate_context = validate_previous_select_context(aggregate_context, current_request=current_request)
        if aggregate_context['consumer_memory_snapshot_sha256'] != expected_snapshot_sha256:
            raise SourceBindingError('SELECT_CONTEXT_CURRENT_SNAPSHOT_IDENTITY')
    view = consumer_views.build_researcher_memory_view_v1(snapshot=snapshot,
        purpose=consumer_views.ResearcherPurposeV1.ROUND_RESEARCH_PLANNING,
        source_partition_by_lineage=source_partition_by_lineage,
        round_evidence=None, heldout_aggregate_metrics=aggregate_context).to_dict()
    # The actual native builder derives records; this adapter never supplies an empty substitute.
    return _write_once(Path(output_root) / 'RESEARCHER_MEMORY_VIEW_V1.json', view)


def _tracked_ref(repo, head, relative, *, git_repo=None):
    """Check one known tracked object against captured HEAD; no status/tree census."""
    path = repo / relative
    raw = _raw(path)
    result = subprocess.run(['git', '-C', str(git_repo or repo), 'cat-file', 'blob', head + ':' + relative],
                            capture_output=True, check=False, shell=False)
    if result.returncode != 0 or result.stdout != raw:
        raise SourceBindingError('REGISTERED_GIT_OBJECT_MISMATCH:' + relative)
    return _ref(path)


def resolve_scientific_repo(sources, layout, implementation_worktree):
    """Use the registered live checkout, or its exact registered local full capture."""
    requested = Path(implementation_worktree)
    registered = Path(sources['scientific_repo_root'])
    if requested == registered:
        return _exact(registered, directory=True), None
    if layout.native_capture_receipt is None or layout.native_git_cache is None:
        raise SourceBindingError('ROLLOUT_SCIENTIFIC_REPO_LOCATION_MISMATCH')
    receipt = _json(_raw(layout.native_capture_receipt))
    if requested != Path(receipt['extracted_root']):
        raise SourceBindingError('ROLLOUT_SCIENTIFIC_REPO_LOCATION_MISMATCH')
    if (receipt.get('schema') != 'REGISTERED_EXACT_GIT_BLOB_SOURCE_CACHE_V2' or
            receipt['registered_commit'] != sources['scientific_repo_head'] or
            receipt['tree_git_sha1'] != sources['scientific_repo_tree'] or
            receipt['missing_tracked_paths']):
        raise SourceBindingError('LOCAL_CAPTURE_REGISTERED_IDENTITY_MISMATCH')
    _raw(receipt['archive_path'], receipt['archive_sha256'])
    git_repo = _exact(layout.native_git_cache, directory=True)
    tree = subprocess.run(['git', '-C', str(git_repo), 'rev-parse', sources['scientific_repo_head'] + '^{tree}'],
                          capture_output=True, check=False, shell=False)
    if tree.returncode or tree.stdout.decode('ascii').strip() != sources['scientific_repo_tree']:
        raise SourceBindingError('LOCAL_CAPTURE_GIT_TREE_MISMATCH')
    return _exact(requested, directory=True), git_repo


def initial_source_partitions(*, snapshot, dependency, native_source, consumer_views):
    """Reuse the original bootstrap partition expression without broadening its scope.

The current tracked run_role_view_smoke_v1.main loads this exact dependency
snapshot and builds its existing diagnostic Researcher partition mapping. Only
that assignment is executed, not the script's Policy/Analyzer/query operation.
"""
    if snapshot.snapshot.snapshot_sha256 != dependency['active_snapshot_sha256']:
        raise SourceBindingError('INITIAL_PARTITION_SNAPSHOT_MISMATCH')
    if snapshot.token_budget_contract.contract_sha256 != dependency['token_budget_contract_sha256']:
        raise SourceBindingError('INITIAL_PARTITION_TOKEN_CONTRACT_MISMATCH')
    module = ast.parse(native_source)
    main = _one([node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == 'main'],
                'native Memory role-view main')
    assignment = _one([node for node in main.body if isinstance(node, ast.Assign)
        and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name)
        and node.targets[0].id == 'partitions'], 'native Memory partition assignment')
    if not isinstance(assignment.value, ast.DictComp):
        raise SourceBindingError('NATIVE_INITIAL_PARTITION_SOURCE_SHAPE')
    scope = {'snapshot': snapshot,
             'MemorySourcePartitionBindingV1': consumer_views.MemorySourcePartitionBindingV1,
             'MemorySourcePartitionV1': consumer_views.MemorySourcePartitionV1}
    exec(compile(ast.Module(body=[assignment], type_ignores=[]),
                 'registered_run_role_view_smoke_v1::partitions', 'exec'), scope)
    return scope['partitions']


def _memory_modules(repo):
    src = repo / 'src'
    for name, module in tuple(sys.modules.items()):
        if name.startswith('pchsi.') and getattr(module, '__file__', None):
            if not Path(module.__file__).resolve().is_relative_to(src.resolve()):
                raise SourceBindingError('SCIENTIFIC_REPO_IMPORT_CONFLICT:' + name)
    sys.path.insert(0, str(src))
    return (importlib.import_module('pchsi.memory.dev_snapshot_loader'),
            importlib.import_module('pchsi.memory.consumer_views'))


def build_source_binding(result, *, layout, output_root, current_index=None,
                         source_partition_by_lineage=None):
    """Internal entry for both operations; reads current authorities and produces a view.

The parent may pass already-loaded native partition objects from its Memory
producer. Otherwise the finite typed index may register their exact serialized
mapping as refs.memory_source_partitions. No operator-filled configuration is used.
    """
    sources = inspect_registered_sources(layout)
    current = current_memory_inputs(result)
    index = current_index or {}
    if 'path' in index and 'file_sha256' in index:
        index = _read_ref(index)
    if index.get('round_id', result['round_id']) != result['round_id']:
        raise SourceBindingError('CURRENT_INDEX_ROUND_IDENTITY')
    if index.get('request_sha256', result['request_sha256']) != result['request_sha256']:
        raise SourceBindingError('CURRENT_INDEX_REQUEST_IDENTITY')
    repo, git_repo = resolve_scientific_repo(sources, layout, result['implementation_worktree'])
    tracked_ref = _tracked_ref if git_repo is None else partial(_tracked_ref, git_repo=git_repo)
    refs = dict(sources['refs'])
    for name, relative in REPO_REFS.items():
        refs[name] = tracked_ref(repo, sources['scientific_repo_head'], relative)
    refs['analyzer_token_contract'] = _ref(current['token_contract_path'])
    if _read_ref(refs['analyzer_token_contract']).get('contract_sha256') != current['request']['token_budget_contract_sha256']:
        raise SourceBindingError('CURRENT_TOKEN_CONTRACT_IDENTITY')
    # Verify the native producer's exact implementation objects before importing.
    for relative in ('src/pchsi/memory/dev_snapshot_loader.py', 'src/pchsi/memory/consumer_views.py'):
        tracked_ref(repo, sources['scientific_repo_head'], relative)
    loader, views = _memory_modules(repo)
    snapshot = loader.load_calibrated_dev_snapshot_v2(
        snapshot_directory=Path(current['snapshot_directory']),
        expected_snapshot_sha256=current['request']['round_start_memory_snapshot_sha256'],
        token_budget_contract_path=Path(current['token_contract_path']),
        expected_token_budget_contract_sha256=current['request']['token_budget_contract_sha256'])
    indexed = index.get('refs', {})
    aggregate_context = None
    if 'previous_select_context' in indexed:
        from analyzer_binding.aggregate_context import validate_previous_select_context
        aggregate_context = validate_previous_select_context(
            _read_ref(indexed['previous_select_context']), current_request=current['request'])
        refs['previous_select_context'] = indexed['previous_select_context']
    if source_partition_by_lineage is None and 'memory_source_partitions' in indexed:
        rows = _read_ref(indexed['memory_source_partitions'])
        source_partition_by_lineage = {}
        for lineage, row in rows.items():
            binding = views.MemorySourcePartitionBindingV1(**{
                **row, 'source_partition': views.MemorySourcePartitionV1(row['source_partition']),
                'authority_scope': views.MemoryPartitionAuthorityScopeV1(row['authority_scope'])})
            if binding.memory_lineage_id != lineage:
                raise SourceBindingError('PARTITION_LINEAGE_IDENTITY:' + lineage)
            source_partition_by_lineage[lineage] = binding
    if source_partition_by_lineage is None and not ({'researcher_view', 'researcher_views'} & indexed.keys()):
        dependency_ref = tracked_ref(repo, sources['scientific_repo_head'],
            'configs/memory/package_b_failure_memory_dependency_v1.json')
        dependency = _read_ref(dependency_ref)
        if dependency['active_snapshot_sha256'] == current['request']['round_start_memory_snapshot_sha256']:
            producer_ref = tracked_ref(repo, sources['scientific_repo_head'],
                'scripts/memory/run_role_view_smoke_v1.py')
            source_partition_by_lineage = initial_source_partitions(snapshot=snapshot,
                dependency=dependency, native_source=_raw(producer_ref['path'], producer_ref['file_sha256']),
                consumer_views=views)
    if source_partition_by_lineage is not None:
        # Carry the exact native authority objects into closure and the next round.
        # This is the same map consumed by the native view builder below.
        refs['memory_source_partitions'] = _write_once(
            Path(output_root) / 'MEMORY_SOURCE_PARTITIONS_V1.json',
            {lineage: partition.to_dict() for lineage, partition in
             sorted(source_partition_by_lineage.items())})
        refs['researcher_view'] = materialize_researcher_view(snapshot=snapshot,
            source_partition_by_lineage=source_partition_by_lineage,
            expected_snapshot_sha256=current['request']['round_start_memory_snapshot_sha256'],
            output_root=output_root, consumer_views=views,
            aggregate_context=aggregate_context, current_request=current['request'])
    elif 'researcher_view' in indexed or 'researcher_views' in indexed:
        candidates = indexed.get('researcher_views', [indexed.get('researcher_view')])
        if not isinstance(candidates, list) or not candidates:
            raise SourceBindingError('RESEARCHER_VIEW_REFS_EMPTY')
        for ref in candidates:
            value = _read_ref(ref)
            if value.get('snapshot_sha256') != current['request']['round_start_memory_snapshot_sha256']:
                raise SourceBindingError('RESEARCHER_VIEW_CURRENT_SNAPSHOT_IDENTITY')
            if value.get('heldout_aggregate_metrics') != (aggregate_context or {}):
                raise SourceBindingError('RESEARCHER_VIEW_SELECT_CONTEXT_IDENTITY')
            parsed = views.ResearcherMemoryViewV1(snapshot_sha256=value['snapshot_sha256'],
                purpose=views.ResearcherPurposeV1(value['purpose']),
                train_side_records=tuple(value['train_side_records']), round_evidence=value['round_evidence'],
                heldout_aggregate_metrics=value['heldout_aggregate_metrics'], view_sha256=value['view_sha256'])
            if parsed.to_dict() != value or parsed.purpose != views.ResearcherPurposeV1.ROUND_RESEARCH_PLANNING:
                raise SourceBindingError('RESEARCHER_VIEW_NATIVE_IDENTITY')
        refs['researcher_views'] = candidates
    else:
        raise SourceBindingError('SOURCE_PARTITION_LOCATOR_MISSING:/source_partition_by_lineage;'
            ' native producer= pchsi.memory.consumer_views.build_researcher_memory_view_v1;'
            ' current snapshot differs from registered bootstrap; current Memory producer must transport its partition bindings')
    return {'scientific_repo_root': str(repo), 'analyzer_snapshot_directory': current['snapshot_directory'],
            'train_root': sources['train_root'], 'packages': sources['packages'], 'refs': refs,
            'source_registration': {'source_plan_file_sha256': SOURCE_PLAN_SHA256,
                                    'scientific_repo_head': sources['scientific_repo_head']}}
