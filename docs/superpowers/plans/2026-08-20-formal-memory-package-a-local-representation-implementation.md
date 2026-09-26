# Formal Package A — Local Failure-Experience Representation Probe Implementation Plan

Parent pre-ABC seal: `ae374ddccde815219624b93222afb5c08087735f`

Branch: `science/memory-package-a-representation-v1`

## Scientific authority

Formal Package A implements only the frozen local representation/mechanism probe:

- exactly three registered source decision states;
- exactly four representation arms per source: M0 / M1 / M2 / M3;
- M0 is the common empty Memory slot;
- M1 is matched raw FM1;
- M2 is the deterministic single cue;
- M3 is structured descriptive FM2, not prescriptive FM3;
- M1/M2/M3 bind the same exact Memory lineage/version;
- continuation seed is 17 for the three frozen TRAIN17 source states;
- exact same replayed source state and Runtime Core across arms;
- effect vocabulary Benefit / Harm / Neutral / Uncertain;
- effect scope `SOURCE_STATE_LOCAL_PAIRED`;
- no general representation-superiority claim is authorized.

Package A1 expanded representation remains OPTIONAL_CONDITIONAL and does not block downstream packages.

## Implementation units

1. Add a hold-open source-state replay session that delegates all state/identity
   verification to the already-audited `replay_source_decision_state_v1()` and
   suppresses only its unconditional final close until continuation ends.

2. Add a strict real-input binder:
   registered replay source ↔ governed record factual provenance ↔ B-DIRECT
   representation template. Any non-unique or mismatched identity fails closed.
   The binder materializes exactly three A0 source bindings plus the existing
   12-cell scientific manifest. It performs no model/environment execution.

3. Add Formal-A pure execution contracts:
   exact cell identity, full prompt-token census, no truncation/context overflow,
   exact pre-result infrastructure retry identity, and resolved cell-result
   semantics.

4. Add an explicit-approval-gated one-cell continuation runner and deterministic
   12-cell local paired aggregator. The code-preparation delivery does not invoke
   either scientific execution or a scheduler.

## Verification and closure

Use TDD RED→GREEN for each implementation unit. Seal each unit as one purpose /
one commit, push immediately, verify local=remote and clean worktree. At the final
fixed head, rebuild the repository's closed native test binary and rerun focused,
all-Memory, and full-repository tests.

Final state remains:

```
SCIENTIFIC_EXECUTION_AUTHORIZED=false
MEMORY_ON_SCIENTIFIC_EXECUTION=false
EFFECT_AUTHORITY=UNTESTED
NEXT_GATE=HUMAN_FIXED_HEAD_SOURCE_REVIEW
```
