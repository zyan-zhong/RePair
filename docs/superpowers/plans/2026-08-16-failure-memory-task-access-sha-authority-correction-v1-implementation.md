# Failure Memory Task-Access SHA Authority Correction V1 — Implementation Plan

## 1. Approval and purpose

Plan approval:

`PLAN_APPROVED_FAILURE_MEMORY_TASK_ACCESS_SHA_AUTHORITY_CORRECTION_V1`

Design approval:

`DESIGN_APPROVED_FAILURE_MEMORY_TASK_ACCESS_SHA_AUTHORITY_CORRECTION_V1`

Correction base:

`1a0feeef8085ba124fa79e72c38fea90b812d9f9`

Primary purpose:

> Correct the provenance/authority binding between the preserved historical
> task-access design candidate digest and the exact-contract protected
> regeneration digest, without changing task membership, partition semantics,
> role semantics, populations, or the pure task-access algorithm.

This plan authorizes only the narrow RED→GREEN implementation work described
below. It does not authorize real task-access materialization, model execution,
environment execution, Memory-record construction, scientific execution, or
repository artifact closure.

---

## 2. Frozen scientific semantics

The following are immutable throughout all four Tasks:

```text
access_policy_id
=
MEMORY_TASK_ACCESS_V2_1

task_gamefile_group_domain
=
ALFWORLD_TASK_GAMEFILE_GROUP_V1

task membership
=
UNCHANGED

partition semantics
=
UNCHANGED

role semantics
=
UNCHANGED

population
=
UNCHANGED

TRAIN_MEMORY_SOURCE
=
2367

TRAIN_RETRIEVAL_DEV
=
1186

VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED
=
140

VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
=
134
```

The pure algorithm file is an immutable no-touch control:

```text
src/pchsi/memory/task_access.py
=
BYTE-IDENTICAL TO CORRECTION BASE
```

No Task may modify:

- canonical task/gamefile identity;
- train partition score;
- task-family stratification;
- `(n + 2) // 3`;
- role-field semantics;
- canonical protected-record ordering;
- canonical sanitized-record ordering;
- canonical JSON encoding.

---

## 3. Frozen digest roles

Historical candidate identity:

```text
historical_design_candidate_sha256
=
6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a
```

Its permanent role is:

```text
PRESERVED_HISTORICAL_DESIGN_CANDIDATE
NOT_EXECUTION_AUTHORITY
```

Proposed exact-contract protected-regeneration authority:

```text
approved_exact_contract_protected_sha256
=
260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea
```

Observed sanitized identity, recorded but not promoted by this plan:

```text
observed_sanitized_sha256
=
e7dc8ddd1795b4ed51fdf62735a49620c8bc03470b86de220180d45a336c5228
```

The generic schema must keep historical provenance and execution authority as
distinct semantic roles. It must not impose a universal rule that their digest
values are unequal.

This correction V1 instance must assert:

```text
6dcd... != 260766...
```

---

## 4. Evidence already established

Real dataset identity:

```text
dataset_version
=
json_2.1.1

dataset_source_integrity_fingerprint_v1
=
d657703df1033a9797e7e9a18b3eb989e49dd3391a468d1a65f6edff3e609e24

record_count
=
3827
```

Three independent exact-contract reproductions agree:

```text
CURRENT_PRODUCTION_IN_MEMORY
=
260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea

HISTORICAL_PURE_CORE
=
260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea

STANDALONE_CANONICAL_SERIALIZER
=
260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea
```

Required equality findings:

```text
historical_current_group_ids_equal
=
true

production_vs_historical_bytes_equal
=
true

production_vs_standalone_bytes_equal
=
true
```

Preserved failed V2 staging:

```text
/data/run01/scwb204/sdar_repro/badcase/
pchsi_materialization_staging/
failure_memory_foundation_v1_1a0feee
```

Known incident-artifact identities:

```text
materialization_stop_v2.json
sha256 =
de08da19fe8ac43e7ed91ad47e6411cb151665f1ee41008db187a983a9b58866

source_integrity_pre_v2.json
sha256 =
b03649bcf252d07bf8c4095aaf396a7ed70e9f8c1d032646dbe38cb44780ab92

task_access_materializer.stderr.log
sha256 =
d6c1b9dc4d4362eba1c82e243c12490644439816d22997a6429ed8e07a76f6c6

task_access_materializer.stdout.log
sha256 =
e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
```

The failed staging is immutable evidence. It must never be removed, overwritten,
or reused.

---

## 5. Commit and execution discipline

Each Task follows:

```text
RED
→ verify expected failure
→ GREEN
→ focused tests
→ full regression
→ compileall
→ static/scope audit
→ independent single-purpose commit
→ push
→ local/remote equality
```

