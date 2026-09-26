"""Carry the exact Memory extension into inherited Python worker processes."""
import os
from pathlib import Path

from .source_overlay import install_memory_overlay

REPO_ENV = 'PCHSI_CURRENT_MEMORY_NATIVE_REPO'


def worker_environment(repo, *, base_environment=None):
    """Return an environment for ordinary Python children, without starting one.

    repo is the authority-resolved exact scientific checkout. Fixed module hashes
    are checked at every interpreter startup; no directory search is performed.
    """
    repo = Path(repo).absolute()
    from .source_overlay import BASE_SHA256, adapt_source
    for name in BASE_SHA256:
        adapt_source(name, (repo / 'src' / (name.replace('.', '/') + '.py')).read_bytes())
    environment = dict(os.environ if base_environment is None else base_environment)
    existing = environment.get(REPO_ENV)
    if existing is not None and Path(existing).absolute() != repo:
        raise ValueError('MEMORY_WORKER_REPO_CONFLICT')
    package = Path(__file__).resolve().parent
    prefix = [str(package / 'worker_startup'), str(package.parent)]
    paths = prefix + [p for p in environment.get('PYTHONPATH', '').split(os.pathsep) if p and p not in prefix]
    environment['PYTHONPATH'] = os.pathsep.join(paths)
    environment[REPO_ENV] = str(repo)
    environment['PYTHONDONTWRITEBYTECODE'] = '1'
    return environment


def bootstrap_current_and_children(repo):
    """Call before native imports in the owner, before it launches any workers."""
    environment = worker_environment(repo)
    receipt = install_memory_overlay(repo)
    # Pin the namespace to the registered checkout before legacy scripts prepend
    # their captured source roots. All pchsi submodules then share one authority.
    import pchsi
    expected = Path(repo).absolute() / 'src' / 'pchsi'
    if list(pchsi.__path__) != [str(expected)]:
        raise ValueError('MEMORY_WORKER_NATIVE_NAMESPACE_CONFLICT')
    for key in ('PYTHONPATH', REPO_ENV, 'PYTHONDONTWRITEBYTECODE'):
        os.environ[key] = environment[key]
    return receipt
