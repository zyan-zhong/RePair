from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path


P2_ROOT = Path("/data/run01/scwb204/pchsi/p2")

PACKAGE = (
    P2_ROOT
    / "p2_strong_offline_proposer_openai_v1_r1_3_2"
)

RUN = (
    P2_ROOT
    / "p2_strong_offline_proposer_openai_v1_run_r1_3_2"
)

LOG = (
    P2_ROOT
    / "logs/p2_r132_primary117/primary117.log"
)

Q2_BINDINGS = (
    P2_ROOT
    / "p2_pre_model_call_package_v1"
    / "contracts/q2_state_bindings.jsonl"
)

OUT = Path(
    "/data/home/scwb204/run/pchsi/scripts/"
    "p4_round1_canonical_gap_audit_v1"
)

CASE_MANIFEST = (
    PACKAGE
    / "manifests/primary_case_manifest.jsonl"
)

REQUEST_MANIFEST = (
    PACKAGE
    / "manifests/primary_requests.jsonl"
)

EXPECTED_PACKAGE_FREEZE = (
    "794727df6157715d3c8e04156f97e533"
    "00ef9107ca793d215caec447cab964b5"
)

CASE_RE = re.compile(
    r"p2-r0-alfworld_valid_unseen_all134_\d{4}"
)