No production code may be written before the corresponding RED is observed.

Planned focused commit subjects:

1. `Record task-access SHA authority correction evidence`
2. `Separate historical and exact task-access authorities`
3. `Enforce task-access SHA authority no-fallback`
4. `Build task-access SHA correction retry wrapper candidate`

No Task may run the real 3827-task materialization.

---

# Task 1 — Correction design synchronization and machine-auditable evidence

## Goal

Synchronize the approved main Failure Memory design and ledger, and implement
a machine-auditable evidence contract whose conclusions are computed from
bound reproduction artifacts rather than copied from declared constants.

## Files

Expected production/documentation scope:

```text
docs/superpowers/specs/2026-08-14-failure-memory-v1-design.md
docs/memory/FAILURE_MEMORY_V1_LEDGER.md
configs/memory/schemas/
  task_access_sha_authority_correction_evidence_v1.json
src/pchsi/memory/
  task_access_sha_authority_correction.py
scripts/memory/
  build_task_access_sha_authority_correction_evidence_v1.py
tests/memory/
  test_task_access_sha_authority_correction.py
```

If the repository maintains an exact schema inventory, update only the
corresponding closed inventory test/registry required for the new schema.

Forbidden Task 1 changes:

```text
src/pchsi/memory/task_access.py
configs/memory/task_access_regeneration_v1.json
scripts/memory/materialize_task_access_v1.py
real external staging
```

## Design and ledger correction

The design section governing task-access regeneration and the Failure Memory
ledger must preserve both identities:

```text
historical_design_candidate_sha256
=
6dcd...

approved_exact_contract_protected_sha256
=
260766...
```

They must state that:

- `6dcd...` is historical provenance only;
- `260766...` is the proposed exact-contract execution authority;
- task membership, partition, role semantics, and populations are unchanged;
- the correction-design commit supersedes the old digest authority binding;
- `b3cb816...` remains design ancestry;
- production execution remains unapproved.

## Evidence schema

Schema ID:

`TASK_ACCESS_SHA_AUTHORITY_CORRECTION_EVIDENCE_V1`

Required top-level fields include:

```text
schema
correction_base_commit
correction_design_commit
access_policy_id
historical_design_candidate_sha256
proposed_exact_contract_protected_sha256
dataset_source_fingerprint
record_count
role_counts
reproductions
production_vs_historical_bytes_equal
production_vs_standalone_bytes_equal
all_three_sha256_equal
incident_evidence
conclusion
```

Each reproduction entry must include:

```text
reproduction_id
implementation_identity
implementation_sha256
source_fingerprint
record_count
role_counts
canonical_output_artifact_sha256
canonical_output_byte_count
observed_protected_sha256
```

The builder must:

- read canonical output bytes;
- calculate byte counts and SHA-256 itself;
- calculate implementation/artifact SHA-256 itself;
- reject caller-supplied claims that disagree with observed bytes;
- compare complete production/historical/standalone bytes;
- calculate equality booleans;
- reject missing or duplicate reproduction IDs;
- require exactly the three registered reproduction roles;
- bind the incident-artifact bytes and their SHA-256 values;
- emit canonical UTF-8 JSON with sorted keys, compact separators, and one LF;
- write no output before all validation succeeds;
- use exclusive/no-clobber publication.

It must not:

- generate a task split;
- enumerate the real ALFWorld dataset in unit tests;
- accept `260766...` solely because it appears in a configuration value;
- claim that semantic task membership changed;
- copy protected task paths into the repository.

## RED tests

At minimum:

```text
test_correction_evidence_requires_three_registered_reproductions

test_correction_evidence_computes_sha_from_canonical_bytes

test_correction_evidence_rejects_declared_sha_that_disagrees_with_bytes

test_correction_evidence_requires_production_historical_byte_equality

test_correction_evidence_requires_production_standalone_byte_equality

test_correction_evidence_binds_role_counts_and_record_count

test_correction_evidence_binds_incident_artifact_hashes

test_correction_evidence_preserves_historical_candidate_role

test_correction_v1_instance_requires_6dcd_not_equal_260766

test_correction_evidence_no_clobber
```

Expected RED:

- module/schema/builder missing;
- no evidence object capable of calculating the required conclusions.

RED must not be caused by syntax/import errors.

## GREEN

Implement only enough to satisfy the frozen evidence contract and design/ledger
synchronization.

## Verification

Focused:

```bash
python -m pytest -q \
  tests/memory/test_task_access_sha_authority_correction.py
```

Then:

```bash
python -m pytest -q
python -m compileall -q src tests scripts/memory
git diff --check
```

No-touch:

