The resident driver calls `close_round_tail` after replaying the original current
Analyzer/H4.4 verifier and, on TRAIN, the actual trainer/OFF/OFF validators.
It supplies start, the Analyzer operation binding and output root, attempt root,
current rollout input/execution refs, and five stage refs named execution_plan,
verifier, post_projection, post_logical_call, post_artifact. All entry refs use
`{path,sha256}`. The Analyzer/Memory producer spelling `{path,file_sha256}` is
converted mechanically. Install the registered Memory overlay before any native
imports; the resident bootstrap must carry it to native child processes.

Current inputs use the existing ROUND_ROLLOUT_INPUT_REFERENCES_V1 schema with
runtime/profile/memory/train_manifest. Every SHA is checked against start. Initial
Memory state is registered from its real nonempty snapshot; later calls pass the
previous materializer's memory_state ref. The Analyzer binding transports the
native memory_source_partitions map. New partitions are merged only for lineages
admitted by the native closure. The actual Memory producer is called directly;
unsupported applicability remains unresolved according to that producer.

NO_TRAIN uses the accepted POST count unchanged, including positive Benefit.
TRAIN consumes CURRENT_NATIVE_OFFOFF_TERMINAL_V1, its original native promotion,
summary and current parent/candidate binding. PROMOTED additionally requires
next_policy_input_refs with runtime/profile/policy_launch_authority/engine_profile
from the candidate publisher. A formal promotion criterion is not created here.
Given promotion fixtures prove identity wiring, not criterion availability.

The return value matches the existing campaign owner result protocol. The driver
uses validate_closed_round_tail during receipt recovery and combines it with the
upstream validators. After the owner advances its original governor, call
build_next_round_tail. It returns request, execution_binding, memory_state,
input_refs, memory_source_partitions, next_request and validation_receipt refs
(also next_creation for TRAIN). The root registers these under the exact new
request SHA; it returns only next_request to NativeRoundDriver.build_next. The
immutable current RESULT is never amended, and STOP produces no next request.

`python -B -m pytest -q -p no:cacheprovider work/v17/entry/tests` exercises real
native fixture reconstruction, candidate publication, five-pair verification,
Memory event/closure/snapshot, positive-Benefit NO_TRAIN and next-round native
governance/request/binding. Provider output, environment evidence and tokenizer
are fixtures. It runs no provider call, GPU job or live scientific campaign.