HEX64_RE = re.compile(
    r"^[0-9a-f]{64}$"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def load_json(path: Path) -> dict:
    value = json.loads(
        path.read_text(encoding="utf-8")
    )

    if not isinstance(value, dict):
        raise ValueError(
            f"expected JSON object: {path}"
        )

    return value


def load_jsonl(path: Path) -> list[dict]:
    rows = []

    for line_no, raw in enumerate(
        path.read_text(
            encoding="utf-8"
        ).splitlines(),
        1,
    ):
        if not raw.strip():
            continue

        value = json.loads(raw)

        if not isinstance(value, dict):
            raise ValueError(
                f"JSONL row not object: "
                f"{path}:{line_no}"
            )

        rows.append(value)

    return rows


def walk(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            yield from walk(
                item,
                path + (str(key),),
            )

    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from walk(
                item,
                path + (str(index),),
            )

    else:
        yield path, value


def extract_case_id(value: object) -> str:
    candidates = set()

    for path, item in walk(value):
        if not isinstance(item, str):
            continue

        if path:
            leaf = path[-1].lower()

            if leaf in {
                "case_id",
                "primary_case_id",
                "source_case_id",
            }:
                if CASE_RE.fullmatch(item):
                    candidates.add(item)

        for match in CASE_RE.findall(item):
            candidates.add(match)

    if len(candidates) != 1:
        serialized = json.dumps(
            value,
            sort_keys=True,
            ensure_ascii=False,
        )

        candidates.update(
            CASE_RE.findall(serialized)
        )

    if len(candidates) != 1:
        raise ValueError({
            "type":
                "case_id_not_unique",
            "candidates":
                sorted(candidates),
        })

    return next(iter(candidates))


def all_sha256_values(value: object) -> set[str]:
    values = set()

    for _, item in walk(value):
        if (
            isinstance(item, str)
            and HEX64_RE.fullmatch(item)
        ):
            values.add(item)

    return values


def client_request_ids(value: object) -> set[str]:
    values = set()

    for path, item in walk(value):
        if not isinstance(item, str):
            continue

        joined = ".".join(
            p.lower()
            for p in path
        )

        if (
            "client_request_id" in joined
            or "x_client_request_id" in joined
        ):
            values.add(item)

    return values


def terminal_label(value: dict) -> str:
    preferred = (
        "terminal_status",
        "terminal_reason",
        "terminal_class",
        "disposition",
        "status",
        "reason",
        "outcome",
    )

    for key in preferred:
        item = value.get(key)

        if isinstance(item, str):
            return f"{key}={item}"

    return "UNRESOLVED_TERMINAL_LABEL"


for required in (
    PACKAGE,
    RUN,
    LOG,
    Q2_BINDINGS,
    CASE_MANIFEST,
    REQUEST_MANIFEST,
):
    if not required.exists():
        raise SystemExit(
            f"MISSING_REQUIRED={required}"
        )


log_text = LOG.read_text(
    encoding="utf-8",
    errors="replace",
)

if EXPECTED_PACKAGE_FREEZE not in log_text:
    raise SystemExit(
        "R132_PACKAGE_FREEZE_MARKER_MISMATCH"
    )


case_rows = load_jsonl(
    CASE_MANIFEST
)

request_rows = load_jsonl(
    REQUEST_MANIFEST
)

q2_rows = load_jsonl(
    Q2_BINDINGS
)


if len(case_rows) != 117:
    raise SystemExit(
        f"CASE_MANIFEST_COUNT={len(case_rows)}"
    )

if len(request_rows) != 117:
    raise SystemExit(
        f"REQUEST_MANIFEST_COUNT="
        f"{len(request_rows)}"
    )

if len(q2_rows) != 351:
    raise SystemExit(
        f"Q2_BINDING_COUNT={len(q2_rows)}"
    )


case_by_id = {}

for row in case_rows:
    case_id = extract_case_id(row)

    if case_id in case_by_id:
        raise SystemExit(
            f"DUPLICATE_CASE_MANIFEST_ID="
            f"{case_id}"
        )

    case_by_id[case_id] = row


request_by_id = {}

for row in request_rows:
    case_id = extract_case_id(row)

    if case_id in request_by_id:
        raise SystemExit(
            f"DUPLICATE_REQUEST_MANIFEST_ID="
            f"{case_id}"
        )

    request_by_id[case_id] = row


if set(case_by_id) != set(request_by_id):
    raise SystemExit(
        "CASE_REQUEST_MANIFEST_ID_SET_MISMATCH"
    )


q2_per_case = Counter()

for row in q2_rows:
    q2_per_case[
        extract_case_id(row)
    ] += 1


if set(q2_per_case) != set(case_by_id):
    raise SystemExit(
        "Q2_CASE_ID_SET_MISMATCH"
    )

bad_q2 = {
    case_id: count
    for case_id, count
    in sorted(q2_per_case.items())
    if count != 3
}

if bad_q2:
    raise SystemExit(
        f"Q2_BINDING_MULTIPLICITY_MISMATCH="
        f"{bad_q2}"
    )


cases_root = RUN / "cases"

observed_dirs = {
    path.name
    for path in cases_root.iterdir()
    if (
        path.is_dir()
        and CASE_RE.fullmatch(path.name)
    )
}

if observed_dirs != set(case_by_id):
    raise SystemExit({
        "type":
            "RUN_CASE_DIRECTORY_SET_MISMATCH",
        "missing":
            sorted(
                set(case_by_id)
                - observed_dirs
            ),
        "unexpected":
            sorted(
                observed_dirs
                - set(case_by_id)
            ),
    })


blockers = []
warnings = []
rows_out = []
terminal_counts = Counter()

teacher_output_count = 0
rejection_count = 0
raw_response_count = 0
call_evidence_count = 0
transport_attempt_count = 0


for case_id in sorted(case_by_id):

    case_dir = cases_root / case_id

    started = (
        case_dir / "started.json"
    )

    request_body = (
        case_dir / "raw_request_body.bin"
    )

    terminal = (
        case_dir / "terminal.json"
    )

    teacher = (
        case_dir / "teacher_output.json"
    )

    rejection = (
        case_dir / "rejection.json"
    )

    raw_response = (
        case_dir / "raw_response_body.bin"
    )

    call_evidence = (
        case_dir / "call_evidence.json"
    )

    missing_required = [
        name
        for name, path in (
            ("started.json", started),
            (
                "raw_request_body.bin",
                request_body,
            ),
            ("terminal.json", terminal),
        )
        if not path.is_file()
    ]

    if missing_required:
        blockers.append({
            "case_id":
                case_id,
            "type":
                "MISSING_REQUIRED_LEDGER_FILE",
            "files":
                missing_required,
        })

        continue


    teacher_present = teacher.is_file()
    rejection_present = rejection.is_file()

    if (
        int(teacher_present)
        + int(rejection_present)
        != 1
    ):
        blockers.append({
            "case_id":
                case_id,
            "type":
                "TEACHER_REJECTION_EXCLUSIVITY",
            "teacher_output":
                teacher_present,
            "rejection":
                rejection_present,
        })

    teacher_output_count += int(
        teacher_present
    )

    rejection_count += int(
        rejection_present
    )


    request_sha = sha256_file(
        request_body
    )

    manifest_hashes = (
        all_sha256_values(
            case_by_id[case_id]
        )
        |
        all_sha256_values(
            request_by_id[case_id]
        )
    )

    if request_sha not in manifest_hashes:
        blockers.append({
            "case_id":
                case_id,
            "type":
                "REQUEST_BYTE_SHA_NOT_BOUND_"
                "IN_FINAL_MANIFESTS",
            "observed_request_sha256":
                request_sha,
        })


    evidence_objects = [
        case_by_id[case_id],
        request_by_id[case_id],
        load_json(started),
    ]

    if call_evidence.is_file():
        call_evidence_count += 1

        evidence_objects.append(
            load_json(call_evidence)
        )

    transport_meta = sorted(
        (
            case_dir
            / "transport_attempts"
        ).glob("*.json")
    )

    transport_attempt_count += len(
        transport_meta
    )

    for path in transport_meta:
        evidence_objects.append(
            load_json(path)
        )


    request_ids = set()

    for obj in evidence_objects:
        request_ids.update(
            client_request_ids(obj)
        )

    if len(request_ids) > 1:
        blockers.append({
            "case_id":
                case_id,
            "type":
                "CLIENT_REQUEST_ID_MISMATCH",
            "values":
                sorted(request_ids),
        })


    raw_response_sha = None

    if raw_response.is_file():
        raw_response_count += 1

        raw_response_sha = sha256_file(
            raw_response
        )

        attempt_responses = sorted(
            (
                case_dir
                / "transport_attempts"
            ).glob("*.response.bin")
        )

        if (
            attempt_responses
            and raw_response_sha
            not in {
                sha256_file(path)
                for path in attempt_responses
            }
        ):
            blockers.append({
                "case_id":
                    case_id,
                "type":
                    "RAW_RESPONSE_NOT_EQUAL_"
                    "TO_ANY_TRANSPORT_RESPONSE",
                "raw_response_sha256":
                    raw_response_sha,
            })

        if call_evidence.is_file():
            call_hashes = all_sha256_values(
                load_json(call_evidence)
            )

            if (
                raw_response_sha
                not in call_hashes
            ):
                warnings.append({
                    "case_id":
                        case_id,
                    "type":
                        "RAW_RESPONSE_SHA_NOT_"
                        "DISCOVERED_IN_CALL_EVIDENCE",
                    "sha256":
                        raw_response_sha,
                })


    terminal_obj = load_json(
        terminal
    )

    terminal_counts[
        terminal_label(
            terminal_obj
        )
    ] += 1


    all_files = sorted(
        path
        for path in case_dir.rglob("*")
        if path.is_file()
    )

    rows_out.append({
        "case_id":
            case_id,

        "request_sha256":
            request_sha,

        "request_sha_bound_in_final_manifests":
            request_sha
            in manifest_hashes,

        "q2_binding_count":
            q2_per_case[case_id],

        "client_request_ids":
            sorted(request_ids),

        "teacher_output_present":
            teacher_present,

        "rejection_present":
            rejection_present,

        "raw_response_present":
            raw_response.is_file(),

        "raw_response_sha256":
            raw_response_sha,

        "call_evidence_present":
            call_evidence.is_file(),

        "terminal_label":
            terminal_label(
                terminal_obj
            ),

        "files": [
            {
                "relative_path":
                    path.relative_to(
                        case_dir
                    ).as_posix(),
                "size":
                    path.stat().st_size,
                "sha256":
                    sha256_file(path),
            }
            for path in all_files
        ],
    })


summary = {
    "schema_id":
        "R132_PRIMARY117_IDENTITY_AUDIT_V1",

    "schema_version":
        1,

    "r132_package":
        str(PACKAGE),

    "r132_run":
        str(RUN),

    "r132_log":
        str(LOG),

    "r132_log_sha256":
        sha256_file(LOG),

    "expected_package_freeze_root":
        EXPECTED_PACKAGE_FREEZE,

    "package_freeze_marker_present":
        True,

    "primary_case_manifest_count":
        len(case_rows),

    "primary_request_manifest_count":
        len(request_rows),

    "run_case_directory_count":
        len(observed_dirs),

    "q2_binding_count":
        len(q2_rows),

    "q2_cases":
        len(q2_per_case),

    "q2_bindings_per_case":
        dict(
            sorted(
                Counter(
                    q2_per_case.values()
                ).items()
            )
        ),

    "teacher_output_count":
        teacher_output_count,

    "rejection_count":
        rejection_count,

    "raw_response_count":
        raw_response_count,

    "call_evidence_count":
        call_evidence_count,

    "transport_attempt_metadata_count":
        transport_attempt_count,

    "terminal_counts":
        dict(
            sorted(
                terminal_counts.items()
            )
        ),

    "blocker_count":
        len(blockers),

    "warning_count":
        len(warnings),

    "blockers":
        blockers,

    "warnings":
        warnings,

    "status":
        (
            "PASS"
            if not blockers
            else "FAIL"
        ),
}


rows_path = (
    OUT
    / "R132_PRIMARY117_CASE_IDENTITY_V1.jsonl"
)

summary_path = (
    OUT
    / "R132_PRIMARY117_IDENTITY_AUDIT_V1.json"
)


rows_path.write_text(
    "".join(
        json.dumps(
            row,
            sort_keys=True,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        + "\n"
        for row in rows_out
    ),
    encoding="utf-8",
)


summary_path.write_text(
    json.dumps(
        summary,
        sort_keys=True,
        ensure_ascii=False,
        indent=2,
    )
    + "\n",
    encoding="utf-8",
)


seal_path = (
    OUT
    / "R132_PRIMARY117_IDENTITY_AUDIT_V1.sha256"
)

script_path = (
    OUT
    / "audit_r132_primary117_identity_v1.py"
)


seal_path.write_text(
    "\n".join(
        [
            (
                f"{sha256_file(script_path)}  "
                f"{script_path}"
            ),
            (
                f"{sha256_file(rows_path)}  "
                f"{rows_path}"
            ),
            (
                f"{sha256_file(summary_path)}  "
                f"{summary_path}"
            ),
        ]
    )
    + "\n",
    encoding="utf-8",
)


print(
    "========== R132 PRIMARY117 "
    "IDENTITY AUDIT =========="
)

for key in (
    "primary_case_manifest_count",
    "primary_request_manifest_count",
    "run_case_directory_count",
    "q2_binding_count",
    "q2_cases",
    "q2_bindings_per_case",
    "teacher_output_count",
    "rejection_count",
    "raw_response_count",
    "call_evidence_count",
    "blocker_count",
    "warning_count",
    "status",
):
    print(
        f"{key} = {summary[key]}"
    )

print()
print(
    "terminal_counts =",
    summary["terminal_counts"],
)

print()
print(
    "R132_PRIMARY117_IDENTITY_AUDIT_V1_"
    + summary["status"]
)
