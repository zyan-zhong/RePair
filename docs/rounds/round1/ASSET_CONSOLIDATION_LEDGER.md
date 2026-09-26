# Round-1 Research Asset Consolidation Ledger

## Major-module status

`MODULE3_CLOSED_MAJOR_MODULE_COMPLETE`

## Purpose

Create a clear, durable and auditable repository map for the completed
first single-round policy-improvement validation without modifying its
scientific evidence.

## Source state

- source branch:
  `implementation/p4-select-execution-compat-v1`
- source commit:
  `04850406c7bc2077e85e59805685f4dfe1563e5e`
- module-closure policy commit:
  `1a92298d451a7517271ec0d82a5f3475a379a900`
- R132 identity-audit commit:
  `04850406c7bc2077e85e59805685f4dfe1563e5e`
- asset-consolidation design commit:
  `4d1d3553f762a9b171a9672da0b9f34951195ed2`
- Module-1 plan commit:
  `b89bd61463dc91863ebbb33cd9632b8ffa9af41d`
- Module-1 closure commit:
  `e0351af647ae4480d87f1ee0353d3c99137f0835`
- Module-2 original plan commit:
  `b99d54424a513fdf019056595f58d5d0b605d3d5`
- Module-2 execution-precondition amendment:
  `80c8fba57705a16cffdc44695a6b2b35468b65d4`
- Module-2 closure commit:
  `a51fb7a62f0581c9090f6982075000c22130bcaf`
- final historical-asset consolidation plan commit:
  `1936c1919e230908f47e1647636882e955766814`

## Preservation boundary

- no historical model output was rerun;
- no ALFWorld environment was rerun;
- no historical evidence was moved;
- no historical evidence was overwritten;
- no scientific result was changed;
- no existing SHA-256 identity was replaced;
- no Failure Memory record was generated.

## Small-module ledger

| Module | Purpose | Status | Closure evidence |
|---|---|---|---|
| Design freeze | Freeze structure, terminology, preservation rules and acceptance criteria | `COMPLETE` | `4d1d3553f762a9b171a9672da0b9f34951195ed2` |
| Navigation and Component Map | Create Round-1 overview and component registry | `COMPLETE` | `e0351af647ae4480d87f1ee0353d3c99137f0835` |
| Hierarchical Analysis Asset Map | Register Levels 1-6 and their internal components | `COMPLETE` | Closure commit identified through Git history; this ledger does not self-embed its own commit SHA. |
| Historical Asset Registry and Global Documentation Sync | Register paths and synchronize README, experiment ledger, code map and closure policy | `COMPLETE` | Closure commit identified through Git history; this ledger does not self-embed its own commit SHA. |

## Module 2 implementation plan

Plan:

`docs/superpowers/plans/2026-08-13-round1-hierarchical-analysis-asset-map-v1.md`

Original plan commit:

`b99d54424a513fdf019056595f58d5d0b605d3d5`

Execution-precondition amendment:

`80c8fba57705a16cffdc44695a6b2b35468b65d4`

The amendment changed only the Git-state execution precondition.

## Module 2 read-only evidence audit

Historical hierarchy assets were inventoried under both:

```text
/data/home/scwb204/run/pchsi
/data/run01/scwb204/pchsi
```

The mirror audit found:

```text
relative_candidate_count = 293
paired = 293
paired_files = 250
paired_directories = 43
file_sha_mismatch = 0
same_underlying_object = 293
```

For Module-2 de-duplication, `/data/run01/scwb204/pchsi` was used as the
representative inspection path.

This does not pre-empt Module 3's final canonical-retention/path
registration.

## Module 2 verified scientific structure

### Level 1

```text
85 matched groups
17 tasks

external-primary:
73 validated
12 unavailable
  6 provider-response incomplete
  6 ambiguous post-send / no-retry

50 complete-core
23 partial-validated

local shadow:
57 validated
decision_authority = false
```

### Level 2

```text
9 capability-scoped units
9 formal requests
30 mechanisms

7  ROBUST_TO_MISSINGNESS
22 MISSINGNESS_SENSITIVE
1  INSUFFICIENT_SUPPORT
```

### Level 3

```text
17 tasks
6 task families
30 frozen mechanisms
180 mechanism × family cells
6 formal requests
```

### Level 4

```text
30 mechanisms
9 capability components

435 total unordered mechanism pairs
39 within-component pairs excluded
396 cross-capability pairs
148 eligible / formally assessed pairs

29 candidate directional relations
```

Directional relations remain hypotheses, not causal edges.

### Level 5

```text
1 formal model request
provider response completed
semantic validation failed

disposition:
REJECT_LEVEL5_SEMANTIC_INVALID
```

No validated global synthesis was accepted.

### Level 6

