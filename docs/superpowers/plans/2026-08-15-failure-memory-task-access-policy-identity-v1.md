# Failure Memory V1 Task Access and Primary Policy Identity Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:test-driven-development to implement this plan task by
> task, and use superpowers:verification-before-completion before
> claiming this implementation unit is closed.

## Plan approval

Plan status:

`PLAN_APPROVED_FAILURE_MEMORY_TASK_ACCESS_POLICY_IDENTITY_V1`

Approval date:

`2026-08-15`

Approved final Plan basis:

`010e525a90d546999b65e31c3389e3d687727e73`

The user explicitly approved this Plan before implementation began.

Current authorization:

```text
SYNTHETIC_TDD_IMPLEMENTATION = AUTHORIZED
CODE_CANDIDATE_IMPLEMENTATION = AUTHORIZED
CODE_CANDIDATE_COMMIT_AND_PUSH = AUTHORIZED

REAL_DATASET_MATERIALIZATION = NOT_AUTHORIZED
REAL_POLICY_ARTIFACT_MATERIALIZATION = NOT_AUTHORIZED
MEMORY_RECORD_MATERIALIZATION = NOT_AUTHORIZED
MODEL_OR_ENVIRONMENT_EXECUTION = NOT_AUTHORIZED
SCIENTIFIC_EXECUTION = NOT_AUTHORIZED
```

This approval authorizes only the code-candidate phase defined in this
Plan.

It does not waive:

- test-first RED evidence;
- repository-preservation requirements;
- no-touch audits;
- code review before real materialization;
- separate read-only materialization approvals;
- final artifact/documentation closure requirements.

## Goal

Create the first authoritative Failure Memory V1 implementation
contracts:

1. the deterministic task-access manifest;
2. the primary/secondary frozen policy identity contract.

This unit creates no Failure Memory records and performs no model or
environment execution.

## Scientific purpose

The implementation must make it mechanically impossible to:

- move one task between Memory-source and retrieval-development roles;
- expose valid_seen during Memory development;
- call historically exposed valid_unseen fresh;
- use a test task as an active Memory source;
- select Train17 because of observed Memory performance;
- substitute Train31/47 for the primary worker after observing results;
- represent the Memory study as legacy E1/P1/SELECT execution.

## Approved design basis

Approved design integration:

`b3cb816e2e727600f79f1947a77c73ce87d4a97c`

Approved task-access candidate SHA-256:

`6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a`

Expected task populations:

```text
TRAIN_MEMORY_SOURCE                                      = 2367
TRAIN_RETRIEVAL_DEV                                      = 1186
VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED                  = 140
VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED = 134
TOTAL                                                    = 3827
```

Scientific prose must describe valid_seen as:

`PROJECT_HELD_OUT_ID_CONFIRMATION`

The compatibility access-class identifier may retain the approved
V2.1 name.

## Frozen policy source identities

The frozen Round-1 checkpoint set contains training seeds:

```text
17
31
47
```

Primary selection rule:

```text
MINIMUM_POLICY_TRAINING_SEED
FROM_FROZEN_ROUND1_CHECKPOINT_SET
```

Therefore:

```text
PRIMARY_FROZEN_MEMORY_WORKER = Train17
```

Registered source identities:

```text
Train17 formal_run_manifest SHA-256
ce44dd66ccf675da5d73fe9ac6b6273799df51e90b72bd92398ef521f1d103e6

Train17 adapter_artifact_manifest SHA-256
cfcff4c187429f5f9a82b55a47bb3ce4a9123e224a541fdfefa45ed09e9073a7

Train31 formal_run_manifest SHA-256
8b14bab7bf9d0396600c0d9bb5fc60340d0bd9336323dd9a3ad4047e76e8bd83

Train31 adapter_artifact_manifest SHA-256
ca06e6807803d82ed803e0ecdbc5b018bb1fdd85a8347f3b05a821cbb117170d

Train47 formal_run_manifest SHA-256
57db3c1dd720d758a21150389df840343cfec53a473b1b59b984303dd43eeb78

Train47 adapter_artifact_manifest SHA-256
b491aec5dc1f65a3b8f2083e605241473b171aa351c07ccf8d252bfaed206159

Frozen checkpoint-set root seal
6dd3ad3389869d6f929af24283589f2e22f4c687a800072af16bb6f23b5092f8
```

