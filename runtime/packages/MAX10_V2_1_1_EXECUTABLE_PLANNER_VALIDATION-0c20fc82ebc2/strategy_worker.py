"""Existing durable POST/recipe worker with registered strategy execution hooks."""
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch
import importlib.util,json,sys
ROOT=Path(__file__).resolve().parent

def main():
    from entry_v208 import verify,checked,load_module
    verify();a=json.loads((ROOT/'AUTHORITY.json').read_bytes())
    from runtime_setup import child_bootstrap,post_representation
    child_bootstrap(a)
    prior=a['feedback_worker_ref'];checked(prior,as_bytes=True)
    sys.path.insert(0,str(Path(prior['path']).parent))
    feedback=load_module('_v207_feedback_worker',Path(prior['path']))
    native=feedback.facts_scope
    @contextmanager
    def scope(*args):
        from strategy_hooks import worker_scope
        request=json.loads(Path(sys.argv[sys.argv.index('--request')+1]).read_bytes())
        binding=checked(request['registered_transport_binding'])
        impl={'path':str(ROOT/'IMPLEMENTATION.json'),'sha256':__import__('hashlib').sha256((ROOT/'IMPLEMENTATION.json').read_bytes()).hexdigest()}
        with native(*args),worker_scope(binding['refs']['cue_strategy_registry'],impl,gpu_entry=ROOT/'strategy_gpu.py'):
            yield
    with post_representation(a),patch.object(feedback,'facts_scope',scope):return feedback.main()

if __name__=='__main__':raise SystemExit(main())
