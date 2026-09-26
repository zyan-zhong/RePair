# RePair: From Plausible Repairs to Policy Capability

RePair studies a concrete question: **when does a useful correction become a
lesson that improves the policy itself?** A research model proposes repairs;
paired environment tests measure their effects; verified evidence supplies
action and strategy supervision; evaluation removes research memory and repair
interventions before comparing the updated policy with its parent.

This is the public research code and experiment release accompanying the
[manuscript](paper/RePair.pdf). It includes the framework, experiment programs,
registered runtime snapshots, configurations, prompts, tests, and numerical
records. [中文阅读入口](docs/README_zh.md).

## What the completed study shows

The later executable-strategy validation finds **4 stable beneficial repairs
among 5 selected source states**. All 20 successful intervention branches finish
inside the repair programs. An update on 8 dual-view examples leaves independent
TRAIN_SELECT success at **3/355 → 3/355**, with one gain and one regression.
The selection rule retains the parent. These are diagnostic findings, not a claim
of improved final benchmark performance or a completed ten-round campaign.

## Reproduce the reported numbers first

Python 3.12; no model, API key, simulator, or GPU is needed:

```bash
git clone https://github.com/zyan-zhong/RePair.git
cd RePair
python paper/reproduce_results.py
python tools/verify_registered_sources.py
python tools/verify_release.py
```

The recount checks the 355 paired selection records, causal outcomes, native
supervision counts, and training configuration. It does not rerun model inference.
Expected headline results and their precise scope are in
[Results](docs/repair/RESULTS.md).

## Run the code checks

Use Linux and Python 3.12 for the complete suite (the controller uses POSIX locks):

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e . -r requirements-dev.txt
make -C native/s1_backend_probe all
python tools/test_public_framework.py
python tools/test_current_strategy.py
```

The current strategy suite and numerical/source checks also run on Windows.
The public framework suite excludes two explicitly listed checks of private
historical evidence and Git history; their original test files remain unchanged.
See [public test scope](runtime/PUBLIC_TEST_SCOPE.json).
Historical runtime packages have their own tests and must be tested separately
because module names overlap. [Validation records](docs/repair/validation/README.md)
distinguish executed checks from full GPU/API campaign reproduction.

## Read or use the framework

| Start here | What it explains |
|---|---|
| [Method and code map](docs/repair/METHOD.md) | Analyzer, Planner, causal verification, Dual-View, memory and round ownership |
| [Installation](docs/repair/INSTALLATION.md) | CPU checks, observed runtime versions and external assets |
| [Experiment settings](docs/repair/EXPERIMENTS.md) | Data splits, models, seeds, budgets, training and selection rules |
| [Reproduction guide](docs/repair/REPRODUCIBILITY.md) | Offline recount, tests, manuscript build and live deployment boundaries |
| [Reported validation](experiments/reported_validation/README.md) | Direct links to the programs and settings behind the paper |
| [Runtime source guide](runtime/README.md) | How exact deployed snapshots relate to the maintained framework |
| [Results and limitations](docs/repair/RESULTS.md) | Completed measurements, missing controls and candidate rollback |
| [Review materials](docs/repair/REVIEW_MATERIALS.md) | Anonymous submission versus this account-owned public repository |

## Repository layout

| Directory | Contents |
|---|---|
| `src/pchsi/` | Analyzer, cognitive runtime, research planning, memory, evaluation and round control |
| `scripts/`, `native/` | Existing experiment, native worker and training programs |
| `configs/`, `prompts/` | Scientific contracts, schemas and role prompts |
| `experiments/` | Experiment manifests and the reported-validation reading map |
| `data/manifests/` | Distributed task identities; simulator data are external |
| `runtime/packages/` | 21 registered deployment snapshots with original source hashes |
| `runtime/registered_sources/` | Additional exact training-binding sources |
| `paper/` | v4.3 manuscript, figures, numerical evidence and standard-library recount |
| `tests/`, `tools/` | Framework tests and release/source verification |
| `docs/repair/` | Current release documentation; other documentation records historical stages |

The registered-source verifier explicitly reports withheld private history and
Git fixtures. Scientific runtime files are preserved byte for byte; the public
release is not a new production execution authority. Older design documents and
closed candidate launchers remain historical records, not instructions to bypass
the registered runtime. See [provenance](docs/repair/PROVENANCE.md).

The final 134 unseen / 140 seen benchmark is separate from TRAIN_SELECT. Final
RePair benchmark results and matched component ablations are not available.
Model weights, simulator assets and credentials are not distributed here.
See [rights and third-party components](NOTICE.md).
