# Human Reference Round and Strong Benchmark Isolation V1

## Scientific products

The Human reference round and the strong-model benchmark are independent
scientific products. They may share frozen protocol identities and code, but
never share per-task results or research decisions.

### Human reference round

May consume Formal Analyzer results, Failure Experience, Human/Strong Researcher
shadow records, F0/F1 outcomes, verified training evidence and OFF/OFF policy
evaluation. It must not consume strong-model benchmark task results.

### Strong-model benchmark

May consume only the shared task/interface/environment protocol and the strong
model execution profile. It must not consume Human PRE/POST, repair portfolios,
Analyzer/Memory findings, local training data or local policy task outputs.

## Blinding

During parallel collection, only operational status, completed/failed counts
and aggregate API usage may leave the benchmark operational root. Per-task
requests, responses, actions and trajectories remain in the sealed benchmark
root until the local method and π2 evaluation protocol are frozen.
