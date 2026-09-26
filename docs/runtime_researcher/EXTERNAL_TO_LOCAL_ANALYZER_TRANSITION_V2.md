# External-to-Local Analyzer Transition V2

1. Strong API Analyzer primary + local raw shadow.
2. Strong API primary + distilled local shadow + X/human adjudication.
3. Local primary on eligible DEV workload + strong-model disagreement audit.
4. Routine external calls removed; external model retained for low-confidence or
   high-risk audit.

Promotion cannot use prose similarity alone. It requires schema/identity/evidence
validity, localization agreement, uncertainty/abstention calibration, candidate
executability, downstream EVRY, Harm, and verification cost.
