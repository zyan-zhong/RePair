# Completed observations and limits

| Experiment | Tested states | Stable Benefit | Stable neutral | Uncertain |
|---|---:|---:|---:|---:|
| Development R1 | 11 | 0 | 11 | 0 |
| R2 | 6 | 1 | 5 | 0 |
| R3 | 2 | 0 | 2 | 0 |
| R4 | 1 | 0 | 1 | 0 |
| R5 | 1 | 0 | 1 | 0 |
| Guarded validation, reused R5 | 17 | 0 | 16 | 1 |
| Executable-strategy validation, reused R5 | 5 | 4 | 1 | 0 |

All listed stable neutral effects are joint failures. The changing, selected
portfolios are not a matched ablation or independent draws from one population.

Latest candidate: 4 source states, 8 dual-view examples, 4 passes, 8 updates,
51 action and 2,546 strategy supervised tokens per pass. The accumulation group
uses a common supervised-token denominator; there is no equal per-view loss weight.
TRAIN_SELECT uses 355 tasks × parent/candidate × seed 17, Memory OFF/Harness OFF.
Both solve 3 tasks: 2 shared successes, 1 gain, 1 regression, 351 shared failures.
Mean goal fraction is 0.1084507042 → 0.1070422535. The recorded decision is ROLLBACK.

The native evaluation initially used five seeds through a legacy entry. The
explicit correction keeps complete seed-17 cells for both arms and cancels extra
jobs; the amendment was made after episode publication. No new model episodes
were needed for the correction or goal-metric replay.

The original campaign stopped after five valid rounds under no-promotion patience,
with one infrastructure-invalid attempt and one user-authorized promotion exception.
The later validation's selection is complete; history closeout stopped on
`CLOSED_HISTORY_ATTEMPT_OWNER`. It is not a closed new formal round. No uninterrupted
autonomy, final RePair benchmark superiority, or completed component-ablation result
is claimed. Existing benchmark reference rows are preserved in the manuscript.
