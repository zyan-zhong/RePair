# PCHSI receipt-driven full-round driver V1.1

## Scope

This package adds only a thin control plane. It does not reimplement rollout, Memory, Analyzer, Research Planner, F0/F1, verifier, training, acceptance, or promotion logic.

The process standard is bounded, not infinite:

`pi_k -> rollout(policy Memory view) -> evidence freeze -> Analyzer(Analyzer Memory view) -> Planner PRE(Planner Memory view) -> same-state F0/F1 -> independent verifier -> Planner POST -> Memory maintenance -> train/no-train -> optional training -> Memory OFF/Harness OFF acceptance -> promote/rollback -> outer-loop stop governance -> {terminal stop | next-round transition}`

The active outer-loop governance must preserve the previously frozen Strong-primary semantics: at most 10 scientifically valid round attempts, stop after 3 consecutive scientifically valid no-promotion attempts, apply the other frozen abstention/verified-benefit/I1-label/acceptance/resource/protocol stop conditions where applicable, do not count invalid infrastructure/protocol attempts as scientific no-improvement, and never use the sealed paper benchmark as loop feedback.

A full round is considered deployable only when every gate has an exact command binding and a machine-verifiable terminal receipt.

## Safety / resume semantics

- Existing valid child terminal receipt: reuse, do not execute again.
- Driver `started.json` exists but no valid child terminal receipt: stop as `PARTIAL_UNSAFE_GATE`; no blind resend.
- Unbound gate: fail during preflight, before side effects.
- Commands are argv arrays executed with `subprocess.run(..., shell=False)`; no `eval`, no shell command-string construction.
- The driver records only control-plane receipts and SHA-256 identities. Stage-specific scientific ledgers remain authoritative.
- Child stages own provider/environment ambiguity and retry semantics. This driver does not add transport retries.

## Round-1 Analyzer-tail bound plan

After deploying `STRONG_PRIMARY_ROUND1_ANALYZER_TAIL_AUTORUN_V1_1` at the frozen server path:

```bash
export ROUND1_REPO="/data/run01/scwb204/sdar_repro/badcase/github_exports/pchsi-wt-strong-primary-takeover-prep-v1"
export DRIVER_STATE="/data/run01/scwb204/sdar_repro/badcase/new_human_pi1/control/full_round_driver_v1_1/STRONG-PRIMARY-R1-PI0-I1"

bash ./RUN_FULL_ROUND.sh \
  --plan ./plans/ROUND1_ANALYZER_TAIL_BOUND_V1.json \
  --state-root "$DRIVER_STATE" \
  --repo "$ROUND1_REPO" \
  --preflight-only
```

Remove `--preflight-only` only after preflight passes.

V1.1 uses a distinct state root from V1 because `plan_binding.json` is immutable and the corrected process-standard metadata changes the plan SHA. Do not reuse a V1 state root if V1 preflight/execution has already written a plan binding there.

## Full-loop template

`plans/CANONICAL_PI_K_TO_NEXT_ROUND_STANDARD_V1.json` defines the required bounded end-to-end gate sequence, including `OUTER_LOOP_STOP_GOVERNANCE` before any next-round transition. It intentionally fails closed because exact Round-1 downstream bindings have not yet been certified. See `ROUND1_AUTONOMY_BINDING_GAP_LEDGER_V1.md`.
