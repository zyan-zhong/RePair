# Formal Memory Package B — Pre-Outcome Protocol-Defect Amendment V1

Trigger: `PROTOCOL_DEFECT`

Timing: before any Formal-B scientific panel execution or Q3 result unblinding.

The fixed-head source review of `f94316668e3907c6c90738f6685b74c962f16e34`
identified two pre-outcome defects:

1. Threshold selection ranked `wrong_memory_exposure_rate` first but omitted
   `non_applicable_memory_exposure_rate` from its selection key. A threshold could
   therefore be preferred despite exposing Memory on gold-abstention rows.

2. The offline runner accepted a panel carrying an
   `independent_gold_authority_sha256` string but did not load and rebind the panel
   to an actual independent gold-authority artifact.

Correction:

- define `unsafe_memory_exposure_rate =
  (wrong_exposure_count + non_applicable_exposure_count) / row_count`;
- selection is lexicographically:
  1. lower unsafe exposure rate;
  2. lower wrong-memory exposure rate;
  3. lower non-applicable-memory exposure rate;
  4. higher correct-memory exposure rate;
  5. higher selective accuracy;
  6. higher coverage;
  7. higher threshold as conservative deterministic tie-break;
- every Calibration DEV, Selection Validation, and Safety Stress pool must contain
  both positive exposure gold and abstention gold;
- active candidate Memory lineages must be unique;
- introduce `FORMAL_B_INDEPENDENT_GOLD_AUTHORITY_V1`;
- require the runner to load `--gold-authority`, verify its semantic authority SHA,
  and rebind every panel query to the independent authority's query ID, gold target,
  and row-level evidence SHA.

Unchanged:

- Q3 scientific question;
- three-stage pool isolation;
- `TRAIN_RETRIEVAL_DEV` source population;
- no `valid_seen` or `valid_unseen` tuning;
- `CASEFOLD_WORD_JACCARD_V1`;
- threshold grid `0.00..0.50` step `0.05`;
- top-score tie abstention;
- existing mechanical applicability gate;
- only `APPLICABLE` permits exposure;
- Safety Stress cannot modify the selected configuration;
- no causal Benefit/Harm authority.

No Formal-B outcome existed when this amendment was registered.
