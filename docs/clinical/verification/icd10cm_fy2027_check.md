# ICD-10-CM value set check, FY2027 tabular (2026-11-27)

Output of `scripts/verify_icd10cm_value_sets.py`, run by the Claude Code agent under the project owner's delegation. Closes the automated part of follow-up F1.

- **Input:** `icd10cm-tabular_-2027.xml` (CDC/NCHS ICD-10-CM Tabular List, FY2027, effective 2026-10-01), extracted from `icd10cm-table-and-index-2027.zip` downloaded from `https://ftp.cdc.gov/pub/Health_Statistics/NCHS/Publications/ICD10CM/2027/` on 2026-11-27.
  - XML sha256 `d778c97a5bb9da7d71645610e277f8db3bd302befa3b08d71dd5043715a74b2a` (pinned in the script)
  - zip sha256 `99b5c2be16ff53eab861cc0be4b1dacba27f687b8ff4bc700679944355037ee0`
- **Result:** every check passes (exit code 0).
- **Changes from FY2026 that touch a value set** (found by comparing the two tabular files):
  - New poisoning codes T52.81-, T52.82-, T52.89- (replacing T52.8X-), T59.82- and T65.85-. The intent-character regexes in `safety.intentional_self_poisoning` and `safety.undetermined_intent_poisoning` match the new intentional (2) and undetermined (4) codes exactly, so each set now matches 318 codes (314 in FY2026). No data change was needed.
  - S23.420 was deleted, so `injury.injury_codes` matches 7745 codes (7746 in FY2026).
  - No other value set changed.
- **FY2026 source check:** the FY2026 April 1 2026 tabular downloaded from ftp.cdc.gov (`icd10cm-April-1-2026-XML.zip`, XML sha256 `fbbb7f6ee319eb0259e43d369ec50bc15af9a2c983d4440b936b3d70a53f7624`) gives output identical to the run recorded in [icd10cm_fy2026_check.md](icd10cm_fy2026_check.md) on the PyPI copy. The two files' hashes differ, but they produce the same result for every value set.
- **Added 2026-11-27:** `mh.mental_behavioral_chapter` (chapter 5 regex, the problem list's fallback family) matches all 872 F leaf codes and nothing else.
- **Added 2026-11-27 (Phase 8):** `care.autism_diagnosis` (F84.0, F84.5, F84.8, F84.9; exclusion of the experimental autism stub) matches 4 tabular leaf codes. Same pinned zip and XML (hashes above); output otherwise unchanged. F84.2 (Rett's syndrome) and F84.3 (other childhood disintegrative disorder) are left out by owner decision.
- **Human spot-check:** waived by the project owner on 2026-11-27 for synthetic-only development; it is a release blocker for 1.0.0 ([verification backlog](../verification_backlog.md), F1).

To reproduce, download the same zip, extract the XML and run:

```bash
uv run python scripts/verify_icd10cm_value_sets.py PATH/TO/icd10cm-tabular_-2027.xml
```

## Output

```
care.adhd_diagnosis: 5 tabular codes
care.autism_diagnosis: 4 tabular codes
care.narcolepsy: 4 tabular codes
family.mental_behavioral_history: 1 tabular codes
injury.accidental_external_cause: 516 tabular codes
  self-harm or assault codes matched: 0
injury.history_tbi: 1 tabular codes
injury.injury_codes: 7745 tabular codes
  self-harm or assault codes matched: 0
injury.motor_vehicle_driver: 72 tabular codes
  non-driver codes matched: 0
injury.tbi: 215 tabular codes
mh.borderline_personality: 1 tabular codes
mh.depression: 20 tabular codes
mh.generalized_anxiety: 1 tabular codes
mh.intermittent_explosive_disorder: 1 tabular codes
mh.mental_behavioral_chapter: 872 tabular codes
mh.ptsd: 3 tabular codes
privacy.hiv: 3 tabular codes
privacy.sickle_cell: 43 tabular codes
psychosocial.education_occupation: 20 tabular codes
psychosocial.homelessness: 3 tabular codes
psychosocial.housing_instability: 3 tabular codes
psychosocial.legal_problems: 4 tabular codes
safety.history_nonsuicidal_self_harm: 1 tabular codes
safety.history_suicidal_behavior: 1 tabular codes
safety.intentional_self_harm_external_cause: 43 tabular codes
safety.intentional_self_poisoning: 318 tabular codes
  matches exactly the 318 'intentional self-harm' codes, no headers: True
safety.nonsuicidal_self_harm: 1 tabular codes
safety.self_harm_asphyxiation: 8 tabular codes
safety.suicidal_ideation: 1 tabular codes
safety.suicide_attempt: 1 tabular codes
safety.undetermined_intent_poisoning: 318 tabular codes
  matches exactly the 318 'undetermined' codes, no headers: True
sleep.insomnia_delayed_phase: 9 tabular codes
sud.alcohol: 58 tabular codes
sud.alcohol_in_blood: 1 tabular codes
sud.blood_alcohol_level: 9 tabular codes
sud.other: 215 tabular codes
sud.stimulant: 48 tabular codes
symptom.attention_executive: 2 tabular codes
0 problem(s)
```