The implementation must verify actual source bytes/manifests rather than
accept these strings merely because they appear in configuration.

## Architecture

Create a new package:

```text
src/pchsi/memory/
```

Do not extend `DistillationAccessClass`,
`ConditionBoundEpisodeCellV1`, legacy run schedules or SELECT identity.

Reuse low-level deterministic primitives from the existing repository
where appropriate.

## Files to create

```text
src/pchsi/memory/__init__.py
src/pchsi/memory/task_access.py
src/pchsi/memory/policy_contract.py

tests/memory/test_task_access.py
tests/memory/test_task_access_materializer.py
tests/memory/test_policy_contract.py
tests/memory/test_policy_contract_materializer.py

scripts/memory/materialize_task_access_v1.py
scripts/memory/materialize_primary_policy_contract_v1.py

configs/memory/task_access_regeneration_v1.json
configs/memory/round1_policy_source_identity_v1.json

data/manifests/memory_task_access_manifest_v1.jsonl
data/manifests/memory_task_access_manifest_v1.sha256

data/manifests/memory_task_access_regeneration_receipt_v1.json
data/manifests/memory_task_access_regeneration_receipt_v1.sha256

data/manifests/failure_memory_primary_policy_contract_v1.json
data/manifests/failure_memory_primary_policy_contract_v1.sha256
```

Modify only:

```text
docs/memory/FAILURE_MEMORY_V1_LEDGER.md
```

during final unit closure.

## Files forbidden to modify

```text
src/pchsi/evaluation/runtime_core.py
src/pchsi/evaluation/budget.py
src/pchsi/evaluation/raw_policy_parser.py
src/pchsi/evaluation/raw_policy_prompt.py

src/pchsi/evaluation/run_schedule.py
src/pchsi/evaluation/condition_run_schedule.py
src/pchsi/evaluation/condition_execution_binding.py
src/pchsi/evaluation/select_execution_identity.py
src/pchsi/evaluation/policy_condition.py
src/pchsi/evaluation/episode_evaluator.py

configs/protocols/raw_with_menu_v1.json
data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl
```

No historical artifact may be rewritten.

## Global implementation constraints

- Python 3.12.
- Standard library only for this unit.
- No ALFWorld import.
- No vLLM import.
- No torch import.
- No provider/API client.
- No model call.
- No environment reset or step.
- No external-model call.
- No retriever.
- No Memory record materialization.
- No task outcome may participate in the train partition.
- No best-of-seed or best-of-checkpoint logic.
- Real dataset and checkpoint inspection is read-only.

## Final plan-review hardenings

### Repository-preservation contract

This implementation unit is additive by default.

Using approved integration commit:

`b3cb816e2e727600f79f1947a77c73ce87d4a97c`

as the preservation base, every already-tracked source, test, schema,
protocol, evaluator configuration and historical data file must remain
byte-identical unless it is explicitly listed below as a documentation
sync file.

Existing production/test/config files are not edited merely to make the
new Memory package convenient.

Allowed existing-file changes at final closure are limited to:

```text
docs/memory/FAILURE_MEMORY_V1_LEDGER.md
docs/code_map.md
```

`docs/code_map.md` changes only if the completed new package must be
added to the active code map.

Everything else in this implementation unit is created under the new
Memory-specific paths listed in this plan.

The deterministic scope audit must compare the final tree against the
preservation base and fail on any unexpected modification.

### Historical-exposure authority boundary

Dataset split and project exposure history are distinct facts.

The materializer may determine dataset identity from the local ALFWorld
filesystem.

It must not infer project exposure history merely from `train`,
`valid_seen` or `valid_unseen`.

Project access/exposure roles come from the approved Failure Memory V1
V2.1 task-access design contract.

The task-access regeneration configuration must bind:

