# Registered runtime sources

The maintained framework lives in `src/pchsi/`; the paper's deployed behavior also
depends on the exact packages in this directory. These are immutable source
snapshots, not twenty-one independent methods and not a version menu for users.

- [COMPONENT_INDEX.json](COMPONENT_INDEX.json) maps scientific roles to exact
  local snapshots. It is a reading/test map, not production launch authority.
- [REGISTERED_SOURCE_INDEX.json](REGISTERED_SOURCE_INDEX.json) retains the source
  origins, package manifests, member hashes and additional training sources.
- [REVIEW_TEST_BINDING.json](REVIEW_TEST_BINDING.json) identifies the current
  strategy package for offline tests.
- [PUBLIC_EXPORT.json](PUBLIC_EXPORT.json) lists private-history/Git fixtures
  omitted from this public source release, with their original checksums.
- [ENVIRONMENT_OBSERVED.json](ENVIRONMENT_OBSERVED.json) records observed package
  versions in the registered Python environment at publication time.

Every included scientific source file is byte-preserved. Original package
manifests are also preserved and consequently still describe explicitly omitted
private members. `python tools/verify_registered_sources.py` checks this relation
and reports both present and omitted counts; it never calls the subset a complete
historical execution bundle. The root release inventory separately covers the
publication documents and helpers.

## Reading order

Start with `strategy_planner.py`, `guarded_strategy.py`, `cue_strategy.py`,
`strategy_worker.py` and `strategy_hooks.py` in the indexed strategy package.
`entry_v208.py` and `one_validation.py` show the existing PRE → F0/F1 → POST →
conditional training → selection integration. The native H44 source is under
`packages/package-123e43da6811/reuse/h44/`. The campaign and registered training
bindings are in the same core package. Additional trainer sources are in
`registered_sources/`, with their exact roles in the original source index.

The V194 and single-seed recovery snapshots document selection and parent reuse;
V196 records memory/token budgets; V204 records the richer feedback connection;
V205 records two-source analysis concurrency; V206 records lossless PRE pooling;
V212 supplies the terminal progress window. Their names are historical provenance,
not settings that should be chosen by sorting version strings.

Absolute source paths are historical deployment identities. Never run an archived
shell entry merely because it is present. See
[Reproduction](../docs/repair/REPRODUCIBILITY.md#live-execution) for external assets
and the difference between offline tests and a rebound live deployment.
