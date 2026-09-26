# ANALYZER_A0_A3_PILOT_PROTOCOL_V1

## 1. Purpose and scope

Freeze staged evaluation of the failure-repair conditions A0–A3 while keeping
success-quality analysis and repair-effect decomposition as separate experiments.

```text
schema fixtures
→ failure/success gold annotation
→ 12-failure-state plumbing/cost pilot
→ 30-failure-state main repair discovery
→ 12-success-episode optimization pilot
→ 8–12 Benefit repair decomposition
```

Pilot outcomes never enter formal repair-discovery denominators.

## 2. Failure-repair conditions

```text
A0_ONE_SHOT_LOCAL
A1_MULTI_HYPOTHESIS_LOCAL
A2_HIERARCHICAL_NO_HISTORY
A3_HIERARCHICAL_WITH_HISTORY
```

A1 local results are generated once. A2 and A3 reuse identical local result
hashes. A3 adds exactly one frozen Analyzer Memory packet at the higher-level
stage. Local passes remain Memory-blind.

## 3. Common fairness contract

The mechanical 85/15, 70/30, and 55/45 scheduler is not used to define this
formal panel. A0–A3 receive the same failure-only `U_reg`.

Frozen across A0–A3:

```text
common preregistered failure-state universe U_reg
common Analyzer Evidence Pack
strong model/provider/reasoning mode
output token cap
maximum hypotheses
maximum candidate count per state = 1
maximum repair action count
same total environment-step budget
same allowed new-observation budget
repair kinds
F0/F1 runner
success definition
task-access policy
```

Only exact executable action/option bytes enter F1. Analyzer prose and Memory
explanations never enter the Task Policy prompt.

Primitive and short-option results are reported separately. Exact duplicate
candidates share one environment execution and result binding.

## 4. Schema-development fixtures

Reuse the three registered Memory source cases only for rendering, schema,
parser, Memory attachment, abstention, and projector checks. They contribute to
no quality or effect denominator.

## 5. Gold annotation

Failure gold panel:

```text
target 36 unique failed episodes
minimum 30
approximately six per task family where available
```

Success reference panel:

```text
12 unique successful episodes
approximately two per task family where available
```

Both panels use deterministic task/gamefile selection and preserve imbalance
rather than duplicate episodes.

## 6. Twelve-failure-state pilot

```text
12 fresh train-side failures
unique gamefiles
same U_reg states across A0–A3
K=1: one formal candidate or ABSTAIN per condition
```

Maximum environment continuations:

```text
12 shared F0
+
up to 48 deduplicated F1
```

Pilot outputs include schema/reference failures, candidate validity,
executability, abstention, tokens, latency, cost, per-layer changes, verifier
throughput, and infrastructure incidents.

One explicit design review may freeze the formal prompt/schema after the pilot.
No prompt/schema/grouping/budget change is allowed after formal F0/F1 outcomes
are visible.

## 7. Main failure repair-discovery panel

```text
30 fresh train-side failed states forming one common U_reg
```

Rules:

- unique task/gamefile is the independent unit;
- deterministic frozen selection;
- no outcome-aware or repairability-aware selection;
- no overlap with fixtures or gold panels;
- all conditions run on the exact same preregistered U_reg states;
- U_reg freezes before Analyzer output and before F0/F1 outcomes;
- K=1 candidate-or-ABSTAIN is enforced at the formal candidate layer;
- preserve every proposal, rejection, abstention, and infrastructure incident.

Maximum theoretical continuations before candidate deduplication:

```text
30 shared F0 + up to 120 F1 = 150
```

## 8. Primary formal metrics

From `ANALYZER_METRIC_REGISTRY_V1` and the frozen literature audit:

```text
Eligible-State Verified Repair Yield (EVRY_reg + EVRY_avail sensitivity)
Harm on failure cohort + protected baseline cohort
ProposalCoverage
Verified Benefit Precision per Proposed Candidate (VBP)
formal verifier environment steps per repaired unique U_reg unit
EVRY@B Verified Repair Discovery Curves
Neutral and Uncertain counts
coverage and abstention
candidate validity/executability
cost per Benefit
```

EVRY is the principal C1 endpoint. Every eligible state remains in its
denominator, so no-candidate, ABSTAIN, invalid, and non-executable cases cannot
be silently excluded. Harm, ProposalCoverage, VBP, and verification cost are mandatory companions;
none is folded into an arbitrary weighted score. Method failures remain in the
registered operational denominator and infrastructure sensitivity is reported
separately.

A2−A1 and A3−A2 are preregistered paired contrasts.

## 9. Protected baseline safety cohort

Before making a strong terminal-Harm/safety claim, separately preregister a
small protected cohort containing baseline-success/high-probability-success
states, late-stage valid-path states, and wrong/non-applicable repair stress
states. It is not part of EVRY's failure denominator.

Report terminal Harm independently on the failure and protected cohorts. Also
report paired delta-steps, delta-calls, delta-progress, and budget debt so that
failure-to-failure degradation is not hidden by a zero terminal-Harm count.

## 10. Separate success-quality pilot

Use the best frozen Analyzer configuration from localization/grounding gates,
not from success-optimization outcomes.

```text
12 successful episodes
at most one efficiency candidate each
```

Compare baseline successful continuation with a registered candidate
intervention. Labels and metrics follow the success-quality sections of the
metric registry. Failure A0–A3 denominators remain unchanged.

## 11. Repair Effect Decomposition

After formal Benefits are frozen, mechanically select 8–12 distinct candidates
and execute `REPAIR_EFFECT_DECOMPOSITION_V1`. The decomposition protocol cannot
change the original A0–A3 Benefit label.

The frozen cohort reports a secondary `specificity-confirmed repair yield`
(internal compatibility id `CSVRY`). It requires D1 Benefit retention, failure
of registered D3 matched perturbations to reproduce the Benefit, and a D2
sufficient tested prefix. D4 history-context dependence remains separate.
Specificity never gates training eligibility for an otherwise formal Benefit.

## 12. Stop conditions

Stop expansion if:

- evidence grounding fails;
- candidate executability is too low;
- group synthesis suppresses disagreement;
- A3 changes common evidence or local results;
- success optimization causes unacceptable regression;
- infrastructure prevents state equality;
- formal prompt changes would be required after outcomes are visible;
- external trace/provenance is incomplete.


## Source-conditioned higher-level repair rule

Formal A0–A3 conditions use the same failure-only `U_reg`; each condition must produce exactly one source-conditioned candidate or ABSTAIN for every registered unit.

A2/A3 do not receive an extra unequal proposal call. The registered G-stage may
produce one source-conditioned repair per member source state while seeing that
state's exact evidence/menu. C/P/X may rank, downgrade, or reject but cannot
rewrite executable bytes. Projector validation remains deterministic; abstract
templates without executable source-conditioned bytes become ABSTAIN.
