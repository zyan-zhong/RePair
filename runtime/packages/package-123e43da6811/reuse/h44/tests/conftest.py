from pathlib import Path
import atexit
import os
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'native_repo' / 'src'))

# Package tests are self-contained.  Extract the frozen E capture fixture outside
# the package tree so test artifacts can never invalidate PACKAGE_FILES.sha256.
_fixture_zip = Path(__file__).resolve().parent / 'fixtures' / 'E_SOURCE_CAPTURE.zip'
_fixture_root = Path(tempfile.mkdtemp(prefix='pchsi-e-source-'))
with zipfile.ZipFile(_fixture_zip) as _zip:
    root = _fixture_root.resolve()
    for info in _zip.infolist():
        target = (_fixture_root / info.filename).resolve()
        if target != root and root not in target.parents:
            raise RuntimeError('TEST_FIXTURE_ZIP_PATH_ESCAPE')
    _zip.extractall(_fixture_root)
os.environ['PCHSI_TEST_EVIDENCE_ROOT'] = str(_fixture_root)
atexit.register(lambda: shutil.rmtree(_fixture_root, ignore_errors=True))
