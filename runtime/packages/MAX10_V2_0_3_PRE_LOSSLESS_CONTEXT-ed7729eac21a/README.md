# V2.0.3 lossless PRE context recovery

The registered R4 PRE failed before send because the full JSON request was
1,348,171 bytes, above the existing conservative 1,025,424-byte input bound.
Local/G/C/X are already closed and must be reused. This change preserves the
full native projection and uses a lossless readable representation only in the
PRE provider request: named columns for repeated record fields, shared constants,
and exact registered owner-path prefixes. Every original value, order, citation,
candidate, analysis sentence, counterexample and memory record is roundtrip
checked before sending. No strings or scientific rows are truncated. No budget,
candidate selection, output schema, API model or scientific threshold changes.

The existing V188 size guard and native output validators remain active. All
future registered rounds and legitimate retries apply the same automatic encoding
from the typed R4 activation index onward. A genuinely unrepresentable full input
still fails closed; arbitrary future context volume is not promised to fit.

VERIFY.py --server runs tests, real G/C/X terminal reuse, the actual stopped PRE
through its native size gate and sender identity, without provider calls or jobs.
RUN.sh starts the single registered owner only after the server proof. Old owner
is already stopped; no live provider call or scheduler job is terminated. The
existing owner resumes this attempt; it does not rerun completed analysis.

The same entry layer carries the repair; no new scientific loop or provider call
is added. Full original and encoded request hashes and encoding proof are written
under the current PRE's registered_lossless_context/<package-manifest>/ area.
Original frozen manifests, sources, PRE inputs and historical receipts are not
edited. G/X guidance, governed memory, BENEFIT-only Dual-View, TRAIN_SELECT split
and promotion rules remain as registered. Observe through the unchanged unified
FORMAL_MAX10_STAGE_STATUS.sh --watch entry. Operator shell is nonstrict and reads
PIPESTATUS[0] immediately after tee. Deliveries are Git staging cache only.
