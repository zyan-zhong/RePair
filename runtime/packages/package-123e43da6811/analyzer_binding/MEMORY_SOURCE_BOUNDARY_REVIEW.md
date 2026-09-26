# Memory source boundary review

Review date: 2026-09-24. This is a source-contract review, not a new scientific authority or execution gate. The source constructor is complete within its stated scope. Current TRAIN_UPDATE-to-native-Memory record production is not implemented here.

## Verified source and completed read route

Current scientific source is registered commit `bba400738a7a53d0402552ecc3576f736ca0eec8`, Git tree `953f5c900b085af97e41fc84d4e75583446cac38`. The exact local capture is `../NATIVE_BBA_FULL_SOURCE_RECEIPT_V2.json`, archive SHA256 `47585cbb74cecec46b2306df259ff5b13d03c545813df6a0474f78b4c6b99a02`. The earlier CRLF-transformed archive is not accepted. All source locations below are relative to `../native_bba_full/`.

`source_binding.py` resolves registered Q/U/X/H4.4 packages, checks their finite manifests, verifies current repo configuration and producer bytes against the registered Git objects, and loads the current request's immutable snapshot and token contract. It can materialize the full native Researcher view automatically. The initial partition map is reused from the tracked assignment in `scripts/memory/run_role_view_smoke_v1.py:157`; the same native pattern exists in `scripts/memory/run_memory_live_cell_executor_v1.py:377`. The initial snapshot/token must match `configs/memory/package_b_failure_memory_dependency_v1.json`.

The original initial partition scope is `ACCESS_DIAGNOSTIC_ONLY`, suitable for `ROUND_RESEARCH_PLANNING`. It is not full training-source provenance. Loaded records remain unchanged. Changed snapshots require the current Memory operation's real native partition bindings or exact registered views; bootstrap authority is not transplanted into later rounds.

## Actual current data labels

The registered rollout package's `V123133_MEMORY_AWARE_GENERIC_ROLLOUT_LIVE_SOURCE_CAPSULE.zip` contains:

- `SHARED_TRAIN_UPDATE_DIRECT_DATA_AUTHORITY_V1.json`: pool `TRAIN_UPDATE`, 2,843 registered rows; benchmark, TRAIN_SELECT, TRAIN_AUDIT, valid_seen and valid_unseen access are false.
- `TRAIN_UPDATE.jsonl`: raw SHA256 `07221cbfa374e5ac100443079aee5940ca6227ffc42600c49c75d1d69de074cb`, 2,843 rows. Rows are `ALFWORLD_CLEAN_TRAIN_TASK_RECORD_V1`, `split=train`, `train_pool=TRAIN_UPDATE`, with task ID, gamefile path/SHA256, task type and train-universe identity.

Package location is `../../v16/reference/PCHSI_CAMPAIGN_AUTHORITY_DRIVEN_FRESH_MEMORY_AWARE_TRAIN_UPDATE_ROLLOUT_V1_23_2/`. These are inspected registered bytes, not a claim of a newly executed Formal rollout. Current source rows must retain their real labels; `TRAIN_UPDATE` must not be rewritten as the old `TRAIN_MEMORY_SOURCE` task-access class.

## Existing native write interfaces and exact mismatch

| Native source | Contract relevant to this handoff |
| --- | --- |
| `src/pchsi/memory/sequence_failure_experience.py:155` | `SequenceSourceTaskAccessBindingV1` binds the fixed historical Memory-source role. Its manifest check at line 249 requires literal SHA `260766366d72a9af7b0b4809d30a45bb56f42134dad66b29a4b61ff7ed4793ea`; its access check at lines 299-319 requires `TRAIN_MEMORY_SOURCE`. |
| `src/pchsi/memory/sequence_failure_experience.py:2022` | `validate_sequence_source_evidence_v1` verifies full immutable episode bytes, registration identity, task access, trace/policy-call consistency and contiguous windows before slicing. These factual checks are reusable. |
| `src/pchsi/memory/sequence_failure_experience.py:2268` | `build_sequence_failure_experience_v1` reconstructs actual factual failure experience; it does not manufacture semantic boundary conditions. |
| `scripts/memory/finalize_approved_source_failures_v1.py:456` | The existing assembly writer consumes explicit activation/release/nonapplicability/mechanism/recovery decisions. Lines 441, 553, 592 and 613 declare human origin/creator roles. Calling it unchanged for Strong output would misstate origin. |
| `src/pchsi/memory/applicability.py:153` | `ApplicabilityBoundarySetV1` requires nonempty activation and at least release or termination (lines 205-208). Empty boundary sets cannot represent an incomplete assembly in this interface. |
| `src/pchsi/analyzer/local_results.py:318` | Accepted EXACT_ACTION requires `termination_condition` and `trainable_rule` to be null; SHORT_OPTION has termination but no activation boundary; TRAINABLE_RULE supplies a rule, not a registered full boundary set. |
| `src/pchsi/memory/candidate_materialization.py:129` | `materialize_candidate_item_v1` consumes real canonical experience and assembly refs, then invokes native procedural builder, source-integrity audit, descriptive governance, retrieval-key and FM1/FM2 producers. Valid source/assembly objects are prerequisites. |
| `src/pchsi/memory/round_maintenance.py:265` | `MemoryShadowEventV1` requires a real record binding, Analyzer finding, candidate repair, native partition, verifier effect and evidence refs; it is not a substitute record builder. |

