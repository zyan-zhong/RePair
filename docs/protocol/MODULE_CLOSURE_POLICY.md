# Module Closure and Major-Module Ledger Policy

## Purpose

Research work must be closed, documented, committed and pushed at the
small-module boundary rather than accumulated until the end of a large
work package.

## Small-module closure

A small module is CLOSED only after all applicable items are complete:

1. implementation / audit / analysis is finished;
2. required tests or deterministic audits pass;
3. authoritative outputs are identified;
4. evidence and SHA-256 identities are recorded;
5. the parent major-module Markdown ledger is updated;
6. the module forms a single-purpose Git commit;
7. the commit is pushed to the remote branch;
8. local HEAD and remote branch HEAD are verified identical;
9. the worktree is clean.

The next scientific small module must not begin before this closure is
complete, unless an explicitly recorded incident requires otherwise.

## Major-module ledger

Every major work package maintains one canonical Markdown ledger.

The ledger is updated after every completed small module and records:

- research or audit question;
- frozen inputs and constraints;
- files or artifacts involved;
- execution or audit commands;
- tests and audit results;
- numerators, denominators and key counts;
- SHA-256 identities;
- source/package/code identities;
- incidents and unresolved limitations;
- conclusion boundary;
- next small module.

The closure commit containing a ledger block is identified through Git
history rather than embedding its own commit SHA in the same commit.

## Commit scope

One completed small module should normally correspond to one
single-purpose commit.

Unrelated completed modules must not be bundled into a final catch-all
commit.

## Major-module completion

A major module may receive a final integrated audit, seal, tag or merge
after its internal small modules are closed.

The final major-module seal does not replace individual small-module
closure evidence.

## Documentation Sync Check

Every small-module closure must explicitly check the documentation
surfaces that can be affected by that work.

When applicable, the check covers:

- parent major-module ledger;
- Round-1 README;
- Component Registry;
- Asset Registry;
- Hierarchical Analysis Ledger;
- Experiment Ledger;
- Code Map;
- root README.

Each checked document receives exactly one state:

```text
UPDATED
CHECKED_NO_CHANGE_REQUIRED
NOT_APPLICABLE
```

The check follows these rules:

- documentation synchronization does not authorize changing a
  scientific result;
- higher-level documentation may not override lower-level raw evidence,
  original manifests, seals or deterministic audits;
- repository-relative Markdown links introduced or modified by the
  module must resolve;
- a scientific module that changes an experiment or research status
  must synchronize the Experiment Ledger;
- a change to top-level project status must synchronize the root README;
- a component-role or authority change must synchronize the relevant
  component registry;
- an exact historical asset identity or retention change must
  synchronize the relevant asset registry.

The Documentation Sync Check is additional to, not a replacement for,
the existing requirements for deterministic audit, a single-purpose
commit, push, remote-HEAD equality and a clean worktree.
