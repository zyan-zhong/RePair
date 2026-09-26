# ANALYZER_METRIC_TARGETED_HARDENING_V2

## Status

```text
METRIC_DESIGN = APPROVED_IN_PRINCIPLE
STATUS = TARGETED_HARDENING_APPLIED
MAJOR_REDIRECTION = NO
PAPER_PRIMARY_ENDPOINT = PI2_VS_PI1_MEMORY_OFF_HARNESS_OFF_TASK_SUCCESS
REPAIR_DISCOVERY_PRIMARY_ENDPOINT = EVRY
```

This addendum hardens the existing `ANALYZER_METRIC_REGISTRY_V1`; it does not
create a second metric system. If older wording conflicts with this document,
this hardening governs the Analyzer V2 implementation plan.

## 1. Common registered universe

The formal A0–A3 repair-generation comparison uses one preregistered common
failure-state universe:

```text
U_reg = same frozen eligible source states for A0, A1, A2, and A3
K = 1 candidate or ABSTAIN per condition per unit
```

Eligibility is frozen before Analyzer output and before any F0/F1 outcome.
`ABSTAIN`, no-candidate, schema-invalid, unsupported, non-admissible,
non-executable, Harm, Neutral, and Uncertain remain represented. Full
localization ability is evaluated separately on the gold panel.

## 2. EVRY estimands

Operational estimate:

```text
EVRY_reg = unique U_reg units with >=1 formal Benefit / all U_reg units
```

Execution-complete sensitivity:

```text
EVRY_avail = unique protocol-complete units with formal Benefit /
             all protocol-complete units
```

Every infrastructure-unavailable unit receives one explicit reason. Method
failures such as invalid schema, context overflow, unsupported evidence, or
non-executable candidates are not reclassified as infrastructure failures.

Formal Benefit authority requires the existing same-state F0/F1 protocol and
its frozen repeat rule. Screening signals, progress events, LLM judgement, or a
single promising branch do not enter the EVRY numerator.

## 3. Safety and negative effects

EVRY is computed on the frozen failure cohort. A small separately registered
`PROTECTED_BASELINE_COHORT_V1` is required before making a strong Harm/safety
claim. It contains states with successful/high-probability baseline
continuations, late-stage valid-path states, and registered wrong/non-applicable
repair stress states.

Report terminal Harm separately on:

```text
failure cohort
protected baseline cohort
```

A failure-to-failure intervention that wastes steps is still `Neutral-failure`
at the terminal label level and is reported through paired delta-steps,
delta-calls, delta-progress, and budget-debt diagnostics. Zero observed Harm is
reported with an exact upper confidence bound rather than as proof of safety.

## 4. Proposal coverage, precision, and cost

Under K=1:

```text
ProposalCoverage = units with a formal proposed candidate / all U_reg units
VBP = Benefit candidates / all formally proposed candidates
```

The VBP denominator retains proposed candidates that are schema-invalid,
unsupported, non-admissible, non-executable, Harm, Neutral, or Uncertain.
ABSTAIN contributes no candidate to VBP but remains in EVRY's denominator.
When execution is complete, the implementation audits the identity
`EVRY = ProposalCoverage * VBP` within numerical tolerance.

Primary verification cost:

```text
formal verifier environment steps consumed /
unique U_reg units with formal Benefit
```

Also report branch episodes, policy calls, Analyzer tokens, API dollars, and
wall time separately. No weighted composite cost is allowed. With zero Benefit,
cost per repaired unit is infinity/not estimable, never zero.

`EVRY@B` is a budget curve whose primary x-axis is cumulative formal verifier
environment steps and y-axis is cumulative unique repaired U_reg units divided
by `|U_reg|`. Candidate priority order is frozen before F0/F1 outcomes. Analyzer
tokens, dollars, and wall time are separate diagnostics rather than combined
into the primary x-axis.

## 5. Gold-panel mechanical authority

`terminal consequence` is a deterministic evidence field. It may be copied or
bound from Mechanical Evidence for trace completeness, but it is not a scored
semantic prediction by the Analyzer. Analyzer localization scoring centers on
failure onset, tolerance, critical-window IoU, evidence grounding,
counterevidence, unsupported facts, and abstention.

## 6. Specificity-confirmed decomposition

Internal artifact names may retain `CSVRY` for compatibility, but paper-facing
language is `specificity-confirmed repair yield` or `specificity-confirmed
subset of EVRY`. It is secondary, not a headline endpoint and not a training
eligibility gate.

D2 reports `shortest tested sufficient prefix` unless every shorter prefix has
been tested, every shorter prefix is definitively non-Benefit, and none is
Uncertain. Only then may `minimal sufficient prefix` language be used.

D3 specificity is relative only to registered matched controls. Controls must
match action count, admissibility, environment-step budget, novelty,
observation opportunities, and option-termination budget. The valid claim is:

```text
registered mechanically matched perturbations did not reproduce the Benefit
```

D4 history dependence remains separate and does not invalidate a verified
Benefit. Specificity failure does not make a formal Benefit ineligible for
verified-training consideration; it only weakens mechanism-specific language.

## 7. Statistics and reporting

- raw numerator/denominator are mandatory;
- task/gamefile-clustered paired bootstrap is the primary interval method;
- repetitions/branches do not increase independent sample size;
- A2-vs-A1 and A3-vs-A2 are the preregistered principal contrasts;
- Holm adjustment is applied to registered secondary multiple comparisons;
- the main paper reports EVRY, Harm, ProposalCoverage, VBP, verifier environment
  steps per repaired unit, and EVRY@B;
- weighted composite scores are forbidden;
- EVRY is described as a project-proposed coverage-aware environment-verified
  repair-discovery endpoint, not as the first mathematically novel ratio.
