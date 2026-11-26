# ICD-10-CM value set check, FY2026 tabular (2026-11-26)

Output of `scripts/verify_icd10cm_value_sets.py`, run by the Claude Code agent under the project owner's delegation.

- **Input:** `icd10c-tabular-April-1-2026.xml` (CMS/NCHS ICD-10-CM Tabular List, FY2026 April 1 2026 update), sha256 `f161f8182aff3ce3a2a78e202f8259c08eaee2c670a9e45b0072445c52302935`.
- **Where the file came from:** the PyPI package `simple-icd-10-cm` 1.5.0, which redistributes the CMS/NCHS file. cdc.gov and cms.gov were not reachable from the build environment, so **the hash has not been compared with a file downloaded from CMS or NCHS** (follow-up F1).
- **Not covered:** FY2027 (effective 2026-10-01) (follow-up F1).

To reproduce, obtain the same file and run:

```bash
uv run python scripts/verify_icd10cm_value_sets.py PATH/TO/icd10c-tabular-April-1-2026.xml
```

## Output

```
care.adhd_diagnosis: 5 tabular codes
care.narcolepsy: 4 tabular codes
family.mental_behavioral_history: 1 tabular codes
injury.accidental_external_cause: 516 tabular codes
  self-harm or assault codes matched: 0
injury.history_tbi: 1 tabular codes
injury.injury_codes: 7746 tabular codes
  self-harm or assault codes matched: 0
injury.motor_vehicle_driver: 72 tabular codes
  non-driver codes matched: 0
injury.tbi: 215 tabular codes
mh.borderline_personality: 1 tabular codes
mh.depression: 20 tabular codes
mh.generalized_anxiety: 1 tabular codes
mh.intermittent_explosive_disorder: 1 tabular codes
mh.ptsd: 3 tabular codes
psychosocial.education_occupation: 20 tabular codes
psychosocial.homelessness: 3 tabular codes
psychosocial.housing_instability: 3 tabular codes
psychosocial.legal_problems: 4 tabular codes
safety.history_nonsuicidal_self_harm: 1 tabular codes
safety.history_suicidal_behavior: 1 tabular codes
safety.intentional_self_harm_external_cause: 43 tabular codes
safety.intentional_self_poisoning: 314 tabular codes
  matches exactly the 314 'intentional self-harm' codes, no headers: True
safety.nonsuicidal_self_harm: 1 tabular codes
safety.self_harm_asphyxiation: 8 tabular codes
safety.suicidal_ideation: 1 tabular codes
safety.suicide_attempt: 1 tabular codes
safety.undetermined_intent_poisoning: 314 tabular codes
  matches exactly the 314 'undetermined' codes, no headers: True
sleep.insomnia_delayed_phase: 9 tabular codes
sud.alcohol: 58 tabular codes
sud.alcohol_in_blood: 1 tabular codes
sud.blood_alcohol_level: 10 tabular codes
sud.other: 215 tabular codes
sud.stimulant: 48 tabular codes
symptom.attention_executive: 2 tabular codes
0 problem(s)
```
