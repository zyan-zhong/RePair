# Strong Researcher PRE Shadow — Hydrated V2

## Purpose

This stage is the Strong-model shadow counterpart of the frozen Human Research
Planner PRE for the Human Reference Round. It is a **controlled pre-outcome
comparison**, not an effect verifier and not a training-authority stage.

The legacy `R-PRE-SHADOW` stage remains preserved as a historical artifact. The
new stage exists because the legacy prompt/schema only consumes the round
evidence package and does not express the full current Research Planner task:
reviewing the complete 30-state A2/A3 universe, constructing a bounded
verification portfolio, and making explicit PRE-outcome risk/value judgments.

## Model-facing input

The provider receives only `STRONG_RESEARCHER_BLIND_PRE_INPUT_V2` plus frozen
identity/gate metadata. The model does **not** receive:

- Human Planner adjudication;
- Human selected 12 source states/candidates;
- Human rationale;
- Human PRE record or its SHA;
- Reference Trace V3 (which intentionally contains Human supervision fields);
- current F0/F1 outcomes;
- future policy-evaluation outcomes;
- Strong benchmark per-task results.

The final blind input contains 9/9 readable evidence slots and explicitly
separates:

- global ALFWorld strict `valid_unseen` 134-task universe;
- current Formal Analyzer MAIN 30-state research cohort;
- PILOT 12-state control cohort.

## Required Strong Research Planner work

The Strong shadow must:

1. review all 30 registered A2/A3 pairs in order;
2. choose one preferred registered arm per state, retaining the alternative;
3. select exactly one principal bottleneck;
4. state one falsifiable hypothesis and one principal scientific change;
5. construct at most a 12-state verification portfolio;
6. preserve the frozen 5 paired repetitions × 2 arms budget;
7. predict expected value and harm risk without assigning environment effect
   labels;
8. explain Memory use as advisory historical evidence;
9. keep exact training-mixture selection on HOLD until a sealed F0/F1 manifest
   exists.

## Authority boundary

The Strong shadow has no Benefit/Harm/Neutral/Uncertain authority. Only the
independent same-state environment verifier may assign effects. It also cannot
promote a policy or start training.

## Output validation

`STRONG_RESEARCHER_PRE_SHADOW_V2` is strict and closed. The semantic finalizer
checks:

- blind/hydration identity binding;
- one selected bottleneck;
- evidence SHA references are from the blind evidence universe;
- all 30 state rows preserve the registered pair order;
- preferred/alternative candidates are exactly the two registered candidates;
- source-state/task-family/Formal-X bindings;
- selected states are unique and ≤ 12;
- selected candidate/source arrays exactly match selected rows;
- A2/A3 counts and branch-run arithmetic;
- Memory has no effect authority;
- training remains HOLD.

## Execution order

The stage may execute only after:

1. final 9/9 Strong blind evidence review passes;
2. the dedicated stage itself passes focused code tests and rendered-request
   leakage audit;
3. Human PRE + 12-state portfolio are frozen;
4. the Human PRE freeze receipt certifies that Human PRE content/hash are hidden
   from the Strong shadow.

The Strong result is then compared with Human PRE at field/state level and the
workflow stops for semantic review **before** any F0/F1 environment execution.
