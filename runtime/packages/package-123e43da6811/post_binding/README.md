# Same-call POST recipe adapter — staging implementation

This adapter extends the existing H4.4 POST call with a structured training
recipe. It retains the existing cognitive runtime, logical-call identity,
accepted native POST artifact and no-resend behavior. It does not add a second
Planner or a second provider call.

`source_overlay.adapt_strong_post` requires the exact source SHA and unique
anchors. The adapted prompt and schema become part of the request and runtime
manifest identities. `runtime.validate_post_output` separates the recipe annex
from the original POST artifact and calls the original POST finalizer.
`runtime.adopt_recipe` checks the accepted logical call, contributing successful
attempt, raw provider response and original accepted artifact before publishing
the recipe binding. A recipe written or changed after acceptance is rejected.

NO_TRAIN has a null recipe and needs no training dataset. TRAIN requires a
current dataset context and the native training adapter's validated recipe;
neither test data nor a hand-written receipt supplies execution authority.

## Verified scope

`python -m pytest -q work/v17/post_binding/tests` passed 13 tests on Windows.
Tests use the captured native POST finalizer, logical/attempt contracts and
provider response parser. They cover accepted TRAIN and NO_TRAIN, source drift,
unaccepted calls, identity/hash mismatches, raw response changes and recipe
replacement. They do not invoke a provider, Slurm, a GPU or an environment.

## Integration still required

This directory is staging source. The overlay is not installed in the sealed
V1.6 package or wired into its H4.4 worker. A production caller must derive the
current dataset context and attach this adapter to that original worker.
The current-round producer of verified strategy rows remains unfinished;
this module does not infer missing strategy fields, truncate a short option,
or manufacture a verified target from a POST assertion. Generic Training,
OFF/OFF, Memory publication and resident whole-round dispatch are not completed
by this module. Passing these tests is not a Max-10 launch claim.
