# V1233H3 zero-scientific-pair recovery

This package continues the exact accepted causal round only after a durable
`NATIVE_INFRA_OR_PROTOCOL_INVALID_NO_SCIENTIFIC_NO_TRAIN` terminal with zero
scientifically complete pairs.

It does **not** rerun Analyzer or Planner PRE and never top-ups/replaces states.
It first writes a branch/pair failure census from the immutable prior run. It
will automatically retry only when the whole prior paired attempt is safely
recoverable under the frozen matched-pair rule. Missing branch terminals,
identity/replay defects, F0 source-prompt inequivalence and zero-intervention
scientific F1 evidence remain no-retry missingness.

When recovery is eligible, both F0 and F1 are rerun for the matched incomplete
pair in one new operational attempt using the same scientific plan, candidate,
seed and Memory authority. Old evidence remains immutable provenance. H3 allows
only one such automatic paired operational recovery.

A narrow package defect is corrected: F1 intervenes before its first policy
call, so source-prompt parity is not required for an unsent source prompt. If
F1 executes zero intervention steps and calls the policy at the source state,
source-prompt parity is enforced at that actual call. F0 source-prompt parity
remains mandatory.

When execution is authorized, H3 launches the recovery controller detached in a
new operational recovery root. The operator does not need to keep an SSH
session open and must not relaunch H3 while that resident owns the recovery.
