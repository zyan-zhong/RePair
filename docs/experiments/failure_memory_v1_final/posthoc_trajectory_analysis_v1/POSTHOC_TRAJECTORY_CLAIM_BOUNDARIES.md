# Post-hoc Trajectory Analysis Claim Boundaries

- This is a post-hoc descriptive analysis over sealed Memory V1 artifacts.
- It cannot change Q1, Q2, or Q3 from their registered dispositions.
- It cannot create Benefit, Harm, Neutral, or Uncertain causal labels.
- `model_calls` and `environment_steps` are process-efficiency proxies, not task success.
- Step-level repeat/loop/divergence metrics are reported only when a trustworthy
  action sequence is discoverable in sealed evidence.
- Missing traces remain missing; no action sequence is reconstructed from Memory
  payloads, paper narratives, or model speculation.
- Cells with `memory_exposed=0` cannot support causal statements that Memory changed
  their trajectories.
- Stage 2/3 zero-coverage results must not be reframed as evidence of safe or
  efficient Memory use.
- Findings may motivate Q4 Analyzer/Verifier hypotheses, but Q4 still requires
  separately implemented and same-state verified experiments.
- Q5 still requires real training followed by Memory-OFF + Harness-OFF evaluation.
