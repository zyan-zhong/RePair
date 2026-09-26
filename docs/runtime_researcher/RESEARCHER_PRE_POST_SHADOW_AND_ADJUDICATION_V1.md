# Researcher PRE/POST Shadow and Adjudication V1

Formal order:

```text
formal Analyzer → ROUND_EVIDENCE_PACKAGE freeze
→ Human PRE freeze
→ API PRE shadow on same evidence, technically unable to see Human PRE
→ field-level adjudication
→ F0/F1
→ Environment Result Package freeze
→ Human POST freeze
→ API POST shadow on same result package, unable to see Human POST
→ post adjudication
```

Researcher outputs are recommendations. Training Harness and Promotion Gate retain
execution authority. GO and NO-GO traces are both retained for local training.
