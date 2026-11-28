# Rule Card: safety gate 0.1.0

| | |
|---|---|
| Ruleset identifier and version | `safety_gate` 0.1.0 (`src/adhd_mcp/data/safety_gate.toml`) |
| Effective date | Not released; draft for development on synthetic data |
| Status | Draft |
| Author | Claude Code agent, under the project owner's decisions of 2026-11-26 and 2026-11-27 |
| Clinical reviewer and date | None yet (open question 1). The human spot-check of the `safety.*` value sets is waived for development and is a release blocker |
| Server versions that can load it | 0.1.0 and later, including release candidate 1.0.0rc1 (tool contract 0.2.0 and later) |

## Intended use

The safety gate runs before any referral suggestion. It reports self-harm signals found in the record so that a clinician addresses them first, through the local suicide risk evaluation process and lethal-means counseling. It does not assess suicide risk, does not replace a risk screen, and is not a diagnosis. See the [intended use statement](intended_use.md).

## Population

Adults whose FHIR record the server can read. No age logic is applied by the gate.

## Safety gate

Look-back: coded signals and screening results count if dated within **365 days** of the as-of date, inclusive (owner decision 2026-11-27, open question 2). The date of a condition is the later of its recorded date and its onset. **Undated items count.** Items dated after the as-of date are ignored. Older items are listed under `history` and do not make the gate positive.

| Signal (check id) | Definition (value set, window) | Source | Verified |
|---|---|---|---|
| Suicidal ideation (`suicidal_ideation_code`) | `safety.suicidal_ideation` (R45.851) on a Condition or an Encounter reason; 365 days | Research report, safety gate table | ICD-10-CM FY2027, agent check; human spot-check owed |
| Suicide attempt (`suicide_attempt_code`) | `safety.suicide_attempt` (T14.91XA/XD/XS), `safety.intentional_self_harm_external_cause` (X71-X83); 365 days | Research report | As above |
| Intentional self-poisoning (`intentional_self_poisoning_code`) | `safety.intentional_self_poisoning` (T36-T65, intent character 2); 365 days | Research report | As above |
| Undetermined-intent poisoning (`undetermined_intent_poisoning_code`) | `safety.undetermined_intent_poisoning` (intent character 4); 365 days | Research report ("treat as possible self-harm") | As above |
| Self-harm by asphyxiation (`self_harm_asphyxiation_code`) | `safety.self_harm_asphyxiation` (T71.1x2, T71.2x2); 365 days | Found during verification; **not in the research**. Owner approved 2026-11-27 | As above |
| Non-suicidal self-harm (`nonsuicidal_self_harm_code`) | `safety.nonsuicidal_self_harm` (R45.88); 365 days | Research report | As above |
| History of suicidal behavior or self-harm (`self_harm_history_code`) | `safety.history_suicidal_behavior` (Z91.51), `safety.history_nonsuicidal_self_harm` (Z91.52); 365 days by recorded date | Research report | As above |
| Psychiatric discharge (`psychiatric_discharge`) | Encounter mapped by the site as psychiatric inpatient or residential; discharge (period end) within 90 days (signal `psychiatric_discharge_within_90_days`, presented first) or 365 days; a stay discharged after the as-of date, or with no discharge date and not finished, counts as current; a finished stay with no discharge date is dated by its start. Planned or cancelled encounters do not count | Research report (Britton 2017; Luxton 2013) | Site mapping (`data/site_codes/`); only the synthetic site exists |
| PHQ-9 item 9 (`phq9_item9`) | LOINC 44260-8, value at or above 1, as an Observation, a panel component, or a mapped QuestionnaireResponse item; 365 days | Research report (Louzon 2016) | **No**: LOINC unverified (F2). Not scored; any result under the code within 365 days fails the check (see below) |
| C-SSRS risk level (`cssrs_risk_level`) | LOINC 93374-7 answered Moderate (LA6751-7) or High (LA9193-9); 365 days | Research report | **No**: LOINC unverified (F2). Not scored; any result under the code within 365 days fails the check (see below) |
| High-risk flag (`high_risk_flag`) | Flag mapped by the site as high risk for suicide, status active and not ended before the as-of date | Research report | Site mapping; only the synthetic site exists |

A negative PHQ-9 item 9 never clears the gate: each check is independent, and any positive check makes the gate positive.

**Gate status** (owner decision 2026-11-27):

