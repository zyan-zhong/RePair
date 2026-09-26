# Analyzer Supervision Layers and Evaluation V1

- Layer 1: raw provider trace, including invalid/refused/infrastructure outcomes.
- Layer 2: adjudicated structured Analyzer target; primary local training target.
- Layer 3: later environment alignment (Benefit/Harm/Neutral/Uncertain), usable
  for weighting/calibration/preferences but forbidden from Analyzer inputs.

No future F0/F1 result may leak into pre-verification diagnosis inputs.
