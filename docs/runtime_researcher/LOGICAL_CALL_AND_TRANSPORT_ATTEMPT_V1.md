# Logical Call and Transport Attempt V1

A scientific call and a network attempt are different identities.

```text
logical_call_id
  ├─ transport_attempt_index=0
  ├─ transport_attempt_index=1 (only registered safe retry)
  └─ one terminal method outcome
```

`MAY_HAVE_BEEN_SENT` is terminal until a human disposition exists. Automatic
retry is forbidden. Every attempt, refusal, invalid output, and infrastructure
failure remains in token/latency/cost and failure-reason ledgers.
