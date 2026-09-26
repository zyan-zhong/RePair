# STRONG_PRIMARY_AUTONOMOUS_CAMPAIGN_DRIVER_V1_11_0

## Purpose

V1.11.0 is a bounded recovery/integration supervisor for the currently live Strong-primary Round-1 tail. It reuses the fixed-head repository and the already-running V1.10 hydrated-tail runtime; it does not create a second Analyzer, Planner, verifier, Memory algorithm, optimizer, or promotion rule.

Its immediate job is to remove known V1.10 integration hazards while preserving exactly-once/no-blind-resend semantics:

1. inherit the live V1.10 process bindings (`package root`, `upstream`, `closure`, `prepared`, `repo`) from `/proc/<pid>/cmdline` and freeze them once;
2. never compete while V1.10 owns the tail-writer lock;
3. after V1.10 releases the lock, validate the existing verifier receipts with the exact V1.10 verifier gate;
4. if V1.10 already made exactly one accepted Strong Planner POST call, adopt it without Provider resend;
5. if no logical POST call exists at all, allow exactly one first POST execution through V1.10's existing POST worker; partial/ambiguous call state fails closed;
6. derive TRAIN vs NO_TRAIN only from the independent verifier's stable Benefit count;
7. invoke the current fixed-head `freeze_no_training_update(...)` with its actual full signature on zero-Benefit rounds;
8. refuse action-only training fallback;
9. keep the max-10 / patience-3 governance contract unchanged;
10. write a machine-readable release gate instead of fabricating unproven training, Memory-close, acceptance, promotion, or next-round authority.

## Important scientific truth

This package **does not claim that the complete max-10 campaign is already released**. `V111_AUTONOMY_RELEASE_GATE_V1.json` remains authoritative. Until every remaining live binding is proven, it deliberately records:

```text
full_max10_autonomous_campaign_released=false
routine_human_scientific_decision_required=false
action_only_training_fallback_allowed=false
```

The remaining gaps are execution bindings, not permission for a Human to make scientific choices. They must be closed by deterministic/native authorities before max-10 release.

## Known V1.10 defects corrected here

### A. Planner POST schema adapter mismatch

The fixed-head `API_RESEARCHER_POST_PRIMARY_V1` uses `researcher_training_recommendation` and `researcher_promotion_recommendation`. V1.10's downstream validator expected different fields. V1.11 therefore treats independent verifier receipts as the effect/TRAIN-route authority and treats Planner POST as interpretation/lesson output only.

### B. NO_TRAIN fixed-head signature mismatch

V1.10's adapter called an older narrow form of `freeze_no_training_update`. V1.11 binds all current fixed-head required fields, including POST/verifier SHAs, full B/H/N/U counts, and `scientifically_valid_round`.

### C. dual-view training identity compatibility

Stage6AN intentionally emits two views of the same real source state: exact-I1 action execution + training-only strategy auxiliary view. V1.11 includes a narrow adapter that keeps the real `source_state_sha256` shared while using unique `source_example_sha256` identities and requiring exactly one action/strategy pair per source state. It delegates optimizer mechanics to the existing Generic Training Stage adapter rather than implementing another trainer.

This compatibility code alone does not authorize optimizer execution.

## One launch while V1.10 PID is live

From the extracted V1.11 directory:

```bash
./VERIFY_PACKAGE.sh
./RUN_DETACHED.sh --v110-pid 3785949
```

The launcher creates a fresh versioned state root automatically and prints it. No upstream/prepared/repo/closure path needs to be manually retyped.

V1.11 snapshots the V1.10 runtime immediately. After that snapshot is written, later disappearance of `/proc/3785949` does not erase the inherited authority.

Do **not** kill PID 3785949 before launching V1.11. V1.11 observes V1.10 while its writer lock is active and does not compete with it.

## Status

Use the printed state root:

```bash
./STATUS.sh --state-root <STATE_ROOT_PRINTED_BY_RUN_DETACHED>
```

Normal current phases include:

```text
RUNTIME_INHERITED
WAIT_V110_WRITER
WAIT_VERIFIER
PLANNER_POST_ADOPTED
CURRENT_ROUND_ROUTE_BOUND
NO_TRAINING_UPDATE_APPLIED
AUTONOMY_RELEASE_BLOCKED
```

`AUTONOMY_RELEASE_BLOCKED` is a truthful integration release gate, not a request for a Human scientific decision.

## Frozen repository authority

```text
repo=/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-strong-primary-takeover-prep-v1
HEAD=61c9b8798f0b0d1cfb046b5ca60d90b9d8d0da6a
```

V1.11 does not modify that active worktree.

## V1.10 frozen runtime defaults being inherited

The authoritative V1.10 launcher itself freezes:

```text
UPSTREAM=/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/strong_primary_r1_f0f1_autorun_v1/20260913T014418Z
PREPARED=/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/strong_primary_r1_dynamic_pre_v2_native_live_v1/20260912T161044Z
REPO=/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-strong-primary-takeover-prep-v1
CLOSURE=/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/strong_primary_r1_verifier_to_autonomous_round_closure_v1/20260914T080000Z
```

V1.11 nevertheless inherits the values from the live process rather than trusting a hand-copied shell command.

## Stop governance

No change:

```text
MAX_SCIENTIFICALLY_VALID_ROUNDS=10
NO_PROMOTION_PATIENCE=3
PROTOCOL_INFRA_INVALID does not consume scientific-round budget
PROMOTED resets the no-promotion streak
```

## Claim boundary

Keep false until fresh current-round evidence proves all required stages:

```text
END_TO_END_POLICY_UPDATE_PROVEN=false
CURRENT_ROUND_END_TO_END_UNATTENDED_COMPLETION_PROVEN=false
WHOLE_ROUND_SINGLE_DRIVER_PROVEN=false
ACTION_ONLY_POLICY_GRADIENT_PROBLEM_CLAIMED_FIXED=false
FULL_SERVER_GITHUB_ALIGNMENT_PROVEN=false
LATEST_RECOVERY_FIXES_DURABLY_PUSHED=false
```
