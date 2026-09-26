# Reported results and how to check them

Run `python paper/reproduce_results.py` from the repository root. The script
recomputes aggregates from the distributed evidence records; it does not invoke
the provider, simulator or trainer.

| Completed experiment | Source states | Stable Benefit | Neutral failure | Uncertain |
|---|---:|---:|---:|---:|
| Development R1–R5 | 21 | 1 | 20 | 0 |
| Guarded strategy validation | 17 | 0 | 16 | 1 |
| Executable-strategy validation | 5 | 4 | 1 | 0 |

The two validations reuse R5 evidence. Portfolios and implementations changed
sequentially, so these rows are not a matched ablation. The successful executable
programs cover 2, 4, 6 and 4 actions; all 20 successful F1 branches require zero
subsequent policy calls.

The update supplies four initial-action targets and four strategy targets, not
stepwise supervision of all sixteen program action positions. Per pass it has
51 action-view and 2,546 strategy-view loss-bearing tokens. Four passes produce
10,388 supervised-token exposures and eight optimizer updates.

| TRAIN_SELECT, seed 17, OFF/OFF | Parent | Candidate |
|---|---:|---:|
| Task successes | 3/355 | 3/355 |
| Mean goal-condition completion | 10.845% | 10.704% |
| Consecutive-nonexecution terminations | 261 | 252 |
| Budget-exhausted tasks | 91 | 100 |
| Out-of-menu calls | 1,556 | 1,612 |

Task pairing gives 2 shared successes, 1 gain, 1 regression and 351 shared failures.
Goal completion improves on 5 tasks, worsens on 6 and ties on 344. The registered
decision is **ROLLBACK / retain parent**.

## Evidence map

| Claim or quantity | Distributed record |
|---|---|
| Development rounds | [development_rounds.json](../../paper/evidence/development_rounds.json) |
| Latest causal states and branches | [causal_states.json](../../paper/evidence/causal_states.json) |
| Parent/candidate task pairs | [selection_pairs.json](../../paper/evidence/selection_pairs.json) |
| Native supervision count | [native_label_counts.json](../../paper/evidence/native_label_counts.json) |
| Verified versus taught action coverage | [supervision_coverage.json](../../paper/evidence/supervision_coverage.json) |
| Training hyperparameters and identities | [training_configuration.json](../../paper/evidence/training_configuration.json) |
| Source checksums | [source_provenance.json](../../paper/evidence/source_provenance.json) |

## What is not established

The final RePair 134-unseen/140-seen evaluation and matched action-only, filtering,
equal-compute, memory and hierarchy controls are incomplete. The reference
checkpoint benchmark tables in the appendix are external context. There is one
training run and one paired selection seed; we do not claim statistical significance
or seed robustness. Full provider cost is not reconciled.

The Max-10 development campaign stopped after five valid rounds under patience,
with one infrastructure-invalid attempt and a promotion exception. Engineering
recoveries occurred. The later validation completed training and selection but
hit an ownership check during history closeout. It is not a closed new formal
round or a demonstration of uninterrupted unattended operation.
