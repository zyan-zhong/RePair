# Executed experiment settings

These settings describe the reported validation. They are not a replacement
launch authority and should not be silently applied to other historical runs.

| Item | Executed setting |
|---|---|
| Policy lineage | Qwen2.5-3B-Instruct with retained parent LoRA adapter |
| Research model | External GPT API; the recent validation records `gpt-5.6-sol` |
| Training-side split | TRAIN_UPDATE 2,843; TRAIN_SELECT 355; TRAIN_AUDIT 355 |
| Final benchmark | 134 unseen and 140 seen; excluded from adaptive research/selection |
| Policy observations | Public goal, observation, eight executed transitions, feedback, full admissible menu |
| Policy output | One JSON object with one string field `action`; exact menu membership |
| Episode budget | 30 environment steps, 60 policy attempts, stop after 3 consecutive nonexecutions |
| F0/F1 repetition | Five paired seeds: 17, 31, 47, 73, 101 |
| Stable Benefit | At least 4/5 valid F0-fail/F1-success pairs and no reverse pair |
| Selection repetition | One paired seed: 17; 355 tasks for each policy |
| Selection assistance | Memory OFF and Harness OFF for parent and candidate |
| Promotion rule | More task successes; ties use mean terminal goal-condition completion; otherwise retain parent |
| Training admission | Stable terminal Benefit only; progress-positive neutral stays research-only |
| Training examples | 4 action views + 4 strategy views from 4 source states |
| LoRA | Rank 16, alpha 32, dropout 0.05, no bias; attention and MLP projections |
| Optimization | AdamW, learning rate 2e-5, weight decay 0.01, gradient clipping 1.0 |
| Schedule | Linear; one warmup step; four passes; eight optimizer updates |
| Batching | Microbatch 1, accumulation 4, one GPU, BF16 |
| Supervision | Assistant completion only; token mean over each accumulation group |
| Sequence length | Maximum 1,248; no truncation, packing or retokenization |
| Randomness | Training/data seed 17; one trained candidate |
| Checkpoint selection | Final step only; no intermediate evaluation |

The machine-readable, executed settings are in
[training_configuration.json](../../paper/evidence/training_configuration.json).
The [reported-validation index](../../experiments/reported_validation/README.md)
links the implementation and records. Original protocol schemas remain in
`configs/`; historical defaults are not evidence that the reported run used them.

## Reuse rules and amendments

The later validations reuse R5 rollout and Analyzer evidence with an unchanged
parent identity; they are not additional formal rounds. Parent selection cells
can only be reused when checkpoint, task, seed, prompt/interface, budgets and
memory/harness identities match. Matching just the model name is insufficient.

A legacy selection entry initially used five seeds. The recorded recovery retained
complete seed-17 cells for both arms and cancelled extra jobs; this amendment
occurred after episode publication. Repair verification kept its five paired seeds.
The five development rounds also include one user-authorized promotion exception.
Both amendments are disclosed in the paper rather than rewritten out of history.

Progress effects P+/P0/P-/PU and efficiency measurements remain separate from
terminal B/H/N/U. A goal-progress tie-break in TRAIN_SELECT does not turn a neutral
F0/F1 repair into Benefit. No hidden environment predicates are sent to the policy.