```text
approved_design_commit
=
b3cb816e2e727600f79f1947a77c73ce87d4a97c

approved_v2_1_manifest_sha256
=
6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a
```

The materializer independently reconstructs dataset/gamefile identity
and applies only the frozen approved access policy.

It may not reclassify access roles from new outcomes, model behavior,
Memory behavior, human preference or ad-hoc historical search.

The final full manifest must byte-regenerate the approved V2.1 SHA.

### Evaluation-split identity-only inspection

For `valid_seen` and `valid_unseen`, this unit is permitted to inspect
only what is necessary to establish immutable task identity.

Permitted operations are:

- enumerate registered filesystem paths;
- inspect file type and symlink status;
- derive dataset-relative path identity;
- derive task-family identity from the registered path convention;
- hash exact gamefile bytes.

This unit must not:

- parse PDDL semantics;
- read or export trajectory-file contents;
- read or export task-goal text;
- construct observations;
- initialize ALFWorld;
- run a task;
- print held-out task contents.

Hashing bytes for identity does not grant semantic-use authority.

### Historical checkpoint-seal authority

The frozen checkpoint-set root seal is historical evidence.

The policy materializer must bind the exact canonical
`A01_CHECKPOINTS` root-seal record and independently verify the
registered Train17/31/47 formal-run and adapter-manifest bytes.

It must not invent a new tree-digest algorithm and then present the
result as the historical Round-1 root seal.

If the exact historical tree-seal implementation is available and
identity-bound, it may be run read-only as an additional verification.

Otherwise the final contract records:

```text
historical_identity_kind = ROOT_SEAL
historical_identity_value =
6dd3ad3389869d6f929af24283589f2e22f4c687a800072af16bb6f23b5092f8
```

together with independently verified member-file identities.

A missing/ambiguous authority record is a hard STOP.

### Code-review-before-materialization gate

Implementation has two audit checkpoints.

#### Checkpoint A — code candidate

After RED/GREEN, focused tests, full regression, compile and static
scope audit:

```text
code candidate commit
→ push
→ local/remote equality
→ complete human code review
```

No real ALFWorld dataset materialization and no real Round-1 checkpoint
materialization occur before:

`CODE_APPROVED_FAILURE_MEMORY_TASK_ACCESS_POLICY_IDENTITY_V1`

#### Checkpoint B — read-only materialization and closure

Only after code approval, separately authorize:

```text
READ_ONLY_TASK_ACCESS_MATERIALIZATION_APPROVED
READ_ONLY_POLICY_IDENTITY_MATERIALIZATION_APPROVED
```

Then run the two read-only materializers.

Audit the generated artifacts.

The final closure commit contains only authoritative generated
manifests/checksums and required documentation sync, unless a code
defect is found.

Any production-code change after Code Approval requires a new code
review before rerunning materialization.

The earlier code-candidate commit is not the module-closure commit.

The module closes only after the final artifact/documentation closure
commit is pushed and remotely verified.

## Final approval-review amendments

### Held-out identity disclosure policy

The implementation must enforce:

`HELDOUT_IDENTITY_DISCLOSURE_POLICY_V1`

Dataset identity reconstruction and development-facing identity are
different artifacts.

For `valid_seen` and `valid_unseen`, the materializer may internally use
the dataset-relative path and task-family information only when required
to reconstruct the approved V2.1 identity.

The following held-out semantic-bearing fields must not be exposed to
Memory/retrieval development logic before method freeze:

```text
raw dataset-relative path
task-family path component
object name
receptacle name
goal-like path component
raw task directory name
trajectory-file content
task-goal content
```

The materializer must not print, summarize or log those held-out fields.

The task-access process therefore produces two logically distinct
representations.

#### Protected regeneration representation

`MEMORY_TASK_ACCESS_REGENERATION_PROTECTED_V1`

This representation may contain the fields required to reconstruct the
approved V2.1 bytes, including semantic-bearing dataset-relative path
information.

Its sole purposes are:

```text
reconstruct approved V2.1 candidate
verify record count
verify exact SHA-256
derive sanitized access records
```

It is not a development-facing manifest.

It must:

