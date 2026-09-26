# Source provenance and publication scope

The maintained framework is exported from source commit
`bba400738a7a53d0402552ecc3576f736ca0eec8`. The runtime export adds 21 registered
packages and individually registered training bindings. The source index gives
their original SHA-256 values; no recursive server discovery was used for this
publication. The new public repository keeps its own independent Git history.

Scientific source files are copied unchanged. Release changes are confined to
documentation, the public subset verifier, inventory/check helpers, CI and paper
packaging. The v4.3 manuscript and evidence replace the stale draft in the earlier
preparation directory.

The original append-only status ledger remains private and unchanged. Publication
omits private canonical ledgers, embedded Git objects and two sealed historical
integration-fixture archives. [PUBLIC_EXPORT.json](../../runtime/PUBLIC_EXPORT.json)
lists each exclusion with its checksum and reason. Exclusion does not revoke or
rewrite the corresponding historical evidence. Some old standalone package VERIFY
commands require those private fixtures; the public verification entry accounts
for the exact subset transparently.

The release retains original scientific settings, source hashes and numerical
outcomes. It neither grants new execution authority nor certifies a portable
end-to-end GPU reproduction. Historical design documents under other `docs/`
folders describe the state at their own dates. Current claims and measured limits
are consolidated in [Results](RESULTS.md) and the paper.
