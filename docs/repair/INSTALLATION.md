# Installation and external assets

## Numerical reproduction

Python 3.12 and its standard library are sufficient for
`python paper/reproduce_results.py`. No API calls, model weights or GPU are used.
Source verification has the same requirements.

On Windows, the historical snapshot names need Git long-path support. Clone into
a short directory and enable the repository setting at clone time:

```powershell
git clone -c core.longpaths=true https://github.com/zyan-zhong/RePair.git RePair
```

The scientific snapshot paths are preserved for hash/provenance consistency.

## Framework tests

On Linux, create a Python 3.12 virtual environment and run:

```bash
python -m pip install -e . -r requirements-dev.txt
python -m pytest tests -q
python tools/test_current_strategy.py
```

The editable installation makes subprocess imports resolve the same source tree.
Do not collect every historical package into one pytest invocation: different
snapshots deliberately reuse module names. Windows supports numerical checks and
the current strategy suite; complete controller tests require POSIX `fcntl`.

## Scientific runtime

[ENVIRONMENT_OBSERVED.json](../../runtime/ENVIRONMENT_OBSERVED.json) records the
registered environment observed at release: Python 3.12.13, PyTorch 2.8.0,
Transformers 4.57.3, PEFT 0.19.1, ALFWorld 0.4.2 and TextWorld 1.7.0, among other
packages. It is an observed version inventory, not a complete reproducible
container or a claim that all historical runs used an unchanged environment.
The registered operator setup loads CUDA 12.4. Match the driver and PyTorch
runtime to the selected GPU deployment before training.

External prerequisites are:

- ALFWorld/TextWorld installation and licensed gamefiles, including the frozen
  task manifests and exact source-state restoration artifacts for a live rerun.
- Qwen2.5-3B-Instruct at the revision in the
  [training configuration](../../paper/evidence/training_configuration.json),
  plus the specific retained parent adapter. Parent/candidate adapter hashes
  are recorded; the adapter weights themselves are not in this release.
- A GPU for native LoRA training and policy service. The original deployment
  uses Slurm; the released numerical check does not need a scheduler.
- Credentials supplied through the deployment's secret loader for external
  research-model requests. Never place credential values in configs or commits.
- Typed bindings for the local interpreter, models, task lists, environment,
  provider, source packages, output directory and scheduler.

Configure these assets through the existing runtime contracts. Original absolute
paths in immutable snapshots document the executed deployment; changing those
strings alone is not a verified portable deployment. See
[the live-run boundary](REPRODUCIBILITY.md#live-execution).

## Manuscript build

Install TeX Live (including the packages in `paper/main.tex`) and BibTeX, then
run `python paper/build.py`. For manuscript inspection install `pypdf`, then run
`python paper/verify_manuscript.py`.