- be written only to an explicitly supplied protected staging path;
- never be emitted to stdout or stderr;
- never be written under the repository tree;
- never be consumed by retriever, Memory builder or Policy code;
- never be committed to Git;
- use restrictive file permissions where supported.

The materializer prints only non-semantic counts and cryptographic
identities.

The approved protected representation must reproduce:

```text
record_count = 3827

sha256 =
6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a
```

#### Sanitized authoritative access manifest

`MEMORY_TASK_ACCESS_MANIFEST_V1`

This is the repository-facing and development-facing authority.

For every task it contains only opaque/access-governance fields required
by downstream Memory code.

It must not contain:

```text
dataset_relative_gamefile
task_type
raw task directory
object/receptacle names
task goal
trajectory path
```

The opaque identity is:

`task_gamefile_group_id`

The exact gamefile-byte identity remains:

`gamefile_sha256`

The sanitized manifest records split/access/exposure/governance state
without revealing semantic path content.

Its SHA-256 is a new authoritative artifact identity produced during
approved real materialization.

It is not required to equal the protected V2.1 SHA.

A separate regeneration receipt binds:

```text
approved_v2_1_sha256
protected_regeneration_sha256
protected_record_count
sanitized_manifest_sha256
sanitized_record_count
disclosure_policy_id
```

The receipt contains no held-out semantic-bearing path values.

### Filesystem identity policy

The implementation must enforce:

```text
GAMEFILE_IDENTITY_INPUT
=
REGULAR_FILE_ONLY

SYMLINK_GAMEFILE
=
FAIL_CLOSED

RESOLVED_PATH_OUTSIDE_DATASET_ROOT
=
FAIL_CLOSED
```

For each gamefile:

1. the leaf path must not be a symbolic link;
2. `lstat` identity must describe a regular file;
3. the path must resolve successfully with strict resolution;
4. the resolved gamefile must remain inside the strictly resolved
   dataset root;
5. only then may exact bytes be hashed.

A path that is lexically inside the dataset root but resolves outside it
is rejected.

A broken symbolic link is rejected.

The implementation must not silently follow a gamefile symlink and hash
its target.

Synthetic tests must treat `symlink gamefile` as a rejection case.

Synthetic tests must separately cover a path that resolves outside the
dataset root.

### Materializer TDD contract

Materializer code itself follows RED then GREEN.

Pure-core TDD does not substitute for materializer TDD.

Task-access materializer sequence:

```text
synthetic materializer RED tests
→ implement materializer
→ synthetic GREEN
```

Policy-identity materializer sequence:

```text
synthetic materializer RED tests
→ implement materializer
→ synthetic GREEN
```

No real dataset/checkpoint materialization is used to obtain GREEN.

The synthetic materializer tests are part of the code-candidate review
surface.


## Task-access record contracts

### Protected regeneration record

`MemoryTaskAccessRegenerationRecordV1`

exists only inside the protected regeneration/materialization boundary.

It preserves every field required to reproduce the approved V2.1
candidate, including:

```text
trial_id
task_type
split
dataset_relative_gamefile
gamefile_sha256
task_gamefile_group_id
historical_exposure_class
historically_exposed
access_class
benchmark_role
allowed_prefreeze_uses
writeback_policy
method_selection_allowed
formal_active_memory_source_allowed
final_evaluation_allowed_after_method_freeze
clean_confirmation
fresh_ood_claim_allowed
shadow_readback_during_formal_evaluation
```

It must not be exposed as a normal public Memory package input.

### Sanitized authoritative record

`MemoryTaskAccessRecordV1`

is the downstream development-facing record.

It contains:

```text
task_gamefile_group_id
gamefile_sha256
split
historical_exposure_class
historically_exposed
access_class
benchmark_role
allowed_prefreeze_uses
writeback_policy
method_selection_allowed
formal_active_memory_source_allowed
final_evaluation_allowed_after_method_freeze
clean_confirmation
fresh_ood_claim_allowed
shadow_readback_during_formal_evaluation
```

It must not contain:

