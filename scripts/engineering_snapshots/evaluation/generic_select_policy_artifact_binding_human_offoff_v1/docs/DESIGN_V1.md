# Generic SELECT Policy-Artifact Binding for Human OFF/OFF — Design V1

## Goal
Generalize the existing P4 Harness-OFF SELECT identity/runtime layer from the historical fixed pi0/pi1 experiment to arbitrary frozen trained LoRA policy artifacts, while preserving existing pi0/pi1 behavior and all evaluator, Runtime Core, parser, prompt, budget, ALFWorld and artifact semantics.

## Scientific boundary
This change does not execute evaluation and does not change the Human T2 scientific result. It only enables exact identity binding for the parent Train17 adapter and the new Human-T2 candidate adapter. The candidate remains diagnostic-only and non-promotable until OFF/OFF evaluation is audited.

## Compatibility strategy
- Keep the V1 wire structures and schema IDs.
- A static LoRA registration may use any non-pi0 logical condition.
- The shared SELECT server registry may contain one or more frozen LoRAs.
- Training seeds may repeat across different logical conditions; duplicate `(logical_condition_id, training_seed)` pairs remain forbidden.
- `max_cpu_loras` must cover every statically registered LoRA.
- Legacy `P4-R1-Q2-BAD` keeps `policy_version=PI1_BAD`; later trained conditions use their exact logical-condition ID as policy version.
- Result audit continues to treat pi0 specially and rejects any trained LoRA that claims pi0 logical identity.

## Unchanged surfaces
No changes to `episode_evaluator.run_single_episode`, Runtime Core, policy client/request/response semantics, prompt construction, admissible-menu semantics, budgets, ALFWorld adapter, artifact publication, task-access governance, condition-schedule construction or retry semantics.

## Isolation
Implementation is performed test-first in a detached worktree based on exact HEAD `daef26b9cde45182ada534d96335da3ea451f12f`. Nothing is committed or pushed.
