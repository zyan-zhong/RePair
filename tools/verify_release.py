#!/usr/bin/env python3
"""Check the explicit public inventory without resolving any runtime receipt."""
from pathlib import Path, PurePosixPath
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT / 'RELEASE_MANIFEST.json').read_bytes())
    names = set()
    for row in manifest['files']:
        name = row['path']
        relative = PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or name in names:
            raise ValueError('INVALID_RELEASE_MEMBER')
        names.add(name)
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError('MISSING_OR_NONREGULAR_RELEASE_MEMBER:' + name)
        if hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('RELEASE_HASH_MISMATCH:' + name)
    exports = json.loads((ROOT / 'runtime/PUBLIC_EXPORT.json').read_bytes())
    for row in exports['excluded']:
        if (ROOT / row['path']).exists():
            raise ValueError('WITHHELD_PRIVATE_FILE_PRESENT:' + row['path'])
    print(json.dumps({'status': 'PUBLIC_RELEASE_VERIFIED', 'files': len(names),
                      'production_execution_started': False}, indent=2))


if __name__ == '__main__':
    main()
