# Formal Analyzer V2 — Branch Consolidation Policy V1

Status: **REMOTE CONSOLIDATION RECORD**

## 1. Why we do not merge every historical branch

The repository currently contains many plan/design/implementation/hardening branches created as scientific checkpoints. For Analyzer V2, the important structural fact is:

`main` (`b6b03d02d8a802f56d0d88fcf9a9de1d16ef5727`)

is an ancestor of:

`hardening/formal-act3-state-k1-materialization-v1` (`17201a462d24985e195a5bb225e388bd9cb9089e`)

with a **pure fast-forward chain of 51 commits and no behind commits**.

Therefore, separately merging every Analyzer milestone branch would add redundant merge commits and obscure the actual scientific lineage. The correct consolidation strategy is to preserve milestone names as history while promoting one canonical descendant.

## 2. Canonical branch

Canonical archive branch:

`archive/formal-analyzer-pi1-reference-v1`

Base:

`17201a462d24985e195a5bb225e388bd9cb9089e`

Purpose:
- final correct Analyzer/Runtime implementation state;
- canonical archive documents;
- π1 Formal reference experiment manifests;
- maintenance invariants;
- artifact/path index;
- branch/release policy.

The actual Formal Main G/X execution used code head:

`0529efa4b4c896f3855a4634c7daa3a3559e3a89`

This distinction is intentionally preserved. The later `17201a...` commit adds explicit state-level K1 materialization infrastructure and is not retroactively claimed as the execution head.

## 3. Mainline milestone branches already subsumed by the canonical descendant

These branches are historical checkpoints, not independent merge targets:

### Design / implementation foundation
- `design/hierarchical-analyzer-v2-v1`
- `plan/outcome-aware-hierarchical-analyzer-v2-v1`
- `plan/outcome-aware-hierarchical-analyzer-v2-v2`
- `implementation/outcome-aware-hierarchical-analyzer-v2-v1`
- `implementation/outcome-aware-hierarchical-analyzer-v2-v2`

Confirmed examples:
- `design/hierarchical-analyzer-v2-v1` is an ancestor of the later Formal ACT3 line;
- `implementation/outcome-aware-hierarchical-analyzer-v2-v2` is an ancestor of `17201a...`;
- `hardening/outcome-aware-hierarchical-analyzer-v2-statistics-v1` is an ancestor of `17201a...`.

### Analyzer scientific hardening milestones
- `hardening/outcome-aware-hierarchical-analyzer-v2-batch1-v1`
- `hardening/outcome-aware-hierarchical-analyzer-v2-tasks6-16-v1`
- `hardening/outcome-aware-hierarchical-analyzer-v2-statistics-v1`

### Runtime / researcher activation milestones
- `design/runtime-researcher-activation-v3-v1`
- `implementation/runtime-researcher-activation-v3-v1`
- `hardening/v10-runtime-analyzer-activation-r2-v1`

### Exact contract hardening milestones
- `hardening/a0-a1-semantic-contract-v1`
- `hardening/act1-evidence-reference-contract-v1`
- `hardening/local-selector-wire-enum-v1`
- `hardening/registry-hard-stop-v1`
- `hardening/act3-g-proposal-serialization-v4`
- `hardening/act3-registration-group-io-v1`

### Formal experiment milestones
- `hardening/formal-analyzer-dag-v2-grouped`
  - commit `5ee40528ed12c64fdb8923f55bf15e44f30ff8f5`
  - grouped Formal Analyzer DAG V2.
- `hardening/formal-analyzer-fresh-pi1-collection-v1`
  - commit `eef643fca368fe68be1967cf5f934df39a9b810e`
  - fresh π1 Formal Analyzer failure collection.
- `hardening/formal-act3-canonical-pack-v1`
  - commit `0529efa4b4c896f3855a4634c7daa3a3559e3a89`
  - actual Formal Main execution code head.
