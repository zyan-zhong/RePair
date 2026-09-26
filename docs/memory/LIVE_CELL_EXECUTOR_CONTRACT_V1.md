# Failure Memory Live Cell Executor Contract V1

The executable is invoked as:

```text
<executor>
  --execution-manifest <absolute path>
  --cell-manifest <absolute path>
  --cell-index <zero-based integer>
  --output-dir <new non-existing cell directory>
```

It must create exactly these scientific files, plus operational logs if needed:

```text
CELL_SCIENTIFIC_RESULT_V1.json
CELL_TERMINAL_RECEIPT_V1.json
POLICY_MEMORY_PACK_V1.json
ANALYZER_MEMORY_PACK_V1.json
RESEARCHER_MEMORY_PACK_V1.json
```

The result is purely mechanical and must conform to
`FAILURE_MEMORY_CELL_SCIENTIFIC_RESULT_V1`.  It may not contain Q1--Q5,
SUPPORTED/NOT_SUPPORTED decisions, free-form scientific claims, or post-hoc
thresholds.  The receipt must bind the result self hash and execution-manifest
identity.  Each role pack binds `cell_id` and `execution_manifest_sha256`, so identical payload bytes in different cells cannot alias scientific identity. All files are canonical JSON, no-clobber and content addressed.

The executor must preserve the registered policy/runtime/environment/panel/
schedule/snapshot identities.  A different identity requires a new execution
manifest.  Infrastructure failures must not be converted into policy failure.