```text
trial_id
task_type
dataset_relative_gamefile
raw gamefile path
raw task directory
trajectory path
task goal
object/receptacle labels
```

Use immutable records and tuple-valued collections.

The sanitized record is deterministically derived from the protected
regeneration record after the latter has passed the approved V2.1
identity check.

Downstream Memory development APIs accept only
`MemoryTaskAccessRecordV1`, never the protected regeneration record.

## Canonical task/group identity

The exact group identity is:

```text
relative_gamefile
=
UTF-8 dataset-relative path using "/" separators

gamefile_sha256
=
SHA-256 of exact gamefile bytes

task_gamefile_group_id
=
SHA256(
  "ALFWORLD_TASK_GAMEFILE_GROUP_V1\0"
  + relative_gamefile
  + "\0"
  + gamefile_sha256
)
```

No absolute dataset root enters the group ID.

## Train split rule

For every train task:

```text
split_score
=
SHA256(
  "MEMORY_TASK_ACCESS_V2_1\0"
  + task_gamefile_group_id
)
```

Within each task family:

1. sort by `(split_score, task_gamefile_group_id)`;
2. calculate retrieval-development size as `(n + 2) // 3`;
3. assign the first group block to `TRAIN_RETRIEVAL_DEV`;
4. assign the remaining block to `TRAIN_MEMORY_SOURCE`.

No success/failure, π0/π1 result, Memory result, Analyzer output or
human preference may influence the split.

## Fixed non-train roles

```text
valid_seen
→ VALID_SEEN_CLEAN_ID_CONFIRMATION_LOCKED
→ scientific role PROJECT_HELD_OUT_ID_CONFIRMATION
→ no pre-freeze use
→ no active-Memory source
→ no method selection

valid_unseen
→ VALID_UNSEEN_STANDARD_OOD_BENCHMARK_HISTORICALLY_EXPOSED
→ standard ALFWorld OOD benchmark
→ historically exposed
→ not fresh confirmatory
→ not an active-Memory source
→ not method-selection data
```

## Canonical serialization and disclosure separation

### Protected V2.1 regeneration serialization

The protected regeneration representation uses the approved V2.1
serialization:

- UTF-8;
- one JSON object per line;
- keys sorted;
- `ensure_ascii=False`;
- separators `(",", ":")`;
- records sorted by
  `(split, task_type, task_gamefile_group_id)`;
- exactly one LF after every record.

The protected representation must reproduce:

`6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a`

Any mismatch is a hard STOP.

This SHA verifies reconstruction of the approved V2.1 design input.

It is not the sanitized authoritative-manifest SHA.

### Sanitized authoritative serialization

`MEMORY_TASK_ACCESS_MANIFEST_V1` is serialized as:

- UTF-8;
- one JSON object per line;
- keys sorted;
- `ensure_ascii=False`;
- separators `(",", ":")`;
- records sorted by
  `(split, task_gamefile_group_id)`;
- exactly one LF after every record.

The sanitized manifest must contain exactly the same 3827 opaque task
identities and exactly the same four access-role populations as the
protected representation.

Its SHA-256 is generated during approved real materialization and is
registered as a new authoritative identity.

### Regeneration receipt

`MEMORY_TASK_ACCESS_REGENERATION_RECEIPT_V1`

cryptographically binds the approved protected reconstruction to the
sanitized authoritative manifest.

The receipt must not disclose held-out semantic path content.

A mismatch in protected SHA, record count, opaque identity set or role
population is a hard STOP.

## Primary policy contract

Create an immutable policy contract with:

```text
checkpoint_set_root_seal
selection_rule
primary_training_seed
primary_checkpoint_identity
secondary_training_seeds
secondary_checkpoint_identities
source_record_effect_policy
secondary_audit_condition
no_best_of_checkpoint
all_secondary_results_reported
```

Required semantics:

```text
primary_training_seed = 17

secondary_training_seeds = (31, 47)

source_record_effect_policy
=
ORIGINAL_SOURCE_CHECKPOINT

secondary_audit_condition
=
FM0_NO_PERSISTENT_MEMORY
vs
FM3_GATED_PRESCRIPTIVE_MEMORY
```

