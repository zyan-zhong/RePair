# ANALYZER_METRIC_REGISTRY_V1

## 1. Purpose

Freeze a claim-aligned metric system that is complete enough to survive review
without turning every diagnostic into a primary endpoint.

Every reported metric must specify:

```text
name
definition
numerator
denominator
independent unit
aggregation level
missing/infrastructure treatment
confidence interval or exact uncertainty method
claim status = PRIMARY | SECONDARY | DIAGNOSTIC
```

## 2. Literature-grounded metric design

The adjacent-work review is frozen in:

```text
ANALYZER_METRIC_LITERATURE_AUDIT_V1
```

The review separates six metric families already used in the literature:

```text
exact / tolerance-based failure localization
failure-category and role attribution
evidence grounding and human/judge agreement
artifact or rerun quality
verified critical-step training and final task performance
process efficiency and redundant-step detection
```

These remain comparison metrics. Their common limitation for this project is
that no one of them simultaneously keeps the full eligible failure-state
universe, abstentions, invalid outputs, Harm, Neutral, verification cost, and
repair specificity visible.

The project therefore preregisters `Eligible-State Verified Repair Yield
(EVRY)` as its primary C1 endpoint. D0–D4 additionally reports a secondary
`specificity-confirmed repair yield` (internal compatibility name `CSVRY`).
Neither replaces final policy success. The authoritative targeted refinements
are frozen in `ANALYZER_METRIC_TARGETED_HARDENING_V2`. Metric language remains
`project-proposed` until the final related-work audit is complete.

## 3. Independent units and denominator rules

Primary independent unit:

```text
unique task/gamefile
```

For same-state comparisons, the paired source state is retained but all states
from one task/gamefile remain in the same resampling group.

Not independent:

```text
candidate branches
F0/F1 repeated continuations
minimal-prefix branches
multiple Analyzer hypotheses from one episode
multiple model calls within one trajectory
```

No abstention, invalid output, infrastructure incident, Harm, Neutral, or
Uncertain result may be silently removed.

## 4. Census and coverage metrics

Report before model-quality results:

```text
eligible task/gamefile count
selected count
excluded count by reason
family distribution
failure/success counts from full census
analysis regime and allocated counts
complete-evidence count
missing-evidence count
infrastructure-unavailable count
Memory-available / no-applicable-Memory count
```

The full rollout census and Analyzer-allocated sample are displayed separately.

## 5. Gold annotation and agreement

Failure lane:

```text
failure-onset exact agreement
failure-onset ±1 agreement
critical-window IoU
relevant-start absolute difference
terminal-consequence mechanical binding audit
error-lifecycle status agreement
mechanism-family agreement
repairability agreement
```

Success lane:

```text
necessary-transition agreement
useful-exploration agreement
self-recovery agreement
redundancy-candidate agreement
regression-guard agreement
workflow-boundary IoU
```

Double-annotation metrics are reported before adjudication.

## 6. Local Analyzer metrics

Primary localization metrics:

```text
failure-onset exact match
failure-onset ±1 accuracy
critical-window IoU
```

Grounding and honesty:

```text
evidence citation precision
evidence citation recall
invalid-reference rate
unsupported-fact rate
counterevidence coverage
alternative-explanation coverage
fact/hypothesis authority violation rate
```

Abstention and confidence:

```text
abstention precision
abstention recall on insufficient-evidence cases
coverage at accepted-confidence threshold
Brier score for registered confidence targets
ECE as secondary descriptive calibration
```

Calibration metrics are secondary when sample size is small.

## 7. Higher-level G/C/P/X metrics

```text
recurring-mechanism support groups
counterexample groups
cross-task support count
scope precision against gold/adjudication
component-attribution macro F1
profile coverage by task family
historical NO-GO overlap detection
X counterexample-discovery rate
X scope-downgrade rate
X unsupported-candidate rejection rate
X false rejection rate
candidate retention from G→C/P→X
per-layer token/latency/cost increment
```

Pilot layer metrics are diagnostic and do not expand the formal A0–A3 condition
count.

