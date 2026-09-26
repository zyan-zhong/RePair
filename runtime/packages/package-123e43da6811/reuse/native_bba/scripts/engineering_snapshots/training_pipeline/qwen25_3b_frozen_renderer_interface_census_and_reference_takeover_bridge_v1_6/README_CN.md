# V1.6 — Frozen Renderer Interface Census + Human→Strong Normative Bridge

V1.5 stopped correctly at:

```text
STOP=HISTORICAL_MESSAGES_INVALID:0
```

The failure means only that the frozen `D_Q2_BAD_V1_TRAINING_EXAMPLE`
source schema is not the `messages=[...]` schema V1.5 assumed.

Hugging Face chat templates consume messages *after preprocessing*; source
datasets are allowed to use domain-specific schemas. Therefore V1.6 does not
guess or rewrite the historical schema.

## Stage 10

Read-only census of exact frozen:

- `training_examples.jsonl` — SHA `9cd758...`
- `materialize.py` — SHA `5f323e...`
- `materialized_examples.jsonl` — SHA `c4f593...`
- `final_materialization_manifest.json` — SHA `868c43...`

It reports:

- real source top-level/nested keys;
- whether source rows actually contain `messages`;
- first three shape summaries and targeted short previews;
- native materialized-row keys;
- materializer function inventory;
- `.get("...")` / `[...]` field accesses by receiver;
- tokenization/chat-template/json calls with line numbers;
- exact source excerpts of functions touching messages/tokenization/labels.

The historical `materialize.py` is never executed.

## Stage 20

Freeze:

```text
REFERENCE_TO_TAKEOVER_NORMATIVE_BRIDGE_V1
```

with the rule:

```text
INHERIT NORMS + TEACHER TRACES
RESET FRESH-ROUND ANSWERS
```

Human reference is the bootstrap curriculum/specification source for Strong
takeover; Strong does not start from a blank methodology. But Strong must
independently recompute fresh-round bottleneck, repairs, F0/F1, routes, recipe
and promotion on fresh evidence.

## Stage 30

Build a self-contained review zip and STOP.

No trainer-native dataset is generated in V1.6. The next package will use the
observed exact schema/materializer interface to build the renderer adapter.
