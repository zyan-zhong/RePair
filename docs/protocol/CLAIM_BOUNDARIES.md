# Claim Boundaries

## Evidence ladder

| Level | Minimum evidence | Allowed claim |
|---|---|---|
| L0 | Harness-ON system score improves | External mechanism improves the combined system |
| L1 | Audited behaviour and event changes | The system exhibits the reported behavioural change |
| L2 | Matched F0/F1 paired evidence | The intervention has a conditional effect under the frozen state and continuation protocol |
| L3 | Fresh task-held-out safe selection | Online-visible state information supports selective intervention on new tasks |
| L4 | Trained policy improves with Harness OFF | The capability is at least partially internalised |
| L5 | Second model/task interface/environment | The framework shows preliminary transfer |

## Prohibited overclaims

The project must not claim:

- V7B.3c performance is raw-model capability;
- Harness-ON improvement proves model self-improvement;
- finding or acquiring one object equals terminal task success;
- one F0/F1 sample is a stable individual causal effect;
- historical Fresh5 action modification caused terminal success;
- results from selected exact states equal all134 success rates;
- no-menu failure frequencies describe with-menu behaviour;
- a safe mandatory fallback is a learned harm detector;
- old 78-state model shopping validates a new representation;
- ALFWorld-specific CE-EFO alone proves a general framework.

## Required language

Prefer:

> Under the frozen matched-state and continuation protocol, the local
> intervention changed the paired terminal outcome for this state.

Do not write:

> This action is universally causal.

Prefer:

> The trained policy improved on held-out tasks with the Harness off.

Do not write:

> The model learned the capability because the Harness-assisted system
> improved.

## E1 terminology boundary

E1 may be described as an off-the-shelf or project-unadapted
instruction-model baseline.

E1 must not be described as:

- the pretrained Qwen base model;
- the V3PlannerPhase adapted policy;
- a policy trained on project trajectories;
- a single-variable ablation of the full historical V7B.3c system.

`RAW` describes the direct model-to-environment execution boundary,
not the absence of general instruction tuning.