The contract must bind the actual formal-run and adapter-manifest
identities for all three checkpoints.

It must fail closed if:

- one source file is missing;
- one registered SHA does not match;
- the frozen checkpoint set cannot resolve all three seeds;
- any training seed is duplicated;
- Train17 is not the deterministic primary under the registered rule.

## TDD Task 1 — Task-access core RED

Create:

`tests/memory/test_task_access.py`

Before production implementation, write failing tests for:

- canonical gamefile-group identity;
- no absolute-root dependence;
- deterministic split-score identity;
- deterministic family-stratified split;
- retrieval-DEV size `(n + 2) // 3`;
- no group overlap;
- valid_seen role;
- valid_unseen role;
- writeback prohibition;
- active-Memory-source prohibition for evaluation tasks;
- exact canonical serialization;
- duplicate task/group rejection;
- changed gamefile bytes changing group identity;
- outcome fields not accepted by the partitioning API.

Run:

```bash
python -m pytest -q tests/memory/test_task_access.py
```

RED is expected.

## TDD Task 2 — Task-access core GREEN

Implement:

`src/pchsi/memory/task_access.py`

Minimum public API:

```text
MemoryTaskAccessClass
MemoryTaskAccessRecordV1

canonical_task_gamefile_group_id(...)
train_partition_score(...)
partition_train_task_groups(...)
canonical_task_access_jsonl(...)
sha256_task_access_manifest(...)
```

No filesystem scanning belongs in the pure core.

Make Task 1 GREEN.

## TDD Task 3A — Task-access materializer RED

Create:

`tests/memory/test_task_access_materializer.py`

Before creating the production materializer, write failing synthetic
filesystem tests for:

- missing split;
- missing gamefile;
- non-regular gamefile;
- symlink gamefile rejection;
- broken symlink rejection;
- lexically in-root path resolving outside dataset root;
- duplicate gamefile group;
- unsupported split;
- existing protected-output refusal;
- existing sanitized-output refusal;
- protected output under repository root rejection;
- deterministic repeated synthetic run;
- protected V2.1 serialization identity;
- sanitized manifest exclusion of semantic path/task-family fields;
- stdout/stderr not containing held-out semantic-bearing path values;
- materializer not reading trajectory-file contents;
- materializer not parsing PDDL/task-goal semantics.

Run:

```bash
python -m pytest -q \
  tests/memory/test_task_access_materializer.py
```

RED is expected because the materializer does not yet exist.

## TDD Task 3B — Task-access materializer GREEN

Create:

`scripts/memory/materialize_task_access_v1.py`

Responsibilities:

- accept a dataset root explicitly;
- accept a protected staging output explicitly;
- accept a sanitized staging output explicitly;
- enumerate only train, valid_seen and valid_unseen;
- establish leaf regular-file identity without following symlinks;
- resolve gamefile/root identity strictly and reject root escape;
- hash exact gamefile bytes;
- build protected regeneration records;
- reproduce the approved protected V2.1 identity;
- derive sanitized authoritative records;
- produce the four approved role populations;
- suppress held-out semantic-bearing path content from logs;
- never overwrite an existing output;
- never write the protected artifact beneath the repository tree;
- print only counts, policy IDs and cryptographic identities.

It must not:

- initialize ALFWorld;
- read trajectory contents;
- parse task-goal content;
- parse PDDL semantics;
- expose held-out raw paths to downstream Memory logic.

Make Task 3A GREEN.

The real 3827-task materialization is not run until read-only
materialization is separately approved after code review.

## TDD Task 4 — Policy-contract RED

Create:

`tests/memory/test_policy_contract.py`

Write failing tests for:

- registered seed set exactly `(17, 31, 47)`;
- primary selection independent of result metrics;
- minimum seed selects 17;
- secondary seeds are exactly `(31, 47)`;
- source-record effect policy uses original source checkpoint;
- FM0-vs-FM3 secondary audit identity;
- duplicate seed rejection;
- missing registered source identity rejection;
- wrong SHA rejection;
- checkpoint-set root-seal mismatch rejection;
- no best-of-checkpoint field or behavior.

