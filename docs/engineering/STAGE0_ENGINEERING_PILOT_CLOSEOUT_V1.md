# Stage 0 Engineering Pilot Closeout

Stage 0 is an engineering pilot, not paper efficacy evidence.

Frozen closeout:

- `round_role = PILOT_ENGINEERING_ROUND_V1`
- `round_status = CLOSED`
- `paper_efficacy_evidence = false`
- `paper_performance_claim_authorized = false`
- `promotion_eligible = false`
- `promotion_decision = NOT_APPLICABLE_ENGINEERING_PILOT`
- `paired_cell_count = 85`
- `total_condition_cell_count = 170`
- `parent_success_cells = 0`
- `candidate_success_cells = 0`
- `both_failure_cells = 85`
- `mean_task_success_rate_delta = 0.0`
- `contaminated_valid_unseen_development_task_count = 117`
- `heldout_select_task_count = 17`

The Human T2 diagnostic candidate therefore showed no terminal-success lift on
the held-out 17-task engineering panel. Because both policies were at the floor,
this result is not interpreted as evidence that their internal action
distributions were identical. It is explicitly excluded from paper efficacy
claims.

The durable engineering contribution of Stage 0 is the completed end-to-end
chain:

Evidence / Analyzer / Memory / Research Planner / F0-F1 / training data /
Trainer / frozen policy artifact / Generic SELECT / OFF-OFF evaluation /
immutable attempt publication / crash recovery / paired closeout.

The pilot also exposed and closed runtime and provenance issues that future
clean rounds must inherit as regression requirements:

- exact authority source binding instead of loose artifact discovery;
- Slurm environment/bootstrap independence from shell-local `module`;
- proxy-free loopback HTTP readiness for local model servers;
- generic policy-artifact identity in SELECT traces and episode artifacts;
- immutable started/terminal attempt receipts;
- attempt-ordinal crash recovery;
- published-attempt reload and missing-cell-receipt recovery;
- matched-pair evaluation and closeout sealing.
