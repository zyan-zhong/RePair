# E0 Minimal Historical V7B.3c Audit

## Purpose

E0 preserves the historical system as a reference without allowing it
to block the raw-policy research line.

## Questions

1. What model, adapter, prompt and action menu did the policy receive?
2. Which action transformations occurred after model output?
3. What information was visible to the policy versus historical
   controllers?
4. How were success, termination and the 30-step budget defined?
5. Which historical headline numbers can be reproduced from source
   code, job logs and raw JSONL?
6. Which model/checkpoint provenance remains incomplete?

## Minimum action pipeline

```text
raw model response
→ historical parser
→ historical phase controller
→ historical action guard, executed or skipped
→ final action sent to environment
```

## Known information asymmetry to verify

Historical evidence indicates:

- policy prompt displayed at most the first 200 commands;
- parser and controllers used the full environment list.

This is prohibited in v3.1 and must be documented as a historical
limitation.

## Required outputs

- project and artifact inventory;
- minimal historical code map;
- action-source summary;
- environment/control-variable table;
- headline-number reproduction table;
- representative untouched, parser-touched, phase-touched,
  guard-touched and unresolved cases;
- checkpoint-provenance limitations.

## Non-goals

E0 will not:

- infer raw-model terminal performance;
- produce causal controller contribution estimates;
- build L2–L4 historical event profiles;
- train or select a new controller;
- delay E1 after the minimum boundary and number checks are complete.

## Exit condition

E0 passes when each retained historical claim has matching:

```text
frozen code
+ execution/log evidence
+ raw output/statistical reproduction
```

Unresolved claims remain explicitly unresolved rather than guessed.

## Fresh5 system boundary

The five frozen all134 files are:

```text
jobs = [112018, 112021, 112022, 112025, 112128]
tasks = 134
episodes = 670
successes = 501
failures = 169
```

They are historical V7B.3c composite-agent replications.
They include the project LoRA, historical parser, phase controller,
action guard and task-specific rewrites.

They must not be presented as E1 trajectories or as the independent
capability of an off-the-shelf instruction model.
