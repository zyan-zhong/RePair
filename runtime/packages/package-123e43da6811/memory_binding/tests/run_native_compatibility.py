"""Run unchanged affected native suites; Windows excludes explicit POSIX checks."""
import os
from pathlib import Path
import sys

root = Path(__file__).resolve().parents[4]
native = root / 'work/v17/native_bba_full'
sys.path.insert(0, str(root / 'work/v17'))
from memory_binding.source_overlay import install_memory_overlay
install_memory_overlay(native)
os.chdir(native)
arguments = ['-q', '-p', 'no:cacheprovider', '--tb=short']
if sys.platform == 'win32':
    from pchsi.memory import dev_descriptive_snapshot_v2 as snapshots, candidate_materialization as candidates
    def binary_write(path, raw):
        with Path(path).open('xb') as stream:
            stream.write(raw)
    snapshots._write_once = binary_write
    snapshots._fsync_directory = lambda path: None
    candidates._write_once = binary_write
    arguments += ['-k', 'not symlink and not materializer_writes_exact_canonical_bytes_once and not parent_directory_fsync_failure']
arguments += ['tests/memory/' + name for name in (
    'test_sequence_failure_experience.py', 'test_memory_round_maintenance_v1.py',
    'test_memory_component_ports_v1.py', 'test_memory_consumer_views_v1.py',
    'test_procedural_memory_builder.py', 'test_package_a_a6_candidate_materialization.py')]
import pytest
raise SystemExit(pytest.main(arguments))
