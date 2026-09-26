# REPAIR_DISCOVERY_AND_SAME_STATE_VERIFICATION_PROTOCOL_V1

## 1. Scope

Coordinate Analyzer candidate discovery, Human Training Researcher
prioritization, existing exact-state replay, same-state F0/F1 verification and
verified-training eligibility.

This protocol does not implement a second branch runner.

## 2. Candidate funnel

Every source failure is accounted for through:

```text
eligible failure
→ Analyzer output received or infrastructure incident
→ schema-valid candidate or abstention
→ evidence-supported candidate
→ admissible/executable candidate
→ F0/F1 registered
→ Benefit / Harm / Neutral / Uncertain / InfrastructureInvalid
→ training eligible or excluded
```

No denominator may silently discard abstentions, Harm, Neutral or invalid
outputs.

## 3. Candidate registration

A registered candidate binds:

```text
candidate_repair_id
condition_id
analyzer_run_id
analyzer_result_sha256
source evidence pack SHA
source task/gamefile
source attempt bundle SHA
decision call index
source state SHA
source prefix SHA
menu SHA
π1 identity SHA
Memory snapshot/packet SHA or null
repair kind/content
repair cost rule
return-control rule
registration SHA
```

Only `EXECUTABLE_EXACT_ACTION` and `EXECUTABLE_SHORT_OPTION` can enter F1.

## 4. Candidate deduplication

Deduplication keys:

```text
task/gamefile
source state SHA
source prefix SHA
mechanism family
repair kind
canonical repair content
```

Cross-state semantic similarity may create a reporting group but cannot merge
different causal units or overwrite individual outcomes.

## 5. Researcher selection interface

The Human Training Researcher receives the frozen candidate pool and may select
a bounded portfolio.

It may use:

- mechanism frequency;
- task-family coverage;
- evidence/counterevidence quality;
- Analyzer uncertainty;
- historical NO-GO;
- duplicate groups;
- estimated verification cost.

It cannot use future F0/F1 outcomes.

Selection experiments:

```text
R0 = frozen FIFO/task order
R1 = frequency-only heuristic
R2 = Human Training Researcher template
R3 = strong API Researcher shadow after R2 pre-decision freeze
```

All receive the same candidate pool and verification budget.

## 6. Same-state pair

F0 and F1 share:

```text
task/gamefile
reconstructed state or validated deterministic prefix
observation
complete admissible menu
executed history
π1 exact identity
Policy Memory condition
Memory snapshot
Runtime Core/parser
decoding
remaining budgets
paired seed
success definition
artifact publication
```

Intervention:

```text
F0 = frozen π1 baseline continuation

F1 = registered repair
     then return control to the same frozen π1 continuation
```

Every repair action consumes the shared environment-step budget.

## 7. Pair validation

Before execution:

- compare all frozen identity fields;
- validate source state and prefix hashes;
- validate remaining budgets;
- validate menu and repair registration;
- confirm the only planned difference is the registered repair.

After execution:

- compute first action/observation/menu/budget divergence;
- reject pairs with divergence before the registered intervention;
- publish both branches together;
- preserve raw evidence and infrastructure errors.

## 8. Development and formal repeats

### Plumbing pilot

One frozen pair seed is sufficient to test infrastructure and throughput.

### Formal outcome

For the preregistered formal shortlist:

```text
five paired repetitions
```

Labels are assigned from the preregistered stability rule, with the source
task/gamefile remaining the independent scientific unit.

A nominal rule is:

```text
stable direction in at least 4/5 valid pairs
```

The exact rule must be frozen before formal outcomes are visible.

No selective rerun of only the unfavorable arm is permitted.

## 9. Outcome authority

Only the Environment Verifier may publish:

```text
Benefit
Harm
NeutralSuccess
NeutralFailure
Uncertain
InfrastructureInvalid
```

Analyzer confidence, Memory similarity and LLM-judge scores are diagnostics,
not effect authority.

## 10. Alternative controls

Where budget allows, include:

```text
equal-action-count random repair
novelty-only repair
extra-text-only guidance
extra-budget-only control
```

These test whether apparent gains come from additional steps, text, novelty or
budget rather than the proposed mechanism.

## 11. Outcome definitions

At minimum:

```text
Benefit:
  F0 fails and F1 succeeds under a valid same-state pair

Harm:
  F0 succeeds and F1 fails under a valid same-state pair

NeutralSuccess:
  both succeed

NeutralFailure:
  both fail without registered improvement

Uncertain:
  valid repetitions do not satisfy the frozen stability rule

InfrastructureInvalid:
  pair integrity or execution infrastructure is invalid
```

Progress diagnostics may be reported but cannot override terminal outcome
authority unless a separately frozen endpoint explicitly defines them.

## 12. Verified training eligibility

```text
Benefit
→ positive/chosen evidence

Harm
→ rejected/negative preference evidence

Neutral
→ excluded from the main training set by default

Uncertain
→ excluded

InfrastructureInvalid
→ no scientific label
```

Eligibility additionally requires:

- exact π1 policy identity;
- source/train access;
- complete F0/F1 evidence;
- candidate and pair lineage;
- no cross-split task/gamefile contamination;
- dedup identity;
- verified-training manifest inclusion.

## 13. Main claim outputs

Publish:

```text
candidate funnel
Benefit/Harm/Neutral/Uncertain census
false-promotion rate without verification
Benefit precision after verification
environment calls per Benefit
tokens and cost per Benefit
task-family coverage
plausible-but-harmful case
```

## 14. Hard boundaries

Forbidden:

- Analyzer self-labeling Benefit/Harm;
- Researcher overriding verifier outcomes;
- training before the verified manifest is sealed;
- omitting Harm or Neutral candidates;
- changing prompt or candidate budget after formal outcomes;
- using held-out detailed trajectories for Analyzer/Researcher;
- counting repeated branch seeds as independent tasks;
- creating a second replay/branch executor.
