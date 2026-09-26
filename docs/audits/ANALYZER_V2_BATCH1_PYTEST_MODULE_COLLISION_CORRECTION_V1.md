# Analyzer V2 Batch-1 pytest module collision correction

```text
STATUS=TEST_COLLECTION_COMPATIBILITY_CORRECTION
PRODUCTION_CODE_CHANGED=false
SCIENTIFIC_CONTRACT_CHANGED=false
PYTEST_GLOBAL_IMPORT_MODE_CHANGED=false
```

The Analyzer Task-2 test was originally named:

`tests/analyzer/test_schema_contract.py`

The repository already contains:

`tests/evaluation/test_schema_contract.py`

The repository test tree is not packaged with `__init__.py`, while pytest's
default `prepend` import mode imports such tests as top-level modules. The
duplicate basename therefore caused an `import file mismatch` during full-suite
collection after Tasks 1–5 were committed.

The correction only renames the newly added Analyzer test to:

`tests/analyzer/test_analyzer_schema_contract.py`

The file content is byte-identical across the rename. No production code,
schema, authority, metric, or validation behavior is changed. The repository's
global pytest import mode remains unchanged.
