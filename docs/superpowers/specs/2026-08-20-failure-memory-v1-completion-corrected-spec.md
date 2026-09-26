# Failure Memory V1 Completion — Corrected Specification

Implement the design in `docs/memory/FAILURE_MEMORY_V1_COMPLETION_DESIGN.md`.

Hard constraints:

1. start from `da505ae55f326a44245c9703847d94edfdbcf775`;
2. preserve `708638a...` as incident evidence only;
3. modify no `src/pchsi/research`, `src/pchsi/training`, `scripts/research` or
   `scripts/training` path;
4. Task Policy, Analyzer export and Researcher export are distinct artifacts;
5. no same-round shadow readback;
6. no evaluation writeback;
7. Memory never executes a model, environment, trainer or benchmark;
8. environment F0/F1 is effect authority;
9. Q4/Q5 missing external authorities remain OPEN/DEFERRED;
10. build locally, perform fixed-head review and create a Git bundle; do not push.
