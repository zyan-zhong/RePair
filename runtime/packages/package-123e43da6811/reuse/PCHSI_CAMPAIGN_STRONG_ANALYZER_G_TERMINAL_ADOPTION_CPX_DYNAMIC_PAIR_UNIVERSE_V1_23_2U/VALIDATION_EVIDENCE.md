# Validation evidence

Observed V1232T log supplied by the operator shows 76 G calls before the wrapper exception: 39 G-A2 and 37 G-A3. Mechanical log census: 69 ACCEPTED, 4 INFRASTRUCTURE_UNAVAILABLE, 3 AMBIGUOUS_POST_SEND. This implies 34 complete A2+A3 groups, 3 quarantined groups, and 2 non-ambiguous incomplete groups. These values are evidence only and are **not production constants**.

The exact exception is `KeyError: 'G-A2'` at the first C-stage lookup after the G sweep. The T producer stores `A2` and `A3` keys, so U adds a single tested stage-key bridge.

Historical Stage6J governance reused unchanged: ambiguity quarantines the group with no resend/replacement; infrastructure missingness with hard_stop=false is preserved and the sweep continues; only complete accepted pairs enter C/P/X.

Package tests explicitly reject any G-stage provider execution path and reject hard-coded live cardinalities.