A real independent-challenger role was designed and its provider/runtime
path was smoke-tested.

The located challenger execution used synthetic evidence with:

```text
contains_real_scientific_data = false
```

No final completed real-scientific-data Level-6 result is registered.

## Module 2 outputs

Created:

- `docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`

Updated:

- `docs/rounds/round1/README.md`
- `docs/rounds/round1/COMPONENT_REGISTRY.md`
- `docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md`

## Documentation Sync Check

| Document | Final consolidation state |
|---|---|
| Parent major-module ledger | `UPDATED` |
| Round-1 README | `UPDATED` |
| Component Registry | `UPDATED` |
| Asset Registry | `UPDATED` |
| Hierarchical Analysis Ledger | `CHECKED_NO_CHANGE_REQUIRED` |
| Experiment Ledger | `UPDATED` |
| Code Map | `UPDATED` |
| Root README | `UPDATED` |
| Module Closure Policy | `UPDATED` |

## Current scientific state to preserve

- first pi0-to-pi1 single-round training: completed;
- Harness-OFF result: `NO-GO`;
- hierarchical analysis Levels 1-4: completed;
- Level 5: `REJECTED`;
- Level 6: `INCOMPLETE`;
- canonical evidence and provenance closure: in progress;
- Failure Memory: `HOLD`.

## Current navigation entry points

Round-1 overview:

`docs/rounds/round1/README.md`

Round-1 component map:

`docs/rounds/round1/COMPONENT_REGISTRY.md`

Round-1 major-asset registry:

`docs/rounds/round1/ASSET_REGISTRY.md`

Hierarchical analysis:

`docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`

Current provenance audit:

`docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md`

## Module 3 implementation plan

Plan:

`docs/superpowers/plans/2026-08-13-round1-asset-registry-global-doc-sync-v1.md`

Plan commit:

`1936c1919e230908f47e1647636882e955766814`

## Final read-only major-asset audit

The verified inventory contains:

```text
31 registered major assets
11 required workflow stages covered

17 AUTHORITATIVE_RAW_OR_SEALED
12 AUTHORITATIVE_DETERMINISTIC_AUDIT
 2 HISTORICAL_REFERENCE
```

The inventory records:

```text
historical_evidence_modified = false
memory_record_generated      = false
```

Major fixed facts include:

```text
R132 primary cases       = 117
R132 teacher outputs     = 91
R132 rejections          = 26
R132 Q2 bindings         = 351

Q2 scientific accepted   = 91
training examples        = 84
formal training seeds    = 17 / 31 / 47

Harness-OFF result       = COMPLETE_NO_GO

raw provenance bundles   = 340 / 340 verified
raw provenance rejected  = 0
```

The three training-seed `formal_run_manifest.json` files are the primary
training-completion identities. Their frozen checkpoint aliases match
byte-for-byte.

The historical Harness-OFF formal evidence root has no standalone
compact root result. Its identity is registered through the original
2724-file tree seal, four condition-level mechanical manifests and the
downstream final-analysis bundle.

The six non-unique historical discovery slots were resolved by human
review for the new Asset Registry without rewriting the original
historical canonical-artifact audit.

## Final consolidation outputs

Created:

- `docs/rounds/round1/ASSET_REGISTRY.md`

Updated:

- `README.md`
- `docs/rounds/round1/README.md`
- `docs/rounds/round1/COMPONENT_REGISTRY.md`
- `docs/rounds/round1/ASSET_CONSOLIDATION_LEDGER.md`
- `docs/experiments/EXPERIMENT_LEDGER.md`
- `docs/code_map.md`
- `docs/protocol/MODULE_CLOSURE_POLICY.md`

Checked with no change required:

- `docs/rounds/round1/HIERARCHICAL_ANALYSIS.md`
- `docs/audits/ROUND1_CANONICAL_GAP_AUDIT.md`

## Major-module completion

The Round-1 historical research-asset consolidation is complete through
this closure work.

The consolidation did not:

- rerun a model;
- rerun ALFWorld;
- retrain a policy;
- move historical evidence;
- overwrite historical evidence;
- change a historical scientific result;
- generate a Failure Memory record.

The completed consolidation does not mean that all scientific
provenance work is finished.

Current project boundary remains:

```text
Canonical evidence/provenance closure = IN_PROGRESS
Failure Memory                        = HOLD
```

## Next action

Historical asset consolidation is finished after the closure commit is
pushed, local and remote HEAD are equal, and the worktree is clean.

The next research-facing gate is human review of the Failure Memory
design and sequence-memory schema before any Memory builder or Memory
materialization is created.

The verified 340-bundle raw provenance layer may be used as an input to
that design review, but no Memory record generation is authorized until
the design is explicitly approved.