The finite search of this complete current source and the registered Q/U/X/H4.4 sources found no current TRAIN_UPDATE sequence/assembly writer. This is not a claim that no future extension is possible. It identifies the missing adapter in the captured implementation.

## Existing ledger authority

Line references are to `../../../outputs/PCHSI_CANONICAL_STATUS_20260924_FORMAL_MAX10_V1_6_BINDING_CANDIDATE_FULL.md`:

- V139-2, lines 76846-76853: the missing piece is current execution/adapter/receipt binding; a second Memory framework is not authorized.
- V139-3, lines 76855-76880: native `round_maintenance.py`, `close_memory_round_v1` and `next_round_state_v1` remain authoritative. Benefit requires complete/clean causal evidence; Harm quarantines; Neutral is descriptive; Uncertain stages unresolved. Same-round exposure of newly written historical Memory and heldout writeback remain forbidden.
- V141-8, lines 78854-78871: the historical executor consumes an actual OPEN state and actual current events; synthetic Memory lineage and synthetic shadow events are explicitly forbidden. It does not supply a missing source/assembly producer.
- V12303-7, lines 140389-140403: Memory runtime identity remains reused; TRAIN_UPDATE authority is derived from actual manifest content. This does not relabel current rows into the old protected task-access manifest.

## Minimal legal adapter proposal, not implemented

1. Add an explicit current-round source-access type, retaining `split=train` and `pool=TRAIN_UPDATE`. Bind current request, round, parent policy and execution attempt; current manifest SHA and exact row index/raw-row SHA; task/gamefile identity; and sealed attempt-bundle SHA. Validate membership against the current request and sealed capsule. Reject heldout/select/audit substitution. Keep V1's historical validation unchanged.
2. Extend native sequence parsing/validation to accept this distinct source-access type while reusing whole-episode validation, deterministic window reconstruction and native source-integrity checks. This is a typed provenance transport change, not permission to mint old protected-manifest membership.
3. A procedural assembly needs actual accepted semantic boundary clauses and actual Strong origin artifact refs. Existing EXACT_ACTION/SHORT_OPTION output cannot be mechanically asserted to provide all those clauses. Do not infer conditions from source-state/menu text, insert human labels, or use empty boundaries. Until a legitimate producer supplies those fields, retain exact factual/Analyzer/verifier artifacts as unresolved evidence without claiming a new governed record or policy-visible FM2.
4. Once legitimate experience and assembly refs exist, reuse `materialize_candidate_item_v1` and its real tokenizer/source-governance results. Retain native ineligibility/failure codes; do not turn an ineligible record into Benefit promotion. Then use unchanged native close/next-state rules.

No new Strong output fields, source schemas, scientific gates, record builders or promotion rules were implemented during this constructor task. This proposal requires integration work before dynamic new-record writeback can be claimed.

## Verification and remaining limits

Command:

```text
python -B -m pytest work/v17/analyzer_binding/tests/test_source_binding.py work/v16/analyzer_adapter/tests/test_exact_bindings.py -q -p no:cacheprovider
```

Result: **25 passed in 6.59s** (16 constructor tests plus 9 unchanged V1.6 exact-binding tests). Tests include actual registered package bytes, relocation/tamper negatives, current/future-round identity checks, real full-current Git blob checks and real native nonempty snapshot producer/loader/view integration. The bootstrap integration substitutes only its test snapshot authority. Windows fixture replacements cover the native POSIX fsync/text-mode write incompatibility; scientific validators remain native.

The actual server initial snapshot is not mounted locally, so this is not evidence that its real server Researcher view has been materialized. This task did not run a provider, environment, trainer, scientific round or Max10 campaign. It did not produce a current-round new governed record, retrieval key, FM1/FM2, or accepted shadow event from Analyzer output. Existing V1.6 files and immutable ZIPs were not modified. No provider/server/network/Git mutation was performed by this constructor task.
