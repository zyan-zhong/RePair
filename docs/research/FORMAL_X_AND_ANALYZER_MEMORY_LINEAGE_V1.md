# Formal X and Analyzer Memory Lineage V1

## Root cause

The previous evidence-graph join treated `ANALYZER_CROSSCHECK_RESULT_V1` as if
its `target_artifact_sha256` should equal a candidate, source-proposal, group
manifest, or local-result SHA. That is not the registered Formal DAG.

Formal X is a **group-condition-level** challenge:

```text
selected source-conditioned candidate
→ candidate-projector wrapper
→ g_custom_id / x_custom_id
→ validated Formal G batch result
→ ANALYZER_GROUP_RESULT_V2.group_result_sha256
→ validated Formal X batch result
→ ANALYZER_CROSSCHECK_RESULT_V1.target_artifact_sha256
```

One X scientific unit may therefore bind multiple source-conditioned candidates
from the same group and condition. Candidate-level completeness is 60; the
number of unique X scientific units may be smaller and must be reported rather
than forced to 60.

## A2/A3 Memory boundary

- A2 must contain no Analyzer Memory pack.
- A3 must contain exactly the frozen Analyzer Memory role pack declared by the
  X registry row.
- The per-group A3 Memory pack is distinct from the round-level Researcher
  Memory view.
- Historical-only evidence cannot independently authorize X `ACCEPT`.

## Authority boundary

Formal X can accept, downgrade, require abstention, or reject an Analyzer
artifact. It cannot issue Benefit/Harm labels. Human Researcher PRE remains
pre-outcome; Environment F0/F1 remains the only effect authority.

## Current round

Success-trajectory optimization remains inactive. No Human PRE, Strong
Researcher shadow, environment execution, F0/F1, training, or benchmark result
is produced by this lineage-recovery unit.


## X registry representation identity recovery

A single Formal X scientific unit may be described in several registered
containers (registry/schedule/preflight/review copies).  `custom_id` is the
unit key.  The lineage adapter therefore does **not** require every wrapper
dictionary to be byte/field-identical.

The adapter now:

- preserves every representation source and object SHA for audit;
- merges complementary registered scientific claims;
- requires overlapping scientific claims to agree exactly;
- fails closed on conflicting condition, G target, group manifest, Memory
  identity, request/input identity, task identity, or other registered
  scientific assertions;
- treats `projection_path` and container-only metadata as provenance/location,
  not as the scientific identity itself.

This change does not weaken Formal G/X result identity, X disposition checks,
A2/A3 Memory isolation, validated artifact hashes, or the 60-candidate
selection authority.
