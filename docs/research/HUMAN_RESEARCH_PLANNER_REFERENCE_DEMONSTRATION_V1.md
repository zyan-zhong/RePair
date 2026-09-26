# Human Research Planner Reference Demonstration V1

## 1. Purpose

The first π1→π2 Human round is not merely a one-off manual experiment. It is a
typed demonstration of how a Research Planner should:

1. read frozen policy, Analyzer, Memory, experiment-history and budget evidence;
2. identify the principal round bottleneck;
3. compare candidate repairs using evidence and counterevidence;
4. allocate a bounded verification portfolio;
5. predict value, Harm risk and cost without claiming causal effect;
6. update its beliefs only after independent F0/F1 results;
7. build verified training evidence under a frozen data policy;
8. preserve lessons for the next round and Local Researcher supervision.

The same PRE/POST interface is used by Human, Strong-API shadow and future Local
Research Planner roles.

## 2. Canonical candidate view

The Formal candidate pool contains multiple semantic layers:

```text
group results
source-conditioned proposals
cross-check sidecars
repair candidates
summary/wrapper objects
```

Only objects with:

```text
schema_id = ANALYZER_REPAIR_CANDIDATE_V1
```

and registered executable status enter the canonical selected pool. The adapter
joins proposal, group and cross-check lineage but never modifies the candidate.

The current Formal result must reproduce:

```text
60 executable rows
30 A2
30 A3
30 unique source states
one A2/A3 pair per state
```

## 3. Planner PRE reasoning

For each candidate/state pair, the Human demonstration records:

```text
evidence grounding
counterevidence
task family / mechanism
repair kind and termination
historical NO-GO overlap
expected Benefit value
expected Harm risk
verification cost
duplication / novelty
selection rationale
```

The Planner may prioritize or compose a bounded repair program. It cannot turn
a language-plausible candidate into Benefit/Harm authority.

## 4. Budget planning

Budget is derived from the frozen round resource manifest and verification
protocol:

```text
registered_state_budget
=
(total_branch_run_budget - reserve)
/
(2 arms × paired_repetitions_per_state)
```

For the current reference round:

```text
120 branch runs
5 paired repetitions
2 arms
→ 12 registered source states
```

This arithmetic is automatic. Future rounds change budget-manifest inputs, not
the loop code. Outcome-adaptive replacement or budget expansion is forbidden.

## 5. POST reasoning

After the independent verifier seals all selected states, POST records:

```text
Benefit/Harm/Neutral/Uncertain census
Benefits per verification budget
environment calls per Benefit
task-family coverage
duplicate-mechanism rate
unexpected Harm
hypothesis status
training recommendation
next-round lesson
```

PRE rationale is immutable.

## 6. Training data construction

The pre-registered arms remain:

```text
T0  untrained parent
T1  ordinary success SFT
T2  unverified Analyzer repairs
T3  environment/event-valid repairs
T4  verified Benefit-only SFT
T5  Benefit-Harm preference
T6  audited RL, optional
```

Eligibility:

```text
Benefit  → positive SFT / chosen preference
Harm     → rejected preference, never positive SFT
Neutral  → analysis only by default
Uncertain→ excluded
InfrastructureInvalid → no scientific label
```

No universal primary mixture ratio is invented before F0/F1. Exact mixture
ratios are frozen after the verifier census and training-eligibility audit, but
before any trained-policy SELECT result. Comparable arms use the same total
training-token budget and shared optimizer/recipe.

The historical 50/50 correction-success-rehearsal mixture is retained only as a
secondary fixed-budget control, not assumed to be optimal.

## 7. Localization supervision

The reference trace preserves:

```text
exact input package
Human PRE
Strong shadow PRE
field-level differences/adjudication
portfolio and budget
actual F0/F1 outcomes
training mixture decision
policy evaluation
GO/NO-GO lesson
```

These records supervise later Local Research Planner training. The local model
must learn both successful decisions and rejected/deferred directions, not only
the final selected answer.
