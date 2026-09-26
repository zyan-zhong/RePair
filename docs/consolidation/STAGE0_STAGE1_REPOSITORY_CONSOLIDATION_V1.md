# Stage 0 + Stage 1 Repository Consolidation V1

This consolidation checkpoint is created after:

- Stage 0 Human engineering pilot closeout;
- Generic SELECT policy/runtime/artifact compatibility closure;
- immutable attempt / crash-recovery closure;
- Stage 1 Generic Round Automation Control Plane PASS.

The repository consolidation has two new commit layers on top of the existing
research-intelligence lineage.

## Commit A — Stage 0 and data-plane engineering assets

Contains:

- Generic SELECT Stage 0 code already present in the worktree;
- final source snapshots of the reusable data-plane, training, evaluation, and
  Stage 0 packages;
- Stage 0 engineering closeout documentation;
- clean-data and round-data-plane documentation.

Failed intermediate patch releases are not duplicated as source snapshots.
Their evidence remains in the external experiment/archive roots.

## Commit B — Stage 1 generic round control plane

Contains:

- `pchsi.round_control`;
- Stage 1 round-control tests and design documents;
- final Stage 1 package-source snapshot;
- repository consolidation manifest.

## Excluded from Git

The consolidation deliberately excludes:

- model weights and adapters;
- checkpoints;
- `.safetensors`, `.pt`, `.pth`, `.bin`, `.ckpt`;
- ZIP review bundles;
- runtime logs;
- ALFWorld trajectories and attempt directories;
- generated review/output directories;
- build caches.

External scientific and engineering evidence is referenced by frozen SHA-256
identity instead of copied into Git.

## Push policy

The driver requires:

1. exact detached source HEAD;
2. exact expected worktree changed-path set;
3. remote `main` to be an ancestor of the local lineage;
4. no unexpected untracked files;
5. no prohibited large/binary assets in the commit;
6. focused and full repository regression PASS;
7. `git diff --check` PASS;
8. two clean commits;
9. atomic push of both `main` and an archive branch.

No force push is used.
