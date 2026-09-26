# V1232X implementation plan

1. Reuse V1232V Dynamic PRE V2 translation, prompt/schema, Memory-view constructor, semantic validator, and F0/F1 handoff.
2. Reuse V1232W historical `infra_recovery_disposition.py` byte-for-byte and its bounded remediation policy.
3. Before stable Memory resolution, construct the exact current-round evidence object.
4. Partition all matching current-snapshot Researcher views by semantic round-evidence binding.
5. Exclude views exactly bound to the current round evidence from **predecessor** Memory authority discovery.
6. Require remaining candidates to collapse to one stable Memory signature using the existing resolver.
7. Reconstruct the exact original V1232V activation artifact and keep `write_or_verify_json` strict; do not weaken identity checking.
8. Record a new resume-census receipt with observed counts and hashes.
9. Reconcile the original PRE terminal and use the historical infra classifier.
10. Only exact safe infra classes may produce one new remediation logical call; ambiguous/method/config failures remain no-call fail-closed.
11. If accepted, produce the existing planner-bound F0/F1 handoff.

No current round counts, candidate SHAs, server activation IDs, or selected-state counts are compiled into production logic.
