# E1 Off-the-Shelf Model Boundary

## Status

This document is the canonical E1 model-boundary clarification for
Research Protocol v3.1.

It resolves an ambiguity in the phrase "model fixed":

- the model is fixed across `R0`, `R2`, F0 and F1;
- the E1 model is not required to equal the historical V7B.3c
  adapted policy;
- `HIST` and E1 are not a single-variable causal comparison.

## E0 historical condition

E0 audits the historical V7B.3c composite system:

```text
Qwen2.5-3B-Instruct
+ V3PlannerPhase project LoRA
+ historical prompt and parser
+ historical phase controller
+ historical action guard
+ historical task-specific rewrites
```

Fresh5 is therefore reported only as:

> Historical V7B.3c composite-agent Fresh5 replications.

It contains 134 tasks × 5 replications = 670 episodes,
with 501 successes and 169 failures.

These counts are not raw-policy or off-the-shelf-model results.

## E1 policy condition

E1 uses exactly:

```text
repository = Qwen/Qwen2.5-3B-Instruct
revision = aa8e72537993ba99e69dfaafa59ed015b17504d1
project adapter = none
project-specific fine-tuning = false
ALFWorld-specific training = false
```

The model is an off-the-shelf instruction-tuned model. It is not a
pretrained base model, and it is not the historical V3PlannerPhase
adapted policy.

## Meaning of RAW

In `RAW_WITH_MENU_V1`, `RAW` means:

```text
model response
→ strict transport parser
→ environment action
```

No external component may canonicalise, replace, redirect or repair
the parsed action.

`RAW` does not mean that the model lacks general instruction tuning.

## Task manifest

E1 uses:

```text
data/manifests/alfworld_strict_valid_unseen_all134_v1.jsonl
```

The manifest selects tasks and gamefiles only. It does not enable,
disable, filter or truncate admissible commands.

## Decoding

The formal E1 result protocol uses:

```text
temperature = 0.2
top_p = 0.95
max_new_tokens = 128
seeds = [17, 31, 47, 73, 101]
```

These values are frozen before observing E1 outcomes. Temperature
0.2 is a low-variance stochastic protocol, not a tuned optimum.

A temperature-zero engineering smoke may verify infrastructure only.
Smoke results are excluded from E1 statistics and scientific claims.

The vLLM server must use:

```text
--generation-config vllm
```

Every request must explicitly provide temperature, top-p,
max tokens and seed, so model-repository defaults cannot silently
change the evaluation protocol.

## Comparisons

The primary intervention comparison is:

```text
R0 off-the-shelf policy, Harness OFF
versus
R2 identical policy and protocol, Phase-Critical Harness ON
```

The only permitted R0/R2 difference is the registered Harness
intervention.

E0/HIST versus E1/R0 is descriptive, not a single-variable causal
estimate.

## Runtime-core accounting clarification

E1 does not provide free parser or admissibility retries.

Every completed generation consumes one of 60 policy attempts.
Only an exact admissible action consumes one of 30 environment steps.

Stage-1/2 format failure and Stage-3 admissibility failure are separate
outcomes and both count toward the limit of three consecutive nonexecuted
attempts.

The model can see only the frozen `FORMAT_ERROR_V1` or
`INVALID_ACTION_V1` feedback, which is declared runtime assistance and is
held constant across all primary comparison arms.
