# E0–E20 Research Roadmap

| Experiment | Research question | Primary output |
|---|---|---|
| E0 | What exactly did the historical system execute and report? | Minimal historical audit and number ledger |
| E1 | What can an off-the-shelf, project-unadapted instruction model do with the complete menu and no controllers? | `RAW_WITH_MENU_V1` trajectory baseline |
| E2 | What failures emerge when only the menu is removed? | Independent grounding stress-test report |
| E3 | Are progress verifiers and critical-point detectors reliable? | Held-out precision/recall and threshold audit |
| E4 | Is a verifier-terminated option better than one-step redirect? | Matched mechanism comparison |
| E5 | Is the gain explained by extra actions or observations? | Equal-cost random/novelty/budget controls |
| E6 | Can fresh states be included without viewing outcomes? | Outcome-independent state manifest |
| E7 | Are matched intervention effects stable across paired seeds? | Benefit/Harm/Neutral/Uncertain evidence |
| E8 | Do terminal effects decompose into distinct pathways? | Direct, indirect, completion and disruption report |
| E9 | How strong is the flat representation baseline? | Task-held-out flat selector results |
| E10 | Do action/source sequences improve selection? | Sequence representation comparison |
| E11 | Do graph state and completion burden improve safe coverage? | Risk–coverage and hybrid-success comparison |
| E12 | What does ordinary successful-trajectory SFT achieve? | Harness-OFF SFT baseline |
| E13 | What does unfiltered Harness-success SFT achieve? | Scaffold-distillation baseline |
| E14 | Does Benefit-only training improve data quality? | Audited positive-evidence result |
| E15 | Do Benefit–Harm preferences reduce regression? | Preference-learning result |
| E16 | Does audited RL credit outperform outcome-only credit? | RL credit-assignment comparison |
| E17 | Does the main failure/method trend reproduce on a second model? | Cross-model result |
| E18 | Does it hold across task families and menu interfaces? | Interface/task-family transfer |
| E19 | Does the protocol transfer to a second environment/option? | Environment/option transfer |
| E20 | Can a gated Trainer Agent propose useful new research operators? | Optional autonomous-research extension |

The active immediate order is:

```text
E0 → E1 → E3 → E2 → E4–E8 → E9–E11 → E12–E16
```

E2 is scientifically useful but does not block the main R0-versus-R2
method comparison.
