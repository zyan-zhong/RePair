# F0F1_REPAIR_VERIFICATION_V2

## Reuse rule

Reuse the existing exact-state/deterministic-prefix replay and paired execution
infrastructure. V2 adds a typed repair-registration ingress and evidence-sidecar
binding; it does not create a second branch runner.

## Registered repair

A repair registration binds:

```text
candidate_repair_id
analyzer_condition
analyzer_run_id
analyzer_output_sha256
source_state_id
source_task_id
source_gamefile_sha256
source_prefix_sha256
source_policy_identity_sha256
memory_snapshot_sha256
repair_kind
repair_actions_or_option
repair_budget_cost_rule
return_control_rule
registration_sha256
```

## Pair invariants

F0 and F1 must share:

```text
task/gamefile
initial state or fully revalidated deterministic prefix
public observation and complete menu at decision state
executed working history
π1 concrete identity
Memory snapshot and Policy Memory condition
Runtime Core/parser
decoding contract
remaining policy/environment budgets
paired seed
success definition
artifact publication contract
```

The sole registered intervention is:

```text
F0 = π1 baseline action/continuation
F1 = registered repair, then return to the same frozen π1 continuation
```

Every repair action counts against the same total environment budget.

## Outcomes

```text
Benefit
Harm
NeutralFailure
NeutralSuccess
Uncertain
InfrastructureInvalid
```

Analyzer and Researcher cannot create or overwrite these outcomes.

## Repeat policy

Development pilot may use one frozen pair seed for plumbing and throughput.
Formal causal labels follow the separately preregistered paired-repeat rule.
Infrastructure failures invalidate both arms and cannot trigger selective
reruns of only the unfavorable arm.