```bash
git diff --exit-code \
  CORRECTION_BASE \
  -- src/pchsi/memory/task_access.py
```

Commit subject:

`Record task-access SHA authority correction evidence`

Task 1 completion does not authorize Task 2 execution until Task 1 is committed,
pushed, and local/remote equality is confirmed.

---

# Task 2 — Versioned authority schema and execution binding

## Goal

Introduce a versioned, unambiguous authority configuration and receipt. Bind
the new execution authority to the Task 1 correction-design commit while
preserving the old V1 config as historical provenance only.

## Files

Expected scope:

```text
configs/memory/task_access_regeneration_v2.json
scripts/memory/materialize_task_access_v1.py
tests/memory/test_task_access_materializer.py
```

Task 2 may update narrowly related schema-inventory tests if required.

Must remain byte-identical:

```text
src/pchsi/memory/task_access.py
```

The old file:

```text
configs/memory/task_access_regeneration_v1.json
```

must remain preserved as a historical artifact unless an explicit review
requires a documentation-only annotation. It must not be silently rewritten
into V2.

## V2 authority contract

Schema ID:

`TASK_ACCESS_REGENERATION_CONFIG_V2`

Required fields:

```text
schema
access_policy_id
disclosure_policy_id
original_failure_memory_design_commit
sha_authority_correction_design_commit
historical_design_candidate_sha256
approved_exact_contract_protected_sha256
expected_populations
```

Bindings:

```text
original_failure_memory_design_commit
=
b3cb816e2e727600f79f1947a77c73ce87d4a97c

sha_authority_correction_design_commit
=
Task 1 commit SHA

historical_design_candidate_sha256
=
6dcd...

approved_exact_contract_protected_sha256
=
260766...
```

The production materializer must compare generated protected bytes only
against:

```text
approved_exact_contract_protected_sha256
```

It may carry `historical_design_candidate_sha256` into provenance and receipt
fields, but may never use it to admit execution output.

## V2 receipt

Schema ID:

`MEMORY_TASK_ACCESS_REGENERATION_RECEIPT_V2`

Required correction-aware fields include:

```text
original_failure_memory_design_commit
sha_authority_correction_design_commit
historical_design_candidate_sha256
approved_exact_contract_protected_sha256
protected_regeneration_sha256
protected_record_count
sanitized_manifest_sha256
sanitized_record_count
role_counts
access_policy_id
disclosure_policy_id
```

The receipt must make clear that:

```text
historical candidate
!=
execution gate
```

## V1 rejection

The production execution loader must reject:

```text
TASK_ACCESS_REGENERATION_CONFIG_V1
```

It must not:

- reinterpret the old field;
- auto-upgrade it;
- fallback to it;
- accept a V1 file based on matching populations;
- accept V1 because the old file is present in the repository.

## RED tests

At minimum:

```text
test_execution_loader_rejects_v1_authority_config

test_v2_authority_requires_correction_design_commit

test_v2_authority_preserves_historical_candidate

test_v2_authority_uses_exact_contract_sha_as_only_execution_gate

test_v2_authority_rejects_missing_exact_contract_sha

test_v2_authority_rejects_wrong_exact_contract_sha

test_v2_receipt_separates_historical_and_execution_digests

test_v2_config_binds_task1_correction_design_commit

test_task_access_core_file_remains_byte_identical
```

Expected RED:

- V2 schema unsupported;
- V1 still accepted;
- authority roles not separated.

## GREEN

Implement the V2 authority/receipt model and configuration only. Do not modify
task identity, partition, role assignment, or canonical record serialization.

## Verification

Focused:

```bash
python -m pytest -q \
  tests/memory/test_task_access_materializer.py
```

Then full regression, compileall, diff check, and no-touch audit.

Commit subject:

`Separate historical and exact task-access authorities`

---

# Task 3 — Behavioral no-fallback enforcement

## Goal

Prove by behavior that the historical candidate can remain in provenance but
cannot become an execution gate through any fallback path.

Behavioral tests are primary authority. Static scans are supplemental.

## Files

Expected scope:

```text
tests/memory/test_task_access_materializer.py
tests/memory/test_task_access_sha_authority_correction.py
scripts/memory/audit_task_access_sha_authority_no_fallback_v1.py
```

Production changes are allowed only if a behavioral RED exposes a remaining
fallback or ambiguity. Any such production change must remain within:

```text
scripts/memory/materialize_task_access_v1.py
```

No other production file is permitted.

## Required behaviors

```text
6dcd present as provenance
→ PASS

6dcd used in exact-authority field
→ FAIL CLOSED

260766 absent
→ FAIL CLOSED

260766 mismatch
→ FAIL CLOSED

260766 mismatch then fallback to 6dcd
→ IMPOSSIBLE / FAIL CLOSED

V1 config
→ FAIL CLOSED
```

