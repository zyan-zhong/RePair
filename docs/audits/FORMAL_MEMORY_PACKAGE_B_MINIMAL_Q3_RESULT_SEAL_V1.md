# Formal Memory Package B — Minimal Q3 Result Seal

Result authority: `ba2290e90631b8836ea93106fd1630237c7b45470bc465c1000e7fb18647fb7b`

Formal B answers only the minimal retrieval/applicability-safety question:
can the frozen Memory tool retrieve relevant historical experience and abstain
instead of exposing wrong/non-applicable Memory under its actual information
boundary?

No external API, model judge, model inference, or environment rollout was used.

Mechanical reference:
- corrected queries: 90
- eligible gold rows: 90
- gold authority: `10ebdb6fe1b6c44d6856f732cb079e1269ea4c6bb01175f6fedb034496a4a0b1`
- gold panel: `481eef8307c18961fcd044bc2093ee0035ddfd42e16e7a75894c58c76e2d5cfa`

Selected retriever:
- threshold: 50%
- config: `54079b6c4d342b57c2944e4e43e0631168a7388fa22f5b660e029c596f2cd2a7`

Selection Validation:
- unsafe exposure: 0/30
- wrong exposure: 0/30
- non-applicable exposure: 0/28
- correct exposure: 0/2
- abstention: 30/30
- coverage: 0/30
- selective accuracy: 0/0
- pre-gate top-1 hit: 1/2

Registered Safety Stress:
- unsafe exposure: 0/30
- wrong exposure: 0/30
- non-applicable exposure: 0/28
- correct exposure: 0/2
- abstention: 30/30
- coverage: 0/30
- selective accuracy: 0/0
- pre-gate top-1 hit: 1/2

Independent byte-identical recomputation: PASS.

This result is Q3 support only. It does not establish causal Benefit/Harm and does
not replace Package C or final Memory-OFF/Harness-OFF policy evaluation.
