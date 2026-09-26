# Validation records

The current release checks the explicit public source subset, recomputes paper
aggregates, runs the framework suite on Linux and runs the current strategy suite
separately. Executed checks are recorded with commands, exit status and counts.
Source integrity and passing software tests do not establish policy improvement.

The public framework command is `python tools/test_public_framework.py`, after
`make -C native/s1_backend_probe all`. It explicitly deselects two original
provenance tests requiring the private B0/A9 server assets and an old private Git
commit. Their unmodified tests remain in the tree, and every other framework test
is retained. `runtime/PUBLIC_TEST_SCOPE.json` records the exact node IDs and reasons.

`LINUX_BASELINE_TESTS.json` is the earlier 1,998-test result on the base scientific
checkout, retained as historical evidence. `LINUX_PUBLIC_VALIDATION.json` records
the fresh extracted public source check when present. The release GitHub Actions
workflow exercises the same commands in a clean Python environment without
provider credentials or a GPU.

`PAPER_FINAL_VERIFICATION.json` records the v4.3 paper delivery checks. Historical
v4.2 validation is retained under an explicitly historical filename. The paper is
9 main-text pages and 22 pages including statements, references and appendix.

The public package deliberately excludes private ledgers and embedded Git fixtures.
The registered-source check reports their absence explicitly; standalone historical
tests that require those files are outside the public test claim. The current
release does not test a full GPU/API campaign on a newly configured machine.
