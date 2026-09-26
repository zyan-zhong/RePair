# From Plausible Repairs to Policy Capability

Anonymous manuscript source, revision 4.3.

The main text is 9 pages. Statements and references follow it; the appendix
follows references. Use the full PDF for submission, not the 9-page reading extract.

## Build

Install a current TeX Live distribution with the packages requested in main.tex.
Run `python build.py` (cross-platform), or `bash build.sh`. The entry is `main.tex`.
The ICLR 2027 style files are unchanged and matched to the official download.

To check the compiled manuscript, install `pypdf` and run
`python verify_manuscript.py`. To recompute numerical results, run
`python reproduce_results.py`; it uses only the Python standard library.

## Evidence scope

The evidence directory contains 355 paired TRAIN_SELECT task records,
50 branch summaries from five intervention states, the training configuration,
native supervision counts, and development-round summaries. These support
recounting the reported aggregates. They do not include model weights, full
environment snapshots, or an independent GPU/API rerun of the campaign.

All final benchmark numbers for external methods are preserved from the
supplied frozen benchmark tables. RePair's final unseen/seen results and
matched component ablations have not been completed; the paper makes no claim
of benchmark superiority or improvement from the strategy objective alone.
The latest candidate ties its parent at 3/355 selection successes and is rejected.

The source archive omits private machine paths, credentials, Git history, and
internal editorial notes. Third-party style files and dependencies retain
their respective licensing terms.
