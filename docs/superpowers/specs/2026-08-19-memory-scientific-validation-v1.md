# Memory Scientific Validation V1 — Targeted Scientific Hardening

Status: `DESIGN_APPROVED_MEMORY_SCIENTIFIC_VALIDATION_V1`

Human design authority: explicit user approval on 2026-08-19 after review of the
three-package Memory scientific-validation design and targeted hardening.

Engineering base authority:

`112ba5d3ccc0a3f3c3a9fdd143ec4c69fa525229`

This document governs scientific execution after the sealed Failure Memory
B-DIRECT engineering package. It does not reinterpret engineering readiness as
scientific outcome authority.

## 1. Project-level claim hierarchy

The project-level evidence chain remains:

```text
failure evidence
→ Researcher / Hierarchical Analyzer
→ historical Failure Experience support
→ candidate repair
→ same-state environment verification
→ Benefit / Harm / Neutral / Uncertain
→ verified training evidence
→ candidate πk+1
→ Memory OFF + Harness OFF evaluation
→ promote / rollback
```

Failure Memory is an historical-experience and researcher-support layer. It is
not the final project endpoint.

## 2. Three-package architecture

```text
Package A: representation / local mechanism
Package B: retrieval + applicability safety
Package C: Analyzer + history → verified repair
Later package: policy internalization and OFF/OFF acceptance
```

The three-package architecture is frozen. Null, adverse, or weak outcomes do not
authorize silent redesign of downstream packages.

## 3. Package A0 — local source-state representation probe

A0 is exactly:

```text
3 frozen source states × M0/M1/M2/M3 = 12 scientific cells
```

The core representation meanings are:

- `M0`: the same Memory-aware interface with an empty Memory payload.
- `M1`: the complete matched raw episodic failure window.
- `M2`: the deterministic single-cue view from the same governed record.
- `M3`: structured descriptive FM2 from the same governed record.

`M3` in A0 is not a prescriptive verified-FM3 arm.

For each source state, all four arms bind the same policy, reconstructed source
state, observation, complete menu, executed history, budget, decoding contract,
snapshot, record lineage/version, and one pre-frozen continuation seed. The
only deliberate scientific difference is the Policy-visible Memory payload.

### A0 authority

A0 is a `SOURCE_STATE_LOCAL_PAIRED` mechanism/representation probe.

Allowed artifact effect labels remain:

```text
Benefit
Harm
Neutral
Uncertain
```

Every such label must carry:

```text
effect_scope = SOURCE_STATE_LOCAL_PAIRED
```

Terminal outcome and mechanism behavior are separate fields. A terminally
neutral pair does not imply that the old failure mechanism was repeated, and a
mechanism change does not imply terminal benefit.

A0 cannot authorize:

- general structured-representation superiority;
- cross-task transfer;
- overall Memory success;
- retriever efficacy;
- Analyzer efficacy;
- parametric policy improvement;
- project-level self-improvement.

## 4. Package A1 — conditional expanded representation evidence

A1 is not an execution prerequisite for B, C, or policy internalization.

Status:

`OPTIONAL_CONDITIONAL`

A1 becomes required only if the paper makes a general representation claim such
as “structured procedural experience is superior to raw/cue exposure.” If A1 is
run, its panel must be outcome-blind and expanded, and it must include a
pre-registered deterministic token/compression control. No post-hoc raw excerpt
selection is allowed.

## 5. Package B — retrieval and applicability safety

The frozen `TRAIN_RETRIEVAL_DEV` population cannot be used as one undivided pool
for both tuning and reporting.

Task/gamefile groups must be mutually exclusive across:

```text
RETRIEVER_CALIBRATION_DEV
RETRIEVER_SELECTION_VALIDATION
REGISTERED_SAFETY_STRESS
```

The selected retriever is frozen after selection validation. `valid_seen` and
`valid_unseen` are excluded from retriever tuning and selection.

Applicability/non-applicability labels are independent diagnostic/safety
authority. Retriever or Analyzer self-labels cannot be used as gold to evaluate
the same system. Applicability gold does not create causal Benefit/Harm truth.

## 6. Package C — repair discovery and environment verification

C compares:

```text
C0: single reflection
C1: Hierarchical Analyzer
C2: Hierarchical Analyzer + historical Failure Experience
```

The C query panel must be fresh at the exact task/gamefile-instance grouping
level. It must exclude:

- A0 source task/gamefile groups;
- token-budget calibration task/gamefile groups;
- active historical Memory source task/gamefile groups;
- Package-B calibration/selection/safety-stress task/gamefile groups.

This isolation forbids exact-instance answer leakage while still permitting
transfer across broad task families or failure mechanisms.

C2 must use the Package-B-selected frozen retriever, frozen threshold/config,
frozen active snapshot, and frozen applicability gate. Human hand-selection of
a convenient historical Memory for a C query is forbidden.

## 7. Infrastructure failure versus scientific uncertainty

A pre-result infrastructure failure is not a scientific outcome. Examples
include transport failure before a scientific response, vLLM startup failure,
environment-constructor failure, and artifact failure before scientific
execution.

Such a failure requires:

```text
retry the exact same frozen cell
```

The retry must preserve seed, prompt, source state, retriever, threshold,
snapshot, decoding configuration, branch definition, and scientific inputs.
It does not enter the Benefit/Harm/Neutral/Uncertain denominator.

Scientific execution followed by unresolved identity/evidence may become
`Uncertain` or a protocol hard stop according to the registered audit rule. A
source-state mismatch is never repaired by silently changing the state.

## 8. Package-C efficiency estimands

Package C must report, in addition to terminal effect labels:

- `Verified Benefit Yield = Benefit candidates / candidate repairs tested`;
- `Repair Discovery Rate = failures with >=1 verified Benefit / failures`;
- `Candidates-to-First-Benefit`;
- `Environment-Verification Cost per verified Benefit`;
- `Harm Exposure Rate = Harm / tested candidate repairs`;
- abstention/no-repair rate;
- Analyzer model-call and token cost where available.

A method that finds more Benefits by proposing far more candidates is not
implicitly more efficient.

## 9. Outcome-guided redesign prohibition

The following are forbidden:

```text
poor/null A → redesign B/C
poor/null B → redesign C
Memory-ON outcome → silently alter representation/retriever/Analyzer prompt
```

A versioned amendment may be opened only for a registered protocol defect,
contamination, critical safety failure, or invalid scientific identity. The
amendment must not erase the original outcome or original protocol.

## 10. Policy-internalization pre-freeze

Actual policy training is deferred from the current Memory scientific package,
but the policy-internalization scientific protocol must be frozen before large
Package-C outcome unblinding.

At minimum it must freeze:

- training-eligibility rule;
- training arms;
- model initialization;
- data-deduplication rule;
- hyperparameter-selection authority;
- Memory-OFF + Harness-OFF evaluation panel;
- primary metric;
- promotion/rollback rule.

Final project-level improvement authority remains Memory OFF + Harness OFF.

## 11. Reporting and visual authority

`PAPER_VISUAL_EVIDENCE_FREEZE_V1` remains a writing/layout plan only. It does
not authorize omission or down-weighting of adverse, null, contradictory, or
harmful scientific results.

## 12. Current execution gate

At the engineering base head, B-DIRECT is ready but scientific execution is not
authorized. This design approval authorizes implementation of the scientific
contracts and A0 execution machinery. It does not itself authorize a Policy or
ALFWorld Memory-ON scientific run.

The next gate after implementation is fixed-head human code review.
