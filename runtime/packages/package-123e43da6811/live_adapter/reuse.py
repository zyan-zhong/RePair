"""Load only explicitly bound, manifest-checked scientific source modules."""
from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

from exact_bindings import BindingError, digest, regular, read_ref


def load_file(name, path):
    path = regular(Path(path).absolute())
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def package_root(binding, name):
    bound = binding['packages'][name]
    if not isinstance(bound, dict) or 'manifest' not in bound:
        raise BindingError('PACKAGE_MANIFEST_REF_REQUIRED:' + name)
    root = Path(bound['root']).absolute()
    raw = read_ref(bound['manifest'], as_bytes=True)
    for line in raw.decode('utf-8').splitlines():
        if not line.strip():
            continue
        expected, rel = line.split(maxsplit=1)
        rel = rel.lstrip('*')
        path = root / rel
        if not path.resolve().is_relative_to(root.resolve()):
            raise BindingError('PACKAGE_MEMBER_ESCAPE:' + name)
        if digest(regular(path).read_bytes()) != expected:
            raise BindingError('PACKAGE_SOURCE_HASH:' + name + ':' + rel)
    return root


def load_cores(binding):
    repo = Path(binding['scientific_repo_root']).absolute()
    repo_src = repo / 'src'
    # Never silently adopt modules already imported from a different checkout.
    for name, module in tuple(sys.modules.items()):
        if name.startswith('pchsi.') and getattr(module, '__file__', None):
            if not Path(module.__file__).resolve().is_relative_to(repo_src.resolve()):
                raise BindingError('SCIENTIFIC_REPO_IMPORT_CONFLICT:' + name)
    sys.path.insert(0, str(repo_src))
    qroot, uroot, xroot = (package_root(binding, name) for name in ('q', 'u', 'x'))
    h44 = package_root(binding, 'h44')
    compatibility = load_file('_exact_schema_compatibility', h44 / 'structured_output_schema_compatibility.py')
    q = load_file('_exact_q', qroot / 'v1232q_driver.py')
    for name, path in (
        ('source_context_equivalence', uroot / 'source_context_equivalence.py'),
        ('dynamic_primary_pre_v2', xroot / 'dynamic_primary_pre_v2.py'),
        ('dynamic_pre_v2_semantic_normalization', xroot / 'dynamic_pre_v2_semantic_normalization.py'),
        ('current_round_researcher_memory_v1', xroot / 'current_round_researcher_memory_v1.py'),
        ('infra_recovery_disposition', xroot / 'infra_recovery_disposition.py'),
    ):
        existing = sys.modules.get(name)
        if existing is not None and digest(Path(existing.__file__).read_bytes()) != digest(path.read_bytes()):
            raise BindingError('SOURCE_MODULE_COLLISION:' + name)
        if existing is None:
            load_file(name, path)
    u = load_file('_exact_u', uroot / 'v1232u_driver.py')
    x = load_file('_exact_x', xroot / 'v1232x_driver.py')
    from pchsi.reference_loop.canonical import domain_hash
    from pchsi.reference_loop.bundle_reader import validate_attempt_bundle
    from pchsi.reference_loop.mechanical import extract_mechanical_episode_evidence
    from pchsi.cognitive_runtime import orchestrator, request_renderer, projections, registry_runner
    from pchsi.cognitive_runtime.identity import build_scientific_unit_identity
    from pchsi.cognitive_runtime.schema_registry import validate_artifact
    from pchsi.analyzer.outcome_router import route_episode
    from pchsi.memory.consumer_views import ResearcherMemoryViewV1, ResearcherPurposeV1
    from pchsi.round_control import clean_analyzer_input_materialization as clean
    api = u.preflight_api()
    api.update(q.assert_fixed_head_api_contract(repo))
    api.update(validate_attempt_bundle=validate_attempt_bundle)
    return SimpleNamespace(q=q, u=u, x=x, api=api, domain_hash=domain_hash,
        validate_bundle=validate_attempt_bundle, mechanical=extract_mechanical_episode_evidence,
        orch=orchestrator, rr=request_renderer, projections=projections, runner=registry_runner,
        identity=build_scientific_unit_identity, validate_artifact=validate_artifact,
        route=route_episode, clean=clean, researcher_view=ResearcherMemoryViewV1,
        researcher_purpose=ResearcherPurposeV1, repo=repo, schema_compatibility=compatibility)