The generic evidence/config schema requires role separation. It does not impose
universal digest inequality.

This correction V1 instance requires:

```text
historical_design_candidate_sha256
!=
approved_exact_contract_protected_sha256
```

## RED tests

At minimum:

```text
test_historical_candidate_is_accepted_only_as_provenance

test_historical_candidate_in_execution_field_is_rejected

test_missing_exact_contract_authority_is_rejected

test_exact_contract_mismatch_does_not_fallback_to_historical

test_v1_config_cannot_reenable_historical_execution_gate

test_correction_v1_instance_requires_distinct_digest_values
```

The tests must invoke real loader/materializer behavior using synthetic data.
They must not only grep source strings.

## Supplemental static audit

The audit checks the materializer AST/data flow and fails if the historical
candidate field participates in:

- the protected-regeneration admission comparison;
- fallback selection;
- `or`/defaulting into the execution digest;
- compatibility conversion from V1;
- receipt substitution for the generated protected digest.

Static audit success does not replace behavioral tests.

## Verification

Run focused behavioral tests, static audit, full regression, compileall, diff
check, and no-touch audit.

Commit subject:

`Enforce task-access SHA authority no-fallback`

---

# Task 4 — Retry wrapper candidate with new staging identity

## Goal

Implement and synthetic-test a correction-aware retry wrapper candidate. It
must preserve both earlier failed staging roots and reserve a new staging
identity bound to the correction code HEAD.

Task 4 does not authorize or execute the real retry.

## Preserved staging

Must remain unchanged:

```text
failure_memory_foundation_v1_71ce8a4
failure_memory_foundation_v1_1a0feee
```

The second contains the preserved SHA-authority incident evidence.

## New staging identity

The wrapper must derive or freeze a new identity containing the correction code
HEAD prefix, for example:

```text
failure_memory_foundation_v1_sha_authority_correction_v1_<head-prefix>
```

The final exact name is frozen in the implementation after the Task 3 head
exists.

The wrapper must reject:

- either old staging name;
- any preexisting new staging root;
- symlink staging roots;
- a dirty worktree;
- a branch/HEAD mismatch;
- missing correction evidence;
- correction evidence whose three reproductions are not byte-equal;
- a V1 authority config;
- an authority config not bound to the Task 1 correction-design commit;
- an authority config whose exact execution SHA is not `260766...`.

## Candidate-only boundary

Before code approval, Task 4 may:

- implement wrapper code;
- run temporary-directory synthetic tests;
- verify CLI execution remains closed or dry-run-only;
- generate no authoritative external staging.

Before a separate execution approval, Task 4 may not:

- create the real new retry staging;
- read/write the formal task-access outputs;
- run the real 3827-task materialization;
- run policy-identity materialization;
- copy artifacts into Git;
- create a closure commit.

## RED tests

At minimum:

```text
test_retry_wrapper_rejects_old_v1_failure_staging_identity

test_retry_wrapper_rejects_old_v2_failure_staging_identity

test_retry_wrapper_requires_new_head_bound_staging_identity

test_retry_wrapper_requires_correction_evidence

test_retry_wrapper_rejects_v1_authority_config

test_retry_wrapper_requires_clean_fixed_head

test_retry_wrapper_candidate_does_not_execute_real_materialization
```

## GREEN

Implement only the candidate wrapper and synthetic verification surface.

## Verification

Focused Task 4 tests, full regression, compileall, static no-execution audit,
exact scope audit, and no-touch audit.

Commit subject:

`Build task-access SHA correction retry wrapper candidate`

---

## 6. Cumulative final audit

After Task 4, the implementation branch must prove:

```text
exactly four focused commits
all four planned commit subjects present
full pytest passes
compileall passes
git diff --check passes
local branch == remote branch
worktree clean
src/pchsi/memory/task_access.py byte-identical to correction base
task membership unchanged
partition semantics unchanged
role semantics unchanged
populations unchanged
historical candidate preserved
historical candidate never used as execution gate
exact-contract protected authority = 260766...
V1 authority config rejected for execution
failed V2 staging preserved
no real retry staging created
no real materialization executed
no repo artifact closure performed
```

Expected approval state after implementation:

```text
CODE_APPROVED_FAILURE_MEMORY_TASK_ACCESS_SHA_AUTHORITY_CORRECTION_V1
=
PENDING INDEPENDENT FIXED-HEAD REVIEW

READ_ONLY_TASK_ACCESS_MATERIALIZATION_APPROVED
=
NO
```

A later independent review and explicit execution approval are mandatory before
the real retry.
