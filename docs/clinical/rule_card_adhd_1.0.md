# Rule Card: ADHD ruleset 1.0.0

| | |
|---|---|
| Ruleset identifier and version | `adhd` 1.0.0 (`src/adhd_mcp/data/adhd/ruleset.toml`), signal catalog `adhd.signal_catalog` 1.0.0 (`src/adhd_mcp/data/adhd/signal_catalog.toml`) |
| Effective date | Not released; draft for development on synthetic data (2026-11-27) |
| Status | **Draft.** Windows and weights approved by the project owner on 2026-11-27; this card awaits the owner's approval before release |
| Author | Claude Code agent, under the project owner's decisions of 2026-11-26 and 2026-11-27 |
| Clinical reviewer and date | None yet (open question 1) |
| Server versions that can load it | 0.1.0 and later, including release candidate 1.0.0rc1 (tool contract 0.3.0) |

## Intended use

`assess_referral_need` suggests whether a clinician should **consider referral for formal adult ADHD screening**, and shows the record entries behind the suggestion. It never diagnoses, never assesses suicide risk, and writes nothing. The ruleset is a starting heuristic from published research and **has not been clinically validated**. See the [intended use statement](intended_use.md).

## Population

Adults whose FHIR record the server can read. No age logic is applied; the evidence base is adult and largely civilian.

## Safety gate

The safety gate (rule card: [rule_card_safety_gate.md](rule_card_safety_gate.md)) runs first on every assessment. A positive gate gives `address_safety_gate_first` and withholds any referral suggestion; other findings are still listed. A gate that could not be evaluated (a check failed) gives `insufficient_data`.

## Withheld data

Under a `withhold` privacy policy, a signal not found in data the policy thinned for this patient is reported "Not checked: records it needs were withheld by the privacy policy": a condition signal when its protected category (substance use) lost records, a visit signal when an Encounter was withheld, a medication signal when a medication record was withheld. If no rule fires, the result is `insufficient_data`, not `no_recommendation` (peer review 01, P1; owner decision 2026-11-28). A rule that fires on the remaining signals still gives a suggestion.

## Exclusions

| Exclusion | Definition | Rationale |
|---|---|---|
| Existing ADHD care | `check_existing_care`: an ADHD code (F90, any status other than refuted or entered in error) on a Condition or as a medication reason; an ADHD referral, evaluation or care plan open or completed within 365 days | Avoid duplicate referrals. A missing F90 code is weak evidence of absence (research report) |
| Incomplete exclusion checks | When an existing-care check could not run (for example a site that maps no evaluation codes), a suggestion is still made, with a note to check the record first | Otherwise unmapped sites could never receive a suggestion |
| Narcolepsy medication | Not an exclusion. Medication ordered for narcolepsy is never an ADHD signal; a note says so | Research report |

## Signals

Window: days before the as-of date, inclusive. A condition counts if it is active (open-ended) or was last recorded inside the window after it resolved; undated conditions do not count. All value sets are verified against ICD-10-CM FY2027; drug classes against RxNorm 02-Nov-2026 (ADR 0009).

