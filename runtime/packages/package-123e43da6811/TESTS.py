"""Fresh isolated software fixtures. Never submits work or contacts a provider."""
from pathlib import Path, PurePosixPath
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent


def extract(archive, destination, mapping=lambda value: value):
    with zipfile.ZipFile(archive) as z:
        seen = set()
        for row in z.infolist():
            name = PurePosixPath(row.filename)
            if name.is_absolute() or '..' in name.parts or '\\' in row.filename or row.filename in seen:
                raise ValueError('FIXTURE_ARCHIVE_MEMBER_INVALID')
            seen.add(row.filename)
            if row.is_dir():
                continue
            mapped = mapping(name)
            if mapped is None:
                continue
            out = destination / mapped
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(z.read(row))


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--groups', nargs='+', type=int, choices=range(1, 6))
    selected = parser.parse_args().groups
    from entry.preflight import verify_package
    verify_package(ROOT)
    with tempfile.TemporaryDirectory(prefix='pchsi_v17_fresh_fixture_') as temporary:
        target = Path(temporary).resolve()
        def v16(name):
            # Archive contains exactly one registered outer package directory.
            parts = name.parts[1:]
            if not parts:
                return None
            category, *tail = parts
            if category == 'reuse':
                if tail[0] == 'h44':
                    return Path('work/reference_g2/PCHSI_PAPER_CRITICAL_CAUSAL_ROUND_EXECUTION_V1_23_3H4_4', *tail[1:])
                if tail[0] == 'native_bba':
                    return Path('work/native_bba', *tail[1:])
                return Path('work/v16/reference', *tail)
            if category == 'registered_sources':
                return Path('work/v16/received', *tail)
            if category == 'authority':
                return Path('work/v14_live_export/current_v14/authority', *tail)
            if category in ('rollout_adapter', 'analyzer_adapter', 'entry'):
                return Path('work/v16', *parts)
            return None
        extract(ROOT / 'validation/V16_SEALED_FIXTURE.zip', target, v16)
        extract(ROOT / 'validation/NATIVE_BBA_EXACT_FIXTURE.zip', target / 'work/v17')
        git_cache = target / 'work/v17/registered_git_cache'
        subprocess.run(['git', 'init', '--quiet', str(git_cache)], check=True)
        with (ROOT / 'validation/NATIVE_GIT_OBJECTS.pack').open('rb') as stream:
            subprocess.run(['git', '-C', str(git_cache), 'index-pack', '--stdin'], stdin=stream,
                           stdout=subprocess.PIPE, check=True)
        archived = target / 'work/v17/native_bba_full_blob_exact.zip'
        shutil.copyfile(ROOT / 'validation/NATIVE_BBA_EXACT_FIXTURE.zip', archived)
        captured = json.loads((ROOT / 'evidence/NATIVE_BBA_FULL_SOURCE_RECEIPT_V2.json').read_bytes())
        captured['archive_path'] = str(archived)
        captured['extracted_root'] = str(target / 'work/v17/native_bba_full')
        (target / 'work/v17/NATIVE_BBA_FULL_SOURCE_RECEIPT_V2.json').write_text(json.dumps(captured) + '\n', encoding='utf8')
        request = target / 'work/v14_live_export/current_v14/authority/ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json'
        request.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / 'validation/ROUND_ROLLOUT_COLLECTION_REQUEST_V1.json', request)
        registry = json.loads((ROOT / 'TEST_FIXTURE_REGISTRY.json').read_bytes())
        for member, destination in registry['copy_members'].items():
            out = target / destination
            out.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / member, out)
        groups = [
            ['work/v17/training_binding/tests', 'work/v17/post_binding/tests'],
            ['work/v17/continuity_binding/tests', 'work/v17/offoff_binding/tests', 'work/v17/entry/tests'],
            ['work/v17/policy_binding/tests', 'work/v17/memory_binding/tests'],
            ['work/v17/analyzer_binding/tests'],
            ['work/v17/memory_binding/tests/run_native_compatibility.py'],
        ]
        if selected:
            groups = [groups[n - 1] for n in selected]
        results = []
        for group in groups:
            argv = ([sys.executable, '-B', group[0]] if group[0].endswith('run_native_compatibility.py') else
                    [sys.executable, '-B', '-m', 'pytest', *group, '-q', '-p', 'no:cacheprovider', '--tb=short'])
            result = subprocess.run(argv, cwd=target, check=False)
            results.append({'tests': group, 'returncode': result.returncode})
            if result.returncode:
                break
        record = {'schema_id': 'FRESH_UNZIP_CURRENT_ENTRY_SOFTWARE_VERIFICATION_V1',
            'groups': results, 'provider_call_count': 0, 'slurm_submission_count': 0,
            'training_execution_count': 0, 'production_readiness_inferred': False}
        print(json.dumps(record, sort_keys=True), flush=True)
        return 0 if len(results) == len(groups) and all(x['returncode'] == 0 for x in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
