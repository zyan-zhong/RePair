"""Find the Python interpreter from the registered native operational request."""
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def main():
    from entry.preflight import verify_package, _raw
    from entry.registration import build_deployment
    identity, _ = verify_package(ROOT)
    deployment = build_deployment(ROOT, entry_source_sha256=identity)
    registration = deployment['training_source_registration']
    request = json.loads(_raw(registration['operational_request_ref']))
    python = Path(request['python'])
    if not python.is_absolute() or not python.is_file():
        raise ValueError('REGISTERED_PYTHON_INTERPRETER_UNAVAILABLE')
    print(str(python))


if __name__ == '__main__':
    main()