## 8. Candidate quality metrics

```text
schema-valid rate
evidence-supported rate
source-state binding rate
exact-admissible rate
executable rate
primitive-action share
short-option share
mean option length
candidate complexity distribution
duplicate-candidate rate
task-family coverage
mechanism coverage
abstention rate
```

## 9. Claim C1 primary repair-discovery metrics

### Common registered universe

Formal A0–A3 repair generation uses one frozen universe:

```text
U_reg = common preregistered eligible failure source states
K = one formal candidate or ABSTAIN per condition per unit
```

Full localization quality is evaluated separately on the gold panel. No
condition receives its own post-hoc eligible-state denominator.

### Primary — Eligible-State Verified Repair Yield (EVRY)

Operational estimand:

```text
EVRY_reg(a)
= unique U_reg units with at least one formal Benefit under condition a
  / all U_reg units
```

Execution-complete sensitivity:

```text
EVRY_avail(a)
= unique protocol-complete units with at least one formal Benefit
  / all protocol-complete units
```

`ABSTAIN`, no-candidate, schema-invalid, unsupported, non-admissible,
non-executable, Harm, Neutral, and Uncertain remain represented. Infrastructure
unavailability receives an explicit reason; method failures are not relabeled
as infrastructure. A formal Benefit requires same-state F0/F1 identity and the
frozen repeat rule.

### Mandatory safety companion — Harm

Report terminal Harm on both:

```text
failure cohort
PROTECTED_BASELINE_COHORT_V1
```

The protected cohort is separately preregistered and contains baseline-success
or high-probability-success states, late-stage valid-path states, and
wrong/non-applicable repair safety states. Failure-to-failure cost worsening is
not terminal Harm; report paired delta-steps, delta-calls, delta-progress, and
budget debt. If observed Harm is 0/n, report an exact upper confidence bound.

### Mandatory coverage companion — ProposalCoverage

```text
eligible U_reg units with a formal proposed candidate / all U_reg units
```

### Secondary — Verified Benefit Precision per Proposed Candidate (VBP)

```text
formal Benefit candidates / all formally proposed candidates
```

Proposed schema-invalid, unsupported, non-admissible, non-executable, Harm,
Neutral, and Uncertain candidates remain in the denominator. ABSTAIN contributes
no candidate to VBP but remains in EVRY. Under K=1 and complete execution, audit
`EVRY = ProposalCoverage * VBP`.

### Primary verification cost

```text
formal verifier environment steps consumed
/
unique U_reg units with formal Benefit
```

Also report branch episodes, policy calls, Analyzer tokens, API dollars, and
wall time separately. No weighted composite is permitted. If there are no
Benefits, report infinity/not-estimable rather than zero.

### Budgeted discovery curve — EVRY@B

Primary x-axis:

```text
cumulative formal verifier environment steps
```

Primary y-axis:

```text
cumulative unique repaired U_reg units / |U_reg|
```

Overlay cumulative Harm units. Candidate priority order is frozen before any
F0/F1 outcome. Tokens, dollars, and wall time are separate diagnostics, not
alternative post-hoc primary x-axes.

Additional C1 diagnostics:

```text
Benefit/Harm/Neutral/Uncertain counts
invalid/non-executable count
ABSTAIN/no-candidate count
infrastructure reason census
time-to-first-Benefit
unique Benefit task families
EVRY by task family and trajectory-length bucket
primitive vs short-option stratification
```

## 10. Claim C2 verification metrics

```text
Benefit/Harm/Neutral-success/Neutral-failure/Uncertain counts
non-Benefit fraction among plausible executable proposals
Harm caught before training
false-promotion rate if language score alone were used
Analyzer confidence vs environment outcome
LLM-judge score vs environment outcome
Memory similarity vs environment outcome
paired success-flip matrix
```

Report exact candidate funnel numerators from failures to verified outcomes.

## 11. Success-quality metrics

Primary pilot endpoints:

```text
success-preservation rate
verified efficiency-gain rate
success-regression rate
```

