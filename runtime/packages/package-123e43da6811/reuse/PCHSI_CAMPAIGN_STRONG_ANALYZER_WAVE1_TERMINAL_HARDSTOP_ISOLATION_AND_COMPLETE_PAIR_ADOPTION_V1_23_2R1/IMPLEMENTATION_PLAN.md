# V1232R1 Implementation Plan

## Root incident
V1232R stopped on `Q_WAVE_HAS_HARD_STOP`. This guard was stricter than the previously frozen Analyzer missingness governance. The Q execution manifest is already full-registry (60/60), so the frozen `run_registry_v1.py` break-on-hard-stop contract implies any hard-stop row must be the final executed frozen unit.

## Machine reconciliation
1. Load Q wave terminal, registry, and full execution manifest.
2. Recompute hard-stop rows and require exact agreement with `hard_stop_count`.
3. Require exactly one hard stop, at the final execution row, bound to the final registry unit.
4. Load its durable `logical_call.json`, `attempt_000.json`, and `method_result.json`; require no-retry / frozen-runtime-policy semantics and a terminal hard-stop receipt.
5. Require the hard-stop source is not a complete A0+A1 pair.
6. Preserve the hard-stop source as censored/quarantined provenance; do not replay it.
7. Adopt only A0=ACCEPTED + A1=ACCEPTED complete pairs.
8. Reuse canonical `load_attempt_directory_v1`, `build_group_signature_binding`, `select_dev_source_call`, `build_group_manifests`, and `build_group_synthesis_inputs`.
9. Materialize the full deterministic group universe and source-closed subset.

## Frozen governance
- Strong local logical-call reexecution: 0
- automatic retry: 0
- replacement source: 0
- top-up: 0
- resource-budget expansion: false
- outcome-adaptive selection: false
- Human disposition: false

A terminal hard stop does not retroactively invalidate independently completed ACCEPTED calls; it only stops later calls. This package proceeds only because Q has a full-registry terminal manifest and therefore there are no unexecuted later calls.