| Signal | Weight class | Definition (value set, window) | Supplied by tool | Evidence source | Inference? |
|---|---|---|---|---|---|
| Stimulant-related disorder | High | `sud.stimulant` (F15, includes caffeine); 1095 days | `get_mh_problem_list` | Hamed 2026 (civilian): among strongest predictors | No |
| Alcohol involvement | High | `sud.alcohol` (F10), `sud.blood_alcohol_level` (Y90.1-Y90.9; Y90.0 excluded), `sud.alcohol_in_blood` (R78.0); 1095 days | `get_mh_problem_list` | Hamed 2026: Y90.3 a top predictor | No |
| Motor-vehicle crash as driver | High | `injury.motor_vehicle_driver`; one per encounter (or day); at least 1 in 1095 days | `get_utilization_summary` | Crash OR about 1.45 (secondary) | No |
| Repeated accidental injury | High | Emergency or urgent care visits with an injury or accidental external-cause code and no self-harm code; at least 2 in 730 days | `get_utilization_summary` | Accidents lead excess ADHD deaths (Dalsgaard 2015) | Count of 2 is inference |
| TBI overlap | Note | `injury.tbi`, `injury.history_tbi`; 1095 days. Adds a note suggesting neuropsychological evaluation; never counts | `get_mh_problem_list` | Research report: TBI mimics ADHD | No |
| Other substance use | Modifier | `sud.other` (F11, F12, F14, F17.2, F19); 1095 days | `get_mh_problem_list` | ASRS validated in SUD | No |
| PTSD | Modifier | `mh.ptsd` (F43.10-F43.12); 1095 days | `get_mh_problem_list` | Howlett 2018 (soldiers) | No |
| Intermittent explosive disorder | Modifier | `mh.intermittent_explosive_disorder` (F63.81); 1095 days | `get_mh_problem_list` | Nock 2014 (soldiers) | No |
| Depression or anxiety | Modifier | `mh.depression`, `mh.generalized_anxiety`; 1095 days | `get_mh_problem_list` | Women first labeled depressed or anxious | No |
| Multiple antidepressants | Modifier | At least 3 distinct `med.antidepressant` ingredients with exposure in 1095 days | `get_medication_timeline` | "Untested inference" in the research | Yes |
| Borderline personality | Modifier | `mh.borderline_personality` (F60.3); 1095 days | `get_mh_problem_list` | ADHD-BPD comorbidity 18-34% | No |
| Insomnia | Modifier | `sleep.insomnia_delayed_phase`; 1095 days | `get_mh_problem_list` | Insomnia in about 67% (secondary) | No |
| Attention symptoms | Modifier | `symptom.attention_executive` (R41.840, R41.844); 1095 days | `get_mh_problem_list` | Unvalidated | Yes |
| Legal problems | Modifier | Psychosocial domain `legal` (Z65.0-Z65.3); 1095 days | `get_psychosocial_context` | Medication about 13% less criminality | No |
| Education or employment problems | Modifier | Domain `education_occupation` (Z55, Z56); 1095 days | `get_psychosocial_context` | Inference | Yes |
| Housing problems | Modifier | Domain `housing` (Z59.0, Z59.81); 1095 days | `get_psychosocial_context` | Inference | Yes |
| Family history | Modifier | `family.mental_behavioral_history` (Z81.8); 1095 days | `get_mh_problem_list` | Code mapping is inference | Yes |

Not used, because their codes or cutoffs are unverified (follow-up F2): AUDIT-C, PC-PTSD-5, PHQ scores, ASRS. Coded social-history Observation values are reported by `get_psychosocial_context` but not counted in 1.0 (no date in the evidence).

## Decision logic

Recommend referral for formal screening when, within the windows above, **either**

1. at least **one high-weight** signal is present together with **two or more modifiers** (`high_with_modifiers`), **or**
2. **two or more high-weight** signal classes are present (`two_high_classes`).

Notes never count. Precedence: positive safety gate; gate not evaluable; already in care; a rule fired; insufficient data (empty record, or a signal source that could not be read completely); otherwise no recommendation.

A data category the FHIR server does not offer at all (`not_supported`, Phase 8) is not a failed read. One exception to "read completely" is allowed (owner decision 2026-11-27): when the server offers no medication dispenses or statements (VA Lighthouse), the distinct-antidepressant count comes from medication orders alone, and the signal's reason says "Counted from medication orders only: the FHIR server does not offer dispenses or statements." Orders themselves are always required. An empty record on such a server is still insufficient data.

## Outputs

