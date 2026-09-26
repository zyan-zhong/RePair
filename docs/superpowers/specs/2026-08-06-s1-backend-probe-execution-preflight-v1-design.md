# S1 Backend Probe Execution Preflight V1 Design

## Purpose

Prepare an exact, dataset-bound, non-executing preflight bundle for a future
`S1_COLLECTOR_BACKEND_PROBE_V1` execution decision.

This design does not authorize or perform backend-probe execution. It only
observes and hashes the exact repository, candidate artifact, probe corpus,
runtime profile, and ALFWorld dataset identity that a later external decision
would have to bind.

## Starting point

| Field | Frozen value |
|---|---|
| Governance merge commit | `57a15945d0d790aa7f7033ffc86ac79273dd1d8d` |
| Candidate review head | `465503d14ee968d2acf23a314c66c65c52260583` |
| Candidate tree SHA-256 | `d61493ccbb433babf2fed2a7e749dc483fe2e63bc6d43422048440d84ad96885` |
| Candidate binary SHA-256 | `3f03b30b408e16466981bca1556983bdf709edf065a11d3b15bb626c3032e713` |
| Source manifest SHA-256 | `41f7461ac7ac7213ca13024a7c755a551f9ad0ab363ac46bc414040af3904eb7` |
| Runtime manifest SHA-256 | `4a524d95339afedbdc282a027cc99d388f4e99005f6ad109ff2bc61158effcfc` |
| Dataset version | `json_2.1.1` |
| Backend-probe execution | `NOT_APPROVED` |
| Read-only inventory execution | `NOT_APPROVED` |

## Scope

The implementation adds:

1. a strict JSON schema for a future external execution decision;
2. a pure Python preflight module;
3. a CLI that can describe or prepare a preflight bundle;
4. focused tests.

The implementation does not modify the closed execution gate, native
supervisor execution, namespace execution, or existing P1–P20 payloads.

## Dataset identity

The caller must provide explicit paths for:

- dataset root;
- legacy manifest;
- input contract.

The preflight must not infer or silently repair these paths.

The dataset root must:

- resolve to an existing directory;
- not be a symbolic link or resolve through a different lexical path;
- contain `train`, `valid_seen`, and `valid_unseen` directories;
- be bound by device, inode, mount ID, and filesystem type;
- be recorded with a logical root ID rather than exposing the absolute path
  in the decision template.

The legacy manifest and input contract must be regular non-symlink files and
are bound by exact SHA-256.

## Probe corpus binding

The preflight must verify exactly 22 probe manifests:

- `P01` through `P14`;
- `P15_CONTROL` and `P15_LIMITED`;
- `P16`, `P17`;
- `P18_BASELINE` and `P18_RESTRICTED`;
- `P19`, `P20`.

Every manifest must remain `execution_status=NOT_APPROVED`, permit no side
effects, and match the SHA-256 of its corresponding C payload.

The preflight records deterministic bundle hashes for:

- probe manifests;
- probe C sources;
- profile description;
- future decision schema.

## Repository and artifact binding

The preflight records:

- current clean source commit;
- governance merge commit;
- reviewed candidate identities;
- current launcher SHA-256;
- current execution-gate SHA-256;
- observed native binary SHA-256;
- profile description SHA-256;
- probe bundle hashes.

The observed native binary must still equal the reviewed candidate binary
SHA-256.

## External output boundary

The output root must:

- be absolute;
- be outside the repository;
- not already exist;
- be created with owner-only permissions.

The preflight writes exactly:

- `backend_probe_execution_preflight.json`;
- `backend_probe_execution_preflight.json.sha256`;
- `backend_probe_execution_decision_template.json`.

The decision template must contain:

```text
decision=NOT_GRANTED
BACKEND_PROBE_EXECUTION=NOT_APPROVED
READ_ONLY_INVENTORY_EXECUTION=NOT_APPROVED
```

Repository files, commit messages, environment variables, and this template
do not constitute execution approval.

## CLI behavior

`--describe` returns a deterministic non-executing description.

`--prepare` creates the preflight bundle.

`--execute` always returns exit code `77` with
`PCHSI_EXECUTION_NOT_APPROVED`.

## Approval sequence after this package

1. review and merge this preflight implementation;
2. run preflight against the explicit dataset root;
3. audit the generated identity and bundle;
4. separately design and review native execution enablement;
5. create an external exact decision record;
6. separately grant `BACKEND_PROBE_EXECUTION_APPROVED`;
7. execute P1–P20 once;
8. audit evidence before any inventory approval.

## Security rationale

Landlock and seccomp are kernel security interfaces whose actual behavior
depends on the target kernel and runtime environment. Static code approval
therefore cannot substitute for an explicit target-host preflight and later
adversarial execution.

## Merge policy

Use **Create a merge commit**. Do not squash, rebase, force-push, or directly
push the branch into `main`.