| Status | When |
|---|---|
| `positive` | Any check found a current signal. Fixed guidance is returned (`safety_gate_guidance` in `data/wording.toml`) |
| `data_unavailable` | No signal found and a check failed because its data could not be read, or was read only in part (the server warned, or a resource could not be read). Partial data never supports "not found" (owner decision 2026-11-27, server 1.0.0rc1) |
| `clear_limited_data` | No signal found, nothing failed, and a check was not performed (including because the FHIR server does not offer the data type it needs), or the record is empty |
| `clear` | Every check ran and found nothing |

Today the two LOINC-based checks are not performed, so no gate is plain `clear`.

**A result under an unverified code stops the gate** (peer review 01, S2; owner decision 2026-11-28). The two LOINC-based checks still look for results under the codes their instrument files list (PHQ-9 item 9: 44260-8 as an Observation, a panel component or a mapped QuestionnaireResponse item; C-SSRS risk level: 93374-7). Any such result inside the 365-day look-back, whatever its value, fails the check with the reason "A result is recorded under this check's code, but the code or cutoff is not verified yet" and cites the resource; the gate is then `data_unavailable` and no referral is suggested. An unreadable Observation or QuestionnaireResponse category fails these checks for the same reason. The unverified code is used only to stop, never to score or to clear. Until LOINC is verified (open question 14), any patient with a PHQ-9 or C-SSRS result in the past year is `insufficient_data`. Persona p15 covers this case.

## Exclusions

None. The gate applies to every patient.

## Signals

Not applicable; the gate has no weighted signals.

## Decision logic

Any one current signal makes the gate positive. There is no scoring and no combination rule.

## Outputs

`check_safety_gate` returns the status, every check with its outcome (found, not found, not performed with a reason, failed with a reason), evidence items citing FHIR resource ids, history items, and the guidance text when positive. In Phase 5 a positive gate makes `assess_referral_need` return "address safety gate first".

## Evidence base

From the research report, safety gate section: prior self-harm is the strongest predictor in published suicide models; VA's Risk ID program uses the C-SSRS screener; PHQ-9 item 9 endorsement carried HR 1.92 for suicide death in VA data (Louzon 2016), but a negative answer does not exclude risk (Simon 2013); risk after psychiatric discharge concentrates in days 1-90 (Britton 2017, veterans; Luxton 2013, service members). The 365-day look-back for coded signals and screens, and counting undated items, are design choices (owner decision), not evidence.

## Evaluation

| Item | Result |
|---|---|
| Cohort used | Synthetic persona catalog (10 personas), plus unit tests per signal |
| Agreement with intended outcomes | All personas match `tests/personas/catalog.toml`, with today's content and with all checks active |
| Recommendation rate by sex | Not applicable |
| Recommendation rate by age band | Not applicable |
| Threshold sensitivity | Boundary days tested for every window |

*Results on a designed synthetic cohort show that the software applies the rules as intended. They are not evidence of clinical accuracy.*

## Known limitations and biases

- Depends on coding: self-harm is under-coded, and much of it lives in note text, which is out of scope.
- The PHQ-9 item 9 and C-SSRS checks cannot be scored until LOINC is verified: a recorded result stops the gate (`data_unavailable`) instead, and a record without one relies on codes, discharges and flags only.
- Psychiatric encounters and flags depend on each site's local codes; a site without a mapping gets those checks as not performed.
- An old suicide attempt (over 365 days) does not make the gate positive; it is listed as history for the clinician.
- C-SSRS screener item answers (without a risk level) are not read; no LOINC code for a screener result was found.
- Encounter reason codes count whatever the encounter's status, and questionnaire responses count whatever their status (in progress or stopped included). Both are deliberately conservative.
- A server with no site code mapping gets the discharge and flag checks as not performed (the default for a FHIR server).
- A check that needs a resource type the FHIR server does not offer (`not_supported`, Phase 8) is not performed, with the reason "the FHIR server does not offer ..."; it is never "not found". A failed read still outranks it (`data_unavailable`). On VA Lighthouse, Flag and QuestionnaireResponse are not offered. Every server profile must offer Condition and Encounter, which the coded checks need.

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| 0.1.0 | 2026-11-27 | First draft, revised after the clinical safety review (unreadable resources limit the gate; finished stays without a discharge date dated by their start) | Phase 3 |
| 0.1.0 (server 1.0.0rc1) | 2026-11-27 | A check whose data was read only in part now fails (gate `data_unavailable`, no referral suggestion) instead of reporting not found with a limited gate. Gate definition data unchanged; the behaviour is in `evidence/safety_gate.py` | Phase 7 clinical safety review; owner decision (open question 19) |
