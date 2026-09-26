# ANALYZER_METRIC_LITERATURE_AUDIT_V1

## 1. Purpose and scope

This audit records how adjacent agent-diagnosis and repair work evaluates its
claims, which parts are directly reusable, and which gaps require a stricter
metric design for Outcome-Aware Hierarchical Analyzer V2.

This is a metric-design audit, not a novelty declaration. The project may claim
that a metric is proposed by this work only after the final related-work review
confirms that no materially equivalent definition has already appeared.

## 2. Metric patterns in adjacent work

### 2.1 Failure-attribution benchmarks

Representative work:

```text
Who&When                    arXiv:2505.00212
AgentRx                     arXiv:2602.02475
FALAT                       dependency-guided failure tracing
LongRCA Bench / RCTA        arXiv:2608.15242
TraceElephant               arXiv:2604.22708
```

Common metrics:

```text
responsible-agent / responsible-role accuracy
exact critical-step or root-step accuracy
critical-step accuracy within ±k steps
mean absolute root-step error
failure-category accuracy / macro F1
performance by trajectory-length bucket
```

Strengths:

- precise, interpretable targets;
- human-labeled evaluation;
- exact and tolerance-based localization are easy to compare;
- separate role and step targets avoid collapsing distinct tasks;
- full-observability ablations expose missing-input failure modes.

Limitations for this project:

- a correct location or category does not imply that an executable repair exists;
- exact-step labels often compress a multi-error trajectory into one decisive
  location;
- the metrics do not by themselves measure Benefit, Harm, Neutral, or policy
  reachability;
- methods may abstain or fail to propose a repair without this appearing in a
  localization-only score;
- downstream environment and training costs are outside the main denominator.

### 2.2 Error-lifecycle diagnosis

Representative work:

```text
TrajDebug / TrajErrBench    arXiv:2608.06346
```

Common metrics and analyses:

```text
critical-step detection accuracy
performance by trajectory length
human agreement on critical-step labels
local-error lifecycle distribution
per-trajectory rerun success
failure-memory transfer success
```

Strengths:

- distinguishes resolved, persistent, and dormant local errors;
- evaluates whether diagnoses can improve later behavior;
- explicitly tests robustness as trajectories grow longer.

Limitations for this project:

- rerun gains can combine localization, natural-language guidance, extra
  observations, changed history, and additional actions;
- the reported repair result does not necessarily isolate whether the proposed
  primitive action, a multi-step option, or nonspecific perturbation caused the
  improvement;
- success-only application results do not fully expose Harm and Neutral rates;
- a rerun subset does not automatically preserve all eligible failures in the
  denominator.

### 2.3 Multi-hypothesis and research-agent recovery

Representative work:

```text
SAGE / MHFA                 arXiv:2606.31478
```

Common metrics:

```text
metrics-bearing output rate
artifact-quality score
blind evaluator score
human expert score
routing/threshold robustness
end-to-end run cost
```

Strengths:

- evaluates grounded reporting rather than only plausible prose;
- combines automatic and human judgments;
- reports robustness and practical cost.

Limitations for this project:

- artifact-level scores are not same-state environment effects;
- the unit is a research artifact, not an interactive task decision state;
- output quality can improve without discovering an executable repair that the
  local task policy can complete;
- candidate coverage, abstention, Harm, and environment calls per repair are not
  the central endpoints.

### 2.4 Verified critical-step post-training

Representative work:

```text
Critical Step Optimization  arXiv:2602.03412
```

Common metrics:

```text
final task accuracy after training
relative gain over SFT and other post-training baselines
fraction of trajectory steps receiving supervision
ablation of candidate selection and outcome verification
number of branch candidates
computational cost
multi-run performance
```

Strengths:

- outcome verification creates stronger supervision than estimated step scores;
- final task performance tests whether verified evidence is trainable;
- supervision density and computational cost are reported.

Limitations for this project:

- the positive verified subset is central, while the denominator of all eligible
  failure states is not the headline metric;
- Harm, Neutral, abstention, invalid candidates, and repair-discovery coverage
  require separate accounting;
- final post-training performance conflates diagnosis, candidate generation,
  verification, data construction, and optimization;
- verified branch success does not necessarily identify the minimal or causally
  specific repair mechanism.

### 2.5 Process decomposition and efficiency

Representative work:

```text
TrajEval                    arXiv:2603.24631
RedundancyBench             arXiv:2605.29893
```

Common metrics:

```text
stage-wise precision and recall
Pass@1 and intervention gain
steps/functions/tokens/cost
trajectory-level redundancy score
average per-trajectory step-level F1
```

Strengths:

- exposes process failures hidden by a terminal success metric;
- separates effectiveness from exploration efficiency;
- recognizes that successful trajectories can contain low-value steps.

Limitations for this project:

- TrajEval depends on a reference patch and measures where the agent acts, not
  whether the action is semantically correct;
- redundancy classification does not prove that removing a step preserves task
  success;
- coarse step, token, or latency reduction can reward unsafe pruning;
- neither metric directly measures verified repair discovery from failed states.

### 2.6 Scalable taxonomy and judge reliability