| Recommendation | Approved text (`data/wording.toml`) | Suggested next step |
|---|---|---|
| `consider_referral_for_formal_screening` | Consider referral for formal ADHD screening. | An adult ADHD screen (for example the ASRS-5), then clinician evaluation if positive. A note says the rule is not clinically validated |
| `address_safety_gate_first` | Self-harm signals were found ... no screening referral is suggested until they have been addressed. | Follow the safety gate guidance |
| `already_in_care` | An ADHD code, referral, evaluation or care plan is already recorded ... | None |
| `no_recommendation` | No referral ... is suggested from the coded record ... does not rule anything out | None |
| `insufficient_data` | Too little data could be read to make a suggestion. | None |

`draft_referral_proposal` returns a FHIR ServiceRequest (status draft, intent proposal) only for `consider_referral_for_formal_screening`; it is never stored.

## Evidence base

The combination rule is the research report's starting heuristic ("refer when one high-weight signal co-occurs with two or more modifiers, or when two or more high-weight classes appear within about three years, then calibrate against chart-reviewed cases"). Every anchor estimate is civilian or service-member, not veteran-specific, and many are secondary sources. Windows (1095 and 730 days), the injury count of two and the antidepressant count of three are owner-approved choices, not evidence.

## Evaluation

Full report: [docs/evaluation/adhd_ruleset_1.0.0.md](../evaluation/adhd_ruleset_1.0.0.md) (generated by `scripts/evaluate_ruleset.py`; a test fails if it is stale). Sex-balance review and options: [docs/evaluation/sex_balance_review.md](../evaluation/sex_balance_review.md).

| Item | Result |
|---|---|
| Cohorts used | The 14 hand-built personas (`tests/personas/catalog.toml`) and the labelled cohort (`tests/evals/cohort.py`): 23 archetypes, each built for both sexes and four age bands, 184 synthetic patients, including look-alikes (TBI, PTSD, bipolar disorder, substance use without ADHD signals) and sparse and empty records |
| Agreement with intended outcomes | Personas 14 of 14; cohort 184 of 184 (recommendation, present signals, fired rules and gate status written by hand per archetype before the run) |
| Recommendation rate by sex and age band | Equal across sexes and age bands (24 of 92 women and men; 12 of 46 in every band). The ruleset is sex- and age-blind and the cohort is balanced, so this is by construction |
| Research-profile groups | Suggestive presentations flagged: externalizing 32 of 32, internalizing 8 of 40. Look-alikes and controls flagged: 0 of 64 |
| Sex balance | Under an illustrative presentation mix (women 70% internalizing, men 30%), 44% of women's and 76% of men's suggestive presentations would be flagged. See the sex-balance review |
| Threshold sensitivity | Sixteen one-threshold changes in the report. Two modifiers alone would flag the TBI and PTSD look-alikes; one high-weight signal alone would flag alcohol involvement alone; the antidepressant count has no effect on its own, because modifiers alone never fire a rule |

*Results on a designed synthetic cohort show that the software applies the rules as intended. They are not evidence of clinical accuracy.*

## Known limitations and biases

- **Women are likely under-flagged.** Every high-weight signal (stimulant and alcohol disorders, crashes, injuries) is an externalizing one, and no rule fires on modifiers alone, so an internalizing presentation (depression, anxiety, insomnia, attention symptoms, antidepressant changes) is flagged only if it also has a high-weight signal. On the cohort, 8 of 40 internalizing suggestive presentations are flagged, against 32 of 32 externalizing ones. Persona p02 is an example. The research recommends sex-specific thresholds but gives no values; none are applied. Options are measured in the [sex-balance review](../evaluation/sex_balance_review.md) and await the project owner (open question 16).
- **Coding quality.** Psychosocial problems, family history and TBI are under-coded; a missing code is weak evidence of absence.
- **TBI mimics ADHD.** TBI is a note, not a signal.
- **Drug classes.** Retired RxNorm product codes are not matched; some products carry a class ingredient for another use (ADR 0009).
- **Protected data.** Substance-use signals are protected categories (Phase 6 privacy policy).

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| 1.0.0 (draft) | 2026-11-27 | First version | Phase 5; owner-approved defaults |