Efficiency decomposition:

```text
environment steps saved
policy calls saved
input/output tokens saved
latency saved
no-effect transitions reduced
exact repeats reduced
destination revisits reduced
time-to-first-progress change
```

Safety/quality:

```text
necessary-transition retention
regression-guard violation
self-recovery retention
useful-exploration false-removal rate
```

## 12. Repair-decomposition metrics

```text
D1 total-effect retention
shortest tested sufficient prefix
D3 registered matched-perturbation result
D4 history-attenuated result
specificity-control pass rate
history-dependence rate
compositional-option rate
unresolved/confounded rate
```

### Specificity-confirmed repair yield (internal compatibility id: CSVRY)

For the preregistered decomposition cohort:

```text
specificity-confirmed units
/
all registered decomposition units
```

A specificity-confirmed unit requires a retained formal D1 Benefit, registered
D3 matched controls that do not reproduce that Benefit, and a D2 sufficient
prefix classification. `minimal sufficient prefix` language is allowed only if
all shorter prefixes were tested, all are definitively non-Benefit, and none is
Uncertain; otherwise report `shortest tested sufficient prefix`.

D3 controls match action count, admissibility, environment-step budget, novelty,
observation opportunities, and option-termination budget. D4 is separate
history-context evidence. Specificity is secondary, does not claim full causal
mediation, and is not a training-eligibility gate for an otherwise formal
Benefit.

## 13. Distillation and localization metrics

Teacher/reference pipeline:

```text
request success
schema parse success
human accept/revise/reject/defer
revision rate
unsupported-fact rate
verified-supervision fraction
class and task-family distribution
cost per accepted trace
```

Local Analyzer comparison:

```text
localization metrics
evidence grounding
abstention
candidate executability
Benefit yield per eligible state
Harm rate
environment calls per Benefit
external/local disagreement rate
```

Do not use BLEU or prose similarity as a primary metric.

## 14. Final policy-facing metrics reserved for later stages

For π1→π2 evaluation:

```text
Memory-OFF + Harness-OFF task success
paired task success difference
family macro success
previously-successful-task regression
steps/calls/tokens among successes
interface/protocol error rate
loop/no-effect burden
multi-seed stability
intervention demand when optional scaffolds are re-enabled
```

These metrics are defined here for continuity but are not created by the
Analyzer design package.

## 15. Statistics

- report exact numerators and denominators;
- use task/gamefile-grouped paired bootstrap intervals for paired differences;
- use Wilson intervals for single proportions when appropriate;
- use exact McNemar tests for paired binary condition outcomes as a supporting
  test;
- report risk difference and relative risk, not p-values alone;
- report task-family micro and macro summaries;
- Holm-adjust secondary multiple contrasts;
- preregister A2−A1 and A3−A2 as the principal hierarchy/history contrasts;
- do not perform significance testing on schema fixtures or the 12-state pilot;
- conduct worst-case sensitivity for infrastructure-missing outcomes;
- retain all negative and failed versions in the experiment ledger.

## 16. Cost and reproducibility ledger

```text
provider/model/version/date
prompt/schema/config/code hashes
API input/output tokens
API cost
request latency
human annotation/adjudication time
environment branch count
environment wall time
GPU type/memory/hours
training time and tokens when applicable
storage footprint
infrastructure incidents
failed/pilot experiments not in the main table
```

## 17. Main paper display plan

Main text:

```text
Table: A0–A3 EVRY, Harm, ProposalCoverage, VBP, and verifier environment steps per repaired unit with exact numerators/denominators
Figure: EVRY@B Verified Repair Discovery Curves with cumulative Harm overlay
Figure: candidate funnel to B/H/N/U
Small table: localization/grounding/abstention
Small panel: success-preserving optimization pilot
Appendix: specificity-confirmed subset of EVRY on the preregistered D0–D4 cohort
```

Appendix:

```text
full metric definitions
all numerators/denominators
family-stratified results
layer diagnostics
calibration
cost ledger
repair decomposition
all negative and infrastructure outcomes
```