Representative work:

```text
HORIZON                     arXiv:2604.11978
```

Common metrics:

```text
task success by horizon
failure-mode distribution
inter-annotator agreement
human–judge agreement
cross-domain / length-stratified analysis
```

Strengths:

- validates whether a scalable judge reproduces human labels;
- reports failure composition, not only total failure rate;
- stratifies degradation by task horizon and domain.

Limitations for this project:

- agreement with a taxonomy is not evidence that the diagnosis yields an
  executable or beneficial repair;
- downstream candidate cost, Harm, abstention, and policy internalization remain
  separate questions.

## 3. Gap identified for Outcome-Aware Analyzer V2

No single localization, classification, prose-quality, or terminal-success
metric answers the project's main C1 question:

```text
Under the same eligible failure-state universe and a bounded research budget,
which Analyzer condition discovers more environment-verified repairs without
hiding abstentions, invalid outputs, Harm, or infrastructure failures?
```

Three anti-gaming requirements follow:

1. every eligible source state remains in the main denominator;
2. one state contributes at most one unit of repair-discovery success, even if
   several correlated candidates or repeats are executed;
3. Benefit must be reported together with Harm and verification cost.

## 4. Project-proposed primary metric

### 4.1 Eligible-State Verified Repair Yield (EVRY)

For Analyzer condition `a`, let `S_a` be the preregistered eligible source-state
set and `C_a(s)` be all registered candidates produced for source state `s`.
Let `Y(s,c)` be the Environment Verifier label.

```text
EVRY(a)
=
number of s in S_a for which at least one c in C_a(s) is verified Benefit
/
number of eligible source states in S_a
```

Formally:

```text
EVRY(a) = |{s ∈ S_a : ∃c ∈ C_a(s), Y(s,c)=Benefit}| / |S_a|
```

Denominator treatment:

```text
ABSTAIN                         retained
schema-invalid output           retained
unsupported candidate           retained
non-executable candidate        retained
no candidate                    retained
Harm / Neutral / Uncertain      retained
infrastructure unavailable      retained in the registered census and handled
                                by a preregistered sensitivity analysis
```

Why it is needed:

- candidate precision alone can be inflated by proposing on only easy states;
- localization accuracy can be high even when no useful repair is produced;
- raw count of Benefits rewards conditions assigned more states;
- branch-level rates treat correlated branches as independent;
- final policy accuracy mixes Analyzer quality with later training decisions.

EVRY is therefore the principal C1 endpoint. It is not sufficient alone and
must always be displayed with the safety and cost companions below.

### 4.2 Mandatory companions — targeted-hardened form

The earlier draft labels `HES` and `ECB` are superseded by the normative metric
registry. The primary table reports separately:

```text
failure-cohort terminal Harm
protected-baseline-cohort terminal Harm
ProposalCoverage
Verified Benefit Precision (VBP)
formal verifier environment steps per repaired unique U_reg unit
```

These quantities and EVRY are never collapsed into an arbitrarily weighted
single score. Failure-to-failure cost degradation is reported through paired
step/call/progress/budget diagnostics rather than relabeled as terminal Harm.

### 4.3 Budgeted discovery curve

Report:

```text
EVRY@B
```

for preregistered cumulative budgets `B`, where budget may be environment
branches, Analyzer tokens, API cost, or wall time. The paper plots the Verified
Repair Discovery Curve:

```text
x-axis = cumulative registered verification budget
y-axis = cumulative unique eligible states with Benefit / all eligible states
```

Cumulative unique Harm states are overlaid rather than subtracted with an
arbitrary weight. Conditions are compared at common budgets.

## 5. Project-proposed specificity-confirmed extension

### Specificity-confirmed repair yield (internal compatibility ID `CSVRY`)

EVRY measures total intervention value. The D0–D4 cohort adds a secondary
specificity analysis relative to preregistered mechanically matched controls.
It does not claim full causal mediation.

A candidate enters the specificity-confirmed numerator only when:

```text
D1 full registered repair retains Benefit
D3 registered matched controls do not reproduce the same Benefit
D2 identifies the shortest tested sufficient action/prefix
```

`Minimal sufficient` language is permitted only if every shorter prefix was
tested and definitively non-Benefit. D4 history attenuation is reported
separately. This secondary cohort does not gate a formal Benefit from verified
training consideration and cannot be extrapolated beyond its frozen coverage.

## 6. Metrics retained from prior work

The project still reports standard metrics so the results remain comparable:

```text
exact and ±1 localization accuracy
critical-window IoU
mechanism/component macro F1
evidence citation precision and unsupported-fact rate
inter-annotator agreement before adjudication
confidence calibration and abstention
success preservation / regression for successful trajectories
steps, calls, tokens, latency, and cost
final Memory-OFF + Harness-OFF task success after training
```

EVRY and CSVRY complement these metrics; they do not replace them.

## 7. Claim boundary

Until the literature review is complete, use:

```text
project-proposed metric
```

and not:

```text
first-ever metric
novel metric with no precedent
```

The scientific contribution is the environment-grounded, coverage-aware
measurement design and its role in the full repair-discovery chain.
