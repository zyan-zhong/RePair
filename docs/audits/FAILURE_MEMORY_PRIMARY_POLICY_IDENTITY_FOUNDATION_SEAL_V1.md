# Failure Memory Primary Policy Identity Foundation Seal V1

## Decision

FAILURE_MEMORY_PRIMARY_POLICY_IDENTITY
=
SCIENTIFICALLY_CLOSED

This seal records successful read-only materialization and independent
verification of the frozen Failure Memory primary/secondary policy
identity contract.

## Approved code identity

Approved repository head:

`1a0feeef8085ba124fa79e72c38fea90b812d9f9`

Materializer Git blob:

`84fda92d63adef433d0adee7156b7c278caefe49`

Policy-contract Git blob:

`1a3fcea0363b34f1b2c08b3e38a73329b31e625d`

Policy-source config Git blob:

`b6829748de4b19e0e2faaebe593f08282aebb031`

## Frozen policy-source archive

Checkpoint-set root seal:

`6dd3ad3389869d6f929af24283589f2e22f4c687a800072af16bb6f23b5092f8`

Regular source files:

`23`

Total source bytes:

`359767109`

Checkpoint-set manifest SHA-256:

`b374398da2f8103376f54998bc15dd35f73ad90fe5bed93742dfd23d52c7ef87`

Runner manifest SHA-256:

`9689eccc2b8209f79d657193cced1790eeb2994e5b3bff759de56fd8418a1b45`

Base model:

`Qwen/Qwen2.5-3B-Instruct`

Base-model revision:

`aa8e72537993ba99e69dfaafa59ed015b17504d1`

Tokenizer bundle SHA-256:

`8fba154872aa8982e9556cb6cbdd35f3f6e83b8c3c41d782caf6fbf5931c8e0c`

Source PRE/POST snapshot:

`6dd3ad3389869d6f929af24283589f2e22f4c687a800072af16bb6f23b5092f8`

Source PRE/POST equality:

`true`

## Frozen Failure Memory policy identity

Primary worker:

`P4-R1-Q2-BAD-TRAIN17`

Primary training seed:

`17`

Secondary policy-realization audit seeds:

`31, 47`

Selection rule:

`MINIMUM_POLICY_TRAINING_SEED_FROM_FROZEN_ROUND1_CHECKPOINT_SET`

Source-record effect policy:

`ORIGINAL_SOURCE_CHECKPOINT`

Secondary audit:

`FM0_NO_PERSISTENT_MEMORY_VS_FM3_GATED_PRESCRIPTIVE_MEMORY`

No-best-of-checkpoint:

`true`

All-secondary-results-reported:

`true`

Primary policy contract SHA-256:

`048b131d57c8080592e8855d483ced33c30b0362eec644a545a5f3ec29e86f82`

## Execution evidence

Execution identity SHA-256:

`ae2fc66326911e08120ae2d2c699160a98febd75d72b1582519b01536e7928bd`

Materializer stdout SHA-256:

`9196c4977e8368c65a5f43149e779154075dd69f57603a13473c32199e0f0e3f`

Materializer stderr SHA-256:

`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`

Terminal-success SHA-256:

`541f88253d377a48cdc4443ba008129f0d6f7ebe4eef53bcf956c66c4b3cb9d8`

Execution manifest SHA-256:

`e88b66e512e47d3ee15f955238d0b9cc225e7e54a7c910b936c84c6f9c8de8e7`

## Independent audit

PRIMARY_POLICY_IDENTITY_OUTPUT_AUDIT_PASS

PRIMARY_POLICY_IDENTITY_INDEPENDENT_REBUILD_PASS

PRIMARY_POLICY_SOURCE_PRE_POST_EQUAL_PASS

PRIMARY_POLICY_IDENTITY_FINAL_AUDIT_PASS

PRIMARY_POLICY_IDENTITY_MATERIALIZATION_PASS

## Explicit non-events

TASK_ACCESS_MATERIALIZATION_EXECUTED=false

ALFWORLD_EXECUTION_EXECUTED=false

MODEL_EXECUTION_EXECUTED=false

FAILURE_MEMORY_CONSTRUCTION_EXECUTED=false

No policy execution, ALFWorld rollout, Failure Memory construction,
retrieval, training or benchmark execution occurred.

## Unit-1 closure consequence

Together with:

`docs/audits/FAILURE_MEMORY_TASK_ACCESS_FOUNDATION_SEAL_V1.md`

this closes both required Unit-1 foundation components:

- task/gamefile access identity;
- primary/secondary frozen Policy identity.

This does not establish Failure Memory effectiveness.
