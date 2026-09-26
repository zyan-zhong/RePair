# Reproduction guide

## 1. Recount the paper (CPU, no network)

```bash
python paper/reproduce_results.py
python tools/verify_registered_sources.py
python tools/verify_release.py
```

The first command reads numerical evidence, the second checks registered source
hashes with explicit private-file exclusions, and the third checks the public
release inventory. None grants execution authority or starts training.

## 2. Exercise the implementation (Linux, no GPU/API)

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest tests -q
python tools/test_current_strategy.py
```

The strategy helper resolves the native H44 test dependency from the exact source
index. It does not scan the server or choose a package by modification time.
Run each historical package separately if investigating that version. Some sealed
historical tests need private fixtures explicitly omitted from the public export.
The source tree includes older closed implementation candidates; their refusal to
launch is intentional. See [runtime guide](../../runtime/README.md).

## 3. Build the manuscript

```bash
python paper/build.py
python paper/verify_manuscript.py
```

Requires TeX Live/BibTeX and `pypdf` for inspection. `paper/RePair.pdf` is the
distributed v4.3 paper; a local build writes `paper/main.pdf`. The original ICLR
style files and paper source checksums are retained.

## Live execution

The release contains the scientific programs and executed configuration, but
not the parent adapter, simulator installation, complete source-state bundles,
credentials or a universal scheduler deployment. A clean clone is sufficient for
the checks above; reproducing GPU/API episodes requires the external assets
listed in [Installation](INSTALLATION.md).

The original one-validation entry is
`runtime/packages/MAX10_V2_1_1_EXECUTABLE_PLANNER_VALIDATION-0c20fc82ebc2/entry_v208.py`.
It exposes `--preflight`, `--run` and `--preflight-and-run`. The archived `RUN.sh`
resolves its interpreter from `AUTHORITY.json`. The original server also used a
deployment-generated `RUN_REGISTERED_ENVIRONMENT.sh`; that generated wrapper is
not part of the immutable package exported here. The package authority
references earlier packages, the exact parent, R5 evidence and deployment assets.
These original references are preserved, not rewritten to pretend a new machine
is equivalent. Its `VERIFY.py` validates the original sealed package, while the
public root-level verifier checks the published subset.

On the original registered deployment, use its registered wrapper with
`--preflight` before an authorized run. Preflight performs no provider request.
For a new deployment, materialize typed bindings for the local assets and verify
their identities with the existing contracts. Do not copy the historical
`AUTHORITY.json` and replace a path without updating its dependent hash bindings.
No new deployment binding is silently inferred by this release.

Operator shells must not enable `set -e`, `set -u` or `pipefail`. When a registered
entry is piped through `tee`, capture the producing exit status immediately:

```bash
# REGISTERED_ENTRY and RUN_LOG are supplied by the deployment binding.
bash "$REGISTERED_ENTRY" --preflight 2>&1 | tee "$RUN_LOG"
run_rc=${PIPESTATUS[0]}
printf 'PREFLIGHT_RC=%s\n' "$run_rc"
```

The current progress window source is indexed under role `progress_window` in
[COMPONENT_INDEX.json](../../runtime/COMPONENT_INDEX.json). It reports registered
receipts and job state; it is not a second campaign controller.

The publication does not resume a stopped campaign, create API calls, submit GPU
jobs, force a promotion, or change the scientific evidence.
