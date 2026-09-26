# V1233H4 — replay-report field-drift correction and paired recovery

This is a narrow recovery of the current accepted-PRE causal round. It does
not rerun Analyzer or Planner PRE and does not replace/top-up states.

The live census showed every current branch failed before a scientific outcome
with the exact package-local defect:

`AttributeError: 'SourceStateReplayReportV1' object has no attribute 'exact_match'`

The frozen report contract uses `status`, `failure_code`,
`source_fingerprint_sha256`, and `replay_fingerprint_sha256`. H4 validates
those fields.

Automatic recovery is allowed only for the exact known error with durable
terminals and zero scientific environment-action results, zero policy-call
results, and no option intervention steps. Both arms of each matched pair are
retried together. Unknown AttributeError variants remain fail-closed.

The branch universe is derived from the accepted handoff. Current branch count
is an observation, never a production constant:

`len(planner_selected_source_state_ids) * paired_repetitions_per_state * branch_arms_per_repetition`.

The independent verifier was aligned to the same frozen report schema. It reconstructs the dataclass, validates the report hash, requires PASS/null failure code, and binds both replay fingerprints to the frozen native source fingerprint.


## H4.1 packaging-only correction

H4.1 adds `tests/__init__.py` so the package-local regression suite is an explicit Python package. This prevents an unrelated environment-level `tests` package from shadowing `tests.test_h3_recovery` / `tests.test_verifier` on Python 3.12. Production execution, recovery, verifier, Planner, branch-budget and scientific-authority code is byte-identical to H4 except PACKAGE_IDENTITY/manifest documentation.