## TDD Task 5 — Policy-contract GREEN

Implement:

`src/pchsi/memory/policy_contract.py`

The pure contract layer accepts already-read bytes/identity records.

It does not open a model, start a server or inspect evaluation results.

Make Task 4 GREEN.

## TDD Task 6A — Policy-identity materializer RED

Create:

`tests/memory/test_policy_contract_materializer.py`

Before creating the production materializer, write failing synthetic
artifact tests for:

- missing formal-run manifest;
- wrong formal-run SHA-256;
- missing adapter manifest;
- wrong adapter-manifest SHA-256;
- duplicate training seed;
- missing training seed;
- incomplete frozen seed set;
- wrong checkpoint reference;
- ambiguous `A01_CHECKPOINTS` authority record;
- missing `A01_CHECKPOINTS` authority record;
- wrong registered historical root seal;
- mismatched formal-run/adapter linkage;
- existing output refusal;
- deterministic repeated synthetic run;
- no result-metric input used for primary selection;
- no model/runtime startup.

Run:

```bash
python -m pytest -q \
  tests/memory/test_policy_contract_materializer.py
```

RED is expected because the materializer does not yet exist.

## TDD Task 6B — Policy-identity materializer GREEN

Create:

`scripts/memory/materialize_primary_policy_contract_v1.py`

Read only the registered Round-1 checkpoint artifacts.

Verify:

- all three formal-run manifests;
- all three adapter artifact manifests;
- exact canonical `A01_CHECKPOINTS` historical authority record;
- registered historical checkpoint-set root seal;
- exact training-seed identity;
- exact formal-run/adapter references;
- exact registered member-file SHA-256 identities;
- tokenizer/runtime identities when explicitly bound by authoritative
  source artifacts.

The script must not invent a replacement tree-seal algorithm.

If any required exact identity is not defensible from authoritative
source artifacts:

```text
STOP
DO_NOT_GUESS
DO_NOT_CREATE_FINAL_CONTRACT
```

It must not inspect FM results or select a checkpoint using performance.

Make Task 6A GREEN.

The real server materialization is not run until code review approves
this unit.

## TDD Task 7 — Canonical configuration

Create:

```text
configs/memory/task_access_regeneration_v1.json
configs/memory/round1_policy_source_identity_v1.json
```

These contain only frozen design constants and source identities.

They do not contain observed Memory outcomes.

Canonical JSON must be deterministic and reject NaN/Infinity.

## Verification

Focused:

```bash
python -m pytest -q \
  tests/memory/test_task_access.py \
  tests/memory/test_task_access_materializer.py \
  tests/memory/test_policy_contract.py \
  tests/memory/test_policy_contract_materializer.py
```

Then:

```bash
python -m compileall -q \
  src/pchsi/memory \
  scripts/memory \
  tests/memory
```

Then the applicable full regression:

```bash
python -m pytest -q
```

## Static scope audit

New Memory foundation code must not contain imports or calls matching:

```text
alfworld
vllm
torch
openai
anthropic
google.generativeai
env.step
environment.step
```

The audit must also prove byte-level no-diff for every file in the
historical no-touch list.

## Real read-only materialization gate

After implementation and full code review, but before unit closure,
separately obtain authorization to run:

1. task-access materialization against the local ALFWorld dataset;
2. policy-contract materialization against the frozen Round-1
   checkpoint artifacts.

These operations are read-only.

They may not execute a model or ALFWorld environment.

## Real materialization acceptance

The protected task-access regeneration output must produce exactly:

```text
2367 TRAIN_MEMORY_SOURCE
1186 TRAIN_RETRIEVAL_DEV
140 valid_seen project-held-out ID
134 valid_unseen historically exposed OOD
3827 total
```

and:

```text
protected_regeneration_sha256
=
6dcd1bc0a08e1233c5ce1bfb841388814feb083a7eb9db02291de0106f91802a
```

The sanitized authoritative manifest must:

