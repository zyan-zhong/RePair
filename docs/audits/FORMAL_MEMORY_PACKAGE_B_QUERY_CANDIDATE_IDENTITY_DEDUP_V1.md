# Formal Memory Package B — Query-Candidate Identity Deduplication

Trigger: PRE-GOLD DATA-PREPARATION PROTOCOL DEFECT.

The first outcome-blind candidate builder stopped before producing a pool freeze
because multiple model calls in at least one failure had identical production
`FormalBQueryV1` identity.

No gold label, retrieval score, threshold result, or Formal-B scientific outcome
existed.

Correction:
- do not alter FormalBQueryV1 identity;
- do not add model-call index or trace index to retriever-visible identity;
- enumerate policy-visible states using the production query identity;
- scan backward from the failure tail;
- collapse repeated identical query IDs;
- retain the last up to three unique query identities;
- restore chronological order in the annotation packet.

Task/gamefile pool assignment remains exactly the V1 outcome-blind rule.
