"""Process startup only when the owning entry explicitly supplies the authority."""
import os

_repo = os.environ.get('PCHSI_CURRENT_MEMORY_NATIVE_REPO')
if _repo:
    try:
        from memory_binding.worker_bootstrap import bootstrap_current_and_children
        bootstrap_current_and_children(_repo)
        if os.environ.get('PCHSI_CURRENT_H44_REGISTERED_ROOT'):
            from policy_binding.h44_overlay import configure_h44_workers
            configure_h44_workers(os.environ['PCHSI_CURRENT_H44_REGISTERED_ROOT'])
    except Exception as exc:
        # Python normally swallows sitecustomize Exception. SystemExit makes a
        # rejected exact-source extension fail before the worker can execute.
        raise SystemExit('CURRENT_MEMORY_WORKER_BOOTSTRAP_FAILED:' + str(exc)) from exc