- contain 3827 records;
- contain the same opaque task identity set;
- contain the same four access-role populations;
- contain no `dataset_relative_gamefile`;
- contain no `task_type`;
- contain no raw held-out task path;
- contain no task goal or trajectory path;
- produce a newly registered authoritative SHA-256.

The regeneration receipt must bind the protected and sanitized
identities without semantic held-out disclosure.

Policy output must bind Train17 as primary and Train31/47 as secondary
without using performance results.

## Documentation Sync Check

At closure:

```text
docs/memory/FAILURE_MEMORY_V1_LEDGER.md = UPDATED

docs/rounds/round1/ASSET_REGISTRY.md
= CHECKED_NO_CHANGE_REQUIRED
unless a new authoritative historical identity is discovered

docs/experiments/EXPERIMENT_LEDGER.md
= CHECKED_NO_CHANGE_REQUIRED

docs/code_map.md
= UPDATED if the new memory package is now part of active code

README.md
= CHECKED_NO_CHANGE_REQUIRED
```

## Commit and review scope

### Code-candidate commit

The code-candidate commit may contain only:

```text
src/pchsi/memory/
tests/memory/
scripts/memory/
configs/memory/
```

No real materialized manifest or closure-ledger update is included in
the code-candidate commit.

Suggested code-candidate commit message:

`Implement Failure Memory task access and policy identity code candidate`

### Final closure commit

After Code Approval and approved read-only materialization, the closure
commit may contain only:

```text
data/manifests/memory_task_access_manifest_v1.jsonl
data/manifests/memory_task_access_manifest_v1.sha256
data/manifests/memory_task_access_regeneration_receipt_v1.json
data/manifests/memory_task_access_regeneration_receipt_v1.sha256
data/manifests/failure_memory_primary_policy_contract_v1.json
data/manifests/failure_memory_primary_policy_contract_v1.sha256
docs/memory/FAILURE_MEMORY_V1_LEDGER.md
docs/code_map.md
```

`docs/code_map.md` is omitted when no change is required.

The closure commit must not contain new production-code changes.

Suggested closure commit message:

`Close Failure Memory task access and policy identity contracts`

Both commits must be single-purpose.

They must not contain unrelated refactoring.

## Closure

This implementation unit is CLOSED only after:

- approved implementation plan;
- RED evidence;
- GREEN focused tests;
- full applicable regression;
- compile pass;
- scope audit;
- historical no-touch audit;
- protected V2.1 task-access regeneration reproduced and hash-matched;
- sanitized authoritative task-access manifest materialized and
  disclosure-audited;
- task-access regeneration receipt materialized and verified;
- real policy identity contract materialized and verified;
- authoritative artifact hashes recorded;
- ledger updated;
- code-candidate commit pushed and remotely equal before materialization;
- explicit human Code Approval;
- explicit read-only materialization approval;
- final artifact/documentation closure commit;
- closure commit pushed;
- local HEAD equals remote HEAD;
- clean worktree.

Plan approval status:

`PLAN_APPROVED_FAILURE_MEMORY_TASK_ACCESS_POLICY_IDENTITY_V1`

The approved code-candidate phase may now begin.

The implementation must start with failing synthetic tests.

No production implementation may be written before the corresponding
test has been observed failing for the expected missing behavior.

Current authorization remains:

```text
SYNTHETIC_TDD_IMPLEMENTATION = AUTHORIZED
CODE_CANDIDATE_IMPLEMENTATION = AUTHORIZED
CODE_CANDIDATE_COMMIT_AND_PUSH = AUTHORIZED

REAL_DATASET_MATERIALIZATION = NOT_AUTHORIZED
REAL_POLICY_ARTIFACT_MATERIALIZATION = NOT_AUTHORIZED
MEMORY_RECORD_MATERIALIZATION = NOT_AUTHORIZED
MODEL_OR_ENVIRONMENT_EXECUTION = NOT_AUTHORIZED
SCIENTIFIC_EXECUTION = NOT_AUTHORIZED
```

The next approval gate after the code-candidate commit is:

`CODE_APPROVED_FAILURE_MEMORY_TASK_ACCESS_POLICY_IDENTITY_V1`