- `hardening/formal-act3-state-k1-materialization-v1`
  - commit `17201a462d24985e195a5bb225e388bd9cb9089e`
  - canonical post-experiment Analyzer head.

## 4. Branches to keep vs prune

### Keep permanently as semantic milestones
Recommended to keep these branch names even after main is fast-forwarded because they are useful scientific anchors:
- `design/hierarchical-analyzer-v2-v1`
- `implementation/outcome-aware-hierarchical-analyzer-v2-v2`
- `hardening/formal-analyzer-dag-v2-grouped`
- `hardening/formal-analyzer-fresh-pi1-collection-v1`
- `hardening/formal-act3-canonical-pack-v1`
- `hardening/formal-act3-state-k1-materialization-v1`
- `archive/formal-analyzer-pi1-reference-v1`

### Keep temporarily until release/tag verification, then optional prune
These are useful during audit but are redundant once the release/tag and canonical archive are verified:
- `plan/outcome-aware-hierarchical-analyzer-v2-v1`
- `plan/outcome-aware-hierarchical-analyzer-v2-v2`
- `implementation/outcome-aware-hierarchical-analyzer-v2-v1`
- `hardening/outcome-aware-hierarchical-analyzer-v2-batch1-v1`
- `hardening/outcome-aware-hierarchical-analyzer-v2-tasks6-16-v1`
- `hardening/outcome-aware-hierarchical-analyzer-v2-statistics-v1`
- `design/runtime-researcher-activation-v3-v1`
- `implementation/runtime-researcher-activation-v3-v1`
- `hardening/v10-runtime-analyzer-activation-r2-v1`
- `hardening/a0-a1-semantic-contract-v1`
- `hardening/act1-evidence-reference-contract-v1`
- `hardening/local-selector-wire-enum-v1`
- `hardening/registry-hard-stop-v1`
- `hardening/act3-g-proposal-serialization-v4`
- `hardening/act3-registration-group-io-v1`

Deletion is optional. If deleted, commit history remains reachable from the canonical main/archive/tag, but branch names disappear. Do not delete before the canonical archive and release tag are independently verified.

### Do not touch as part of Analyzer cleanup
Branches belonging to other subsystems remain independent and should not be folded into Analyzer cleanup merely because they share repository history, including:
- E1 evaluator/runtime-core branches;
- Failure Memory design/implementation/science branches;
- P1/P4 governance/access/distillation branches;
- reference-loop evidence foundation branches;
- backend probe/governance branches.

Those may be consolidated in their own subsystem releases.

## 5. Main branch policy

Because `main -> 17201a...` is a pure fast-forward chain, the preferred integration is:

1. build and verify `archive/formal-analyzer-pi1-reference-v1`;
2. ensure archive docs and experiment manifests are correct;
3. fast-forward `main` once to the archive branch head;
4. do **not** create merge commits from every historical Analyzer branch;
5. after main/archive equality is confirmed, create a release-specific tag such as `formal-analyzer-pi1-reference-v1.0`.

The main fast-forward should happen only after archive documentation is complete.

## 6. Release policy

Recommended permanent release identity:

`formal-analyzer-pi1-reference-v1.0`

Release notes should bind:
- source commit/archive branch head;
- actual Formal Main execution code head `0529efa...`;
- canonical post-experiment Analyzer code head `17201a...`;
- Formal DAG V2 SHA;
- G and X Batch IDs;
- Round Evidence SHA;
- experiment manifest path;
- artifact archive checksum if a raw artifact bundle is attached later.

If repository release immutability is enabled, publish only after all assets are attached. An immutable release is preferred for the scientific checkpoint.

## 7. Future development

Do not continue active development on the archive branch.

Future Analyzer changes should branch from the consolidated `main` using explicit new versions, for example:
- `design/hierarchical-analyzer-v3-*`
- `implementation/hierarchical-analyzer-v3-*`
- `hardening/formal-analyzer-v3-*`

The V2 archive should remain unchanged except for corrections that explicitly state they are documentary errata and do not rewrite the scientific result.