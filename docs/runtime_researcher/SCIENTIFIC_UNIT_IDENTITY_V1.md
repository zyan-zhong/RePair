# Scientific Unit Identity V1

Supported units:

```text
EPISODE
ERROR_INSTANCE
GROUP
COMPONENT_BATCH
POLICY_PROFILE
CROSSCHECK_TARGET
ROUND
```

Episode identifiers are nullable for group/policy/round calls. Every call binds a
source-unit manifest and, where applicable, a task-set manifest. Random record
splitting is forbidden for Researcher traces; a round, policy lineage, and task
set remain in one split.
