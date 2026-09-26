"""Isolated H4.4 execution; original scientific functions stay unchanged."""
from __future__ import annotations

import argparse
import os
import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from exact_bindings import BindingError, read_json, read_ref


def exact_post_source(source):
    old = 'PCHSI_V1232Z_TERMINAL_V1.json'
    if source.count(old) != 4:
        raise BindingError('H44_POST_LOCATOR_SOURCE_DRIFT')
    source = source.replace(old, 'ACCEPTED_PRE_REF.json')
    old_scan = "manifests=list((inp/'schema_compatibility_repair').glob('*/REPAIRED_RUNTIME_MANIFEST_V1.json'))"
    if source.count(old_scan) != 1:
        raise BindingError('H44_POST_MANIFEST_LOCATOR_SOURCE_DRIFT')
    return source.replace(old_scan, "manifests=[inp/'EXACT_RUNTIME_MANIFEST.json']")


def load_current_post_module(request, root):
    """One original POST runtime, extended with its current native dataset."""
    from post_binding.source_overlay import adapt_strong_post
    from post_binding.context import materialize_post_context
    from exact_bindings import digest
    manifest = read_ref(request['h44_manifest'], as_bytes=True).decode('utf8')
    registered = {}
    for line in manifest.splitlines():
        if not line.strip():
            continue
        expected, member = line.split(maxsplit=1)
        member = member.lstrip('*')
        if member in registered:
            raise BindingError('H44_SOURCE_MANIFEST_DUPLICATE_MEMBER')
        registered[member] = expected
    raw = (root / 'strong_post.py').read_bytes()
    if digest(raw) != registered.get('strong_post.py'):
        raise BindingError('H44_REGISTERED_POST_SOURCE_SHA')
    source = adapt_strong_post(raw.decode('utf8'), expected_source_sha256=registered['strong_post.py'])
    module = types.ModuleType('strong_post'); module.__file__ = str(root / 'strong_post.py')
    exec(compile(exact_post_source(source), module.__file__, 'exec'), module.__dict__)
    original = module.execute_post

    def execute_post(run_root, plan, verifier):
        from source_adapter import load_source_rows
        context = materialize_post_context(request=request, run_root=run_root, plan=plan,
            verifier=verifier, source_loader=load_source_rows)
        module._POST_MATERIALIZATION_CONTEXT = context['recipe_context']
        return original(run_root, plan, verifier)

    module.execute_post = execute_post
    sys.modules['strong_post'] = module
    return module


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--request', type=Path, required=True)
    args = parser.parse_args(); request = read_json(args.request.absolute())
    root = Path(request['h44_root']); run = Path(request['run_root']); run.mkdir(parents=True, exist_ok=True)
    read_ref(request['capture'], as_bytes=True); read_ref(request['memory_runtime'])
    from memory_binding.worker_bootstrap import bootstrap_current_and_children
    bootstrap_current_and_children(request['scientific_repo_root'])
    from policy_binding.h44_overlay import configure_h44_workers
    configure_h44_workers(root)
    sys.path[:0] = [str(root), str(root / 'native_repo' / 'src')]
    from round_plan import prepare_plan
    from controller import run_controller, require_current_causal_release
    from io_utils import read_json as native_read
    os.environ[request['locators']['memory_runtime_environment_variable']] = request['memory_runtime']['path']
    load_current_post_module(request, root)
    plan_path = run / 'EXECUTION_PLAN.json'
    if plan_path.exists():
        plan = native_read(plan_path)
        if plan['capture_zip_sha256'] != request['capture']['file_sha256']:
            raise BindingError('H44_EXISTING_PLAN_CAPTURE_MISMATCH')
    else:
        prepare_plan(capture_zip=request['capture']['path'], expected_sha256=request['capture']['file_sha256'],
            run_root=run, locators=request['locators'], operations=native_read(root / 'assets/operational_policy.json'))
    if request['execute']:
        require_current_causal_release()
        return run_controller(run)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
