# SPLIT_AND_ACCESS_V1 — Trusted Manifest Fast Lane

## Decision

For E1, the critical path no longer depends on executing the optional hostile-
collector sandbox or generating a separate automated inventory.

The experiment will use the already committed, reviewed strict-134 task
manifest directly through a trusted evaluator process.

Formal access mode:

`TRUSTED_MANIFEST_DIRECT_V1`

## Why this scope reduction is valid

The backend probe protects a future collector process that may be buggy or
hostile. The E1 experiment does not require that collector when the task list
is already frozen, content-addressed, and checked against the exact ALFWorld
dataset root.

This decision does not claim that the S1 sandbox is effective. It removes S1
execution, P1–P20, and inventory collection from the E1 critical path.

## Frozen task scope

- Dataset version: `json_2.1.1`
- Split: `valid_unseen`
- Unique tasks: `134`
- Repository manifest:
  `data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl`
- Repository manifest SHA-256:
  `6e480bb663a6f17207aa2c7a6e1b504adad8448f6e8a2615c5e62fea0b64c0f4`
- Legacy strict-134 manifest SHA-256:
  `cc08cf1f437548dd6b81411e567cfc9b743488ee49ef1dff8173860fce1d9d56`
- Dataset input-contract SHA-256:
  `7be24bc2d1bb5a9a0328445f69efb23bd84358ae23a52eddaa4fcb9e4ae76979`
- Dataset-bound preflight manifest SHA-256:
  `f21ec29cc44b029c6d0412c7565596790eabe28424a2fc0c2e8da27a4723af6c`
- Preflight decision ID:
  `cdb7a6de952f648eb83e37947f8d00090f5fb0fb44df29d22699a7fa276911a0`

The machine-readable split record contains no absolute path values. The
referenced repository task manifest currently contains server-local absolute
`gamefile` paths bound to this target host. Moving the experiment to another
host or dataset root requires regenerating the task manifest and performing a
new `SPLIT_AND_ACCESS_V1` freeze. Device, inode, mount ID, and filesystem type
remain local preflight evidence.

## Evaluator access contract

The trusted evaluator must:

- consume the repository manifest in original order;
- execute exactly the listed 134 game files;
- reject missing, duplicate, reordered, substituted, or extra records;
- verify each listed game file before environment creation;
- use `valid_unseen` only for the frozen E1 condition;
- expose the full current `admissible_commands` sequence without sorting,
  filtering, deduplication, repair, or truncation;
- perform no dataset writes;
- record the manifest and protocol hashes in every trajectory.

The evaluator must not infer the split from a directory scan.

## Deferred optional hardening

The following remain implemented or prepared but are not E1 prerequisites:

- S1 backend-probe execution enablement;
- P1–P20 target-host execution;
- hostile-collector containment evidence;
- automated read-only inventory collection.

They may be resumed later without changing the frozen E1 task manifest.

## Current execution boundary

- `BACKEND_PROBE_EXECUTION=NOT_APPROVED`
- `READ_ONLY_INVENTORY_EXECUTION=NOT_APPROVED`
- `ALFWORLD_EVALUATOR=NOT_IMPLEMENTED`
- `E1_DEV_EXECUTION=NOT_APPROVED`
- `E1_CONFIRMATORY_EXECUTION=NOT_APPROVED`

Freezing split/access does not authorize ALFWorld or model execution.
