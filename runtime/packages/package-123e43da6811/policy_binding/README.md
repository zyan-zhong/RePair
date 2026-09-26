# Accepted candidate runtime publication

`entry.candidate_runtime.publish_candidate(start, current_inputs_ref, trained,
output_root, source_registration)` is a keyword-only internal API. It returns
`parent_ref`, `candidate_ref`, `next_policy_input_refs`, `current_parent_context`
and `result_ref`, using exact `{path, sha256}` references. The next-policy map has
exactly `runtime`, `profile`, `policy_launch_authority`, and `engine_profile`.
Publishing these objects is not promotion and starts no model service.

The registration is the full Analyzer binding's source registration structure:
`scientific_repo_root`, `source_registration`, `training_source_registration`,
plus `rollout_capsule_ref`. The entry derives the latter from the registered
READY authority's capsule path/SHA, not a directory search. Only three fixed
`policy_runtime_lifecycle_source/` members of that exact ZIP are loaded: the
original engine builder, engine receipt validator, and launch validator.

The publisher calls the actual accepted-output reader, which rechecks native
receipt/index/authorization/contract domains and the original training output
file map. The candidate identity binds the native adapter bundle; the current
request and execution attempt must match. It preserves the actual optimizer
output's final trainable-parameter identity and continuation context. A resumed
publication accepts only identical output bytes.

The candidate runtime schema is `CURRENT_TRAINED_POLICY_RUNTIME_BINDING_V1`.
It retains the current base path, tokenizer, chat template, decoding, context,
I1 continuation and endpoint configuration; adds the actual adapter path,
bundle, native rank, artifact manifest and accepted-training references; and
uses a deterministic request/adapter-bound candidate label. The separate base
service alias prevents an adapter request from silently addressing the base.
The engine profile and resource choices stay registered values.

The original runtime launch builder produces only a base command. The small
`launch.extend_lora_launch` adapter adds the same native LoRA CLI form used by
`scripts/memory/run_memory_final_gpu_job_v1.py`: `--enable-lora`, the actual
`--max-lora-rank`, and `--lora-modules name=actual_adapter_path`. It checks the
entire finite adapter file map, including weight bytes, before constructing the
launch. It then recomputes the original launch command and contract hashes and
runs the original launch validator. It does not merge weights or synthesize an
adapter. Rollout's existing shard worker executes this published command.

For H4.4, call `policy_binding.h44_overlay.configure_h44_workers(h44_root)` in the
existing H4.4 entry before importing its vendor module. The already-installed
Memory worker bootstrap transports the exact H4.4 root to child interpreters.
The hook accepts only the registered vendor module SHA `b72888cd...baa44a4d` and
wraps its original launch builder. The actual `gpu_job.py::run_allocation` call
therefore applies the same trained-LoRA extension, including when H4.4 chooses
an allocation-local port. Base runtime calls return the original launch
unchanged. No controller, GPU worker or immutable vendor source is edited.

The OFF/OFF owner consumes the published policy refs and original native
evaluation/promotion APIs. Only a real PROMOTE result permits the tail to use
the next-policy map and continuation context. ROLLBACK retains the current
policy. This publisher supplies no promotion verdict.

Tests use actual original formal-training manifest builders and native Generic
receipts/contracts with explicitly synthetic weight bytes. They do not run an
optimizer or vLLM. They exercise real artifact revalidation, immutable replay,
changed-weight rejection, current-request mismatch, H4.4 child inheritance, and
the next-rollout capsule's actual LoRA command. Production GPU loading and
scientific evaluation remain runtime work; local format tests do not attest it.

```
python -B -m pytest work/v17/policy_binding/tests/test_publication.py -q -p no:cacheprovider
```
