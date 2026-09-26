# Server-First Research Workflow

## Authority

The research server is the authoritative execution environment.

```text
server modification
→ focused test
→ human code review
→ approved execution
→ raw result audit
→ commit and annotated tag
→ server push to GitHub
```

GitHub is used for remote versioning, review, fixed permalinks and
artifact sharing. Experimental source files are not authored directly
through GitHub web edits.

## Default review gates

1. `DESIGN_APPROVED`
2. `CODE_APPROVED`
3. `RESULT_AUDIT_APPROVED`

Additional `EXECUTION_APPROVED` is required for:

- all-task or paper-primary rollout;
- exact/matched F0/F1 execution;
- SFT, preference training or RL;
- changes to frozen task/state inclusion;
- changes to labels or paper-primary statistics.

## Before execution

Record:

- branch, commit and diff;
- config and prompt SHA-256;
- model and tokenizer identifiers/digests;
- task/state manifest and SHA-256;
- seeds and repetition count;
- environment-step and model-call budgets;
- output directory;
- stop and exclusion rules.

## After execution

Audit:

- output completeness;
- task, episode and state counts;
- numerator and denominator of every result;
- parser and invalid-action failures;
- budget equality;
- branch-start/state equality;
- paired repetition validity;
- infrastructure incidents;
- representative benefit, harm, neutral and uncertain cases.

## Git safety

- do not force-push `main`;
- do not rewrite frozen annotated tags;
- do not use broad `git clean` in research worktrees;
- do not commit raw credentials or model access tokens;
- preserve negative results and incident reports.
