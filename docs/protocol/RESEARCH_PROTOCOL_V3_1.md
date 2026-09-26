# Raw-Policy Research Protocol v3.1

## Status

This document is the canonical research protocol for
Phase-Critical Harness-Guided Self-Improvement.

The full research proposal is Draft v3.1, dated 2026-07-31.
This repository document records its executable research boundary.

## Core research question

Can local executable interventions identify decision states that
conditionally change terminal outcomes, and can audited evidence be
transferred into a policy that improves with the Harness disabled?

## System conditions

| ID | Condition | Role |
|---|---|---|
| `HIST` | Historical V7B.3c composite system | Historical reference |
| `R0` | Off-the-shelf Qwen2.5-3B-Instruct under `RAW_WITH_MENU_V1`, Harness OFF | Primary project-unadapted policy baseline |
| `R1` | The same R0 policy without an action menu | Independent grounding stress test |
| `R2` | `R0` plus Phase-Critical Harness | Primary intervention system |
| `R3` | Trained policy, Harness OFF | Core internalisation test |
| `R4` | Trained policy, Harness ON | Secondary collaboration ceiling |

Primary system-effect comparison:

```text
R0 versus R2
```

Decisive policy-internalisation comparison:

```text
R3 versus R0
```

with the Harness disabled in both conditions.

## E0/E1 model boundary

`HIST` is the historical V7B.3c composite system, including its
V3PlannerPhase project LoRA and historical controllers.

E1/R0 uses the off-the-shelf instruction model:

```text
Qwen/Qwen2.5-3B-Instruct
revision aa8e72537993ba99e69dfaafa59ed015b17504d1
project adapter: none
```

The model must remain byte-identical across R0, R2 and their
matched continuations. "Model fixed" applies within the new
R0/R2 causal comparison; it does not make E0 and E1 a
single-variable comparison.

The complete boundary is defined in
`docs/protocol/E1_OFF_THE_SHELF_MODEL_BOUNDARY.md`.

## Immutable v3.1 conditions

1. Every with-menu condition receives the complete current admissible
   action list in the environment-provided order.
2. Policy and Phase-Critical Harness receive byte-identical action lists.
3. No sorting, filtering or truncation is allowed.
4. The public task goal is repeated at every decision.
5. The current observation is provided in full.
6. History contains the most recent eight executed environment
   transitions.
7. The parser is a strict top-level JSON transport parser and cannot
   inspect or rewrite against the admissible-action list.
8. Historical phase, guard, DONE, release and retake rewrites are off.
9. The total environment-step budget is 30.
10. Every Harness option action consumes the shared step budget.
11. Online policy and selector features cannot use hidden state, future
    observations, F0/F1 outcomes or terminal reward.
12. Final self-improvement requires trained-policy improvement with the
    Harness disabled on held-out tasks.

## F0/F1 matched protocol

Each accepted decision state is evaluated using five paired replicates:

```text
seeds = [17, 31, 47, 73, 101]
```

Each pair:

- begins from the same task and matched decision state;
- uses the same model, prompt, decoding configuration and seed;
- has the same remaining environment-step budget;
- differs only by the registered local intervention;
- counts all option actions against the shared budget.

Stable labels require at least four of five valid paired replicates:

- Benefit: F0 fails and F1 succeeds;
- Harm: F0 succeeds and F1 fails;
- Neutral failure: both fail;
- Neutral success: both succeed;
- Uncertain: no category reaches the stability requirement, opposite
  directional effects coexist, or fewer than five valid pairs remain.

Infrastructure failure invalidates both arms of the replicate.
State, observation, command-list, budget or runner-fidelity mismatch
invalidates the entire batch.

## Research progression

```text
E0 historical audit
→ E1 raw-with-menu baseline
→ E2 no-menu stress test
→ E3 verifier/detector audit
→ E4–E5 intervention and equal-cost controls
→ E6–E8 fresh matched causal evidence
→ E9–E11 safe graph-state selection
→ E12–E16 policy training and Harness removal
→ E17–E19 transfer
→ E20 optional Trainer Agent
```

## Approval workflow

Default:

```text
DESIGN_APPROVED
→ CODE_APPROVED
→ RESULT_AUDIT_APPROVED
```

`EXECUTION_APPROVED` is additionally required for full rollouts,
matched F0/F1 experiments, formal training and paper-primary results.

## E1 runtime-core budget clarification

E1 uses two independent limits:

```text
max_policy_attempts = 60
max_environment_steps = 30
```

It also terminates after three consecutive attempts that execute no
environment action.

Format/schema failure and exact-menu-membership failure each consume one
policy attempt but consume no environment step.

These outcomes are reported separately as
`FORMAT_PROTOCOL_FAILURE` and `ACTION_NOT_ADMISSIBLE`.

The complete design and test contract are frozen in:

`docs/superpowers/specs/2026-07-31-e1-runtime-core-v1-design.md`
