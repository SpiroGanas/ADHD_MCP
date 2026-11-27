# Verification Backlog

The research report was written with full-text access blocked for many sources, so most codes and cutoffs are marked unverified there. **Nothing on this list may be used in an active ruleset until it is checked against an authoritative source and marked verified here.** The terminology loader enforces this in strict mode.

The full list of items to verify, including effect sizes and regulatory facts, is in the research report under "Evidence limitations and items to verify". This file tracks only what the planned ADHD ruleset and safety gate need.

## How to verify

1. Check the item against the authoritative source named below.
2. Record the source, its version or date, the date checked and who checked it.
3. Set the status. If the item is wrong, record the correct value and correct the data file in the same pull request.

Authoritative sources: the CDC ICD-10-CM browser and current fiscal-year tabular list for diagnosis codes; loinc.org for LOINC; the NLM RxNorm browser for medications; instrument manuals or the publisher for cutoffs.

**Status values:** Unverified, Verified, Corrected, Dropped.

## Verification record (2026-11-26)

Checked by the Claude Code agent under the project owner's delegation of 2026-11-26.

- **ICD-10-CM** items were checked against the CMS/NCHS tabular list, FY2026 April 1 2026 update (`icd10c-tabular-April-1-2026.xml`, sha256 `f161f8182aff3ce3a2a78e202f8259c08eaee2c670a9e45b0072445c52302935`). **The file was obtained from the PyPI package `simple-icd-10-cm` 1.5.0, which redistributes it; its hash has not yet been compared with a file downloaded from CMS or NCHS**, because cdc.gov and cms.gov were not reachable from the build environment. Every value set was run against every code in the file with the project's own matcher (`scripts/verify_icd10cm_value_sets.py`; output in [verification/icd10cm_fy2026_check.md](verification/icd10cm_fy2026_check.md)). Items are marked Verified or Corrected on that basis. **FY2027 (effective 2026-10-01), the current fiscal year, was not checked directly**; secondary change summaries report no FY2027 change to any code in scope. All entries were checked by the agent; no human has spot-checked them yet. Follow-up item F1.
- **Update 2026-11-27 (follow-up F1, automated part):** cdc.gov became reachable. The FY2026 April 1 2026 tabular downloaded from ftp.cdc.gov gives identical results to the PyPI copy (the file hashes differ). Every value set was re-run against the **FY2027** tabular from ftp.cdc.gov and passes; provenance in the data files now names FY2027. See [verification/icd10cm_fy2027_check.md](verification/icd10cm_fy2027_check.md). The **human spot-check was waived by the project owner on 2026-11-27** for synthetic-only development; it remains a **release blocker** (Phase 7).
- **LOINC codes and cutoffs** could only be confirmed through search-engine summaries of loinc.org and abstracts; loinc.org, ptsd.va.gov and healthquality.va.gov were not reachable. They stay **Unverified**, with the finding recorded. Follow-up item F2.
- The value set files in `src/adhd_mcp/data/value_sets/` and instrument files in `src/adhd_mcp/data/instruments/` carry the same status per entry.

## Priority 1: safety gate (needed for Phase 3)

| Item | Value in the research | Source to check | Status | Checked (who, when, source version) |
|---|---|---|---|---|
| Suicidal ideation | ICD-10-CM R45.851 | ICD-10-CM | Verified. Exact code only: parent R45.85 includes homicidal ideation (`safety.suicidal_ideation`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Suicide attempt | T14.91XA and related characters; external causes X71 to X83 | ICD-10-CM | Corrected: T14.91 needs the placeholder (T14.91XA/XD/XS); T14.90 must not match. X71-X83 verified; there is no X84 (`safety.suicide_attempt`, `safety.intentional_self_harm_external_cause`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Intentional self-poisoning | T36 to T65 with sixth character 2; undetermined intent with 4 | ICD-10-CM | Corrected: the intent digit is the last character before the 7th, which is the 5th character in five-character codes (T36.92XA). The rule matches exactly the 314 official self-harm and 314 undetermined codes (`safety.intentional_self_poisoning`, `safety.undetermined_intent_poisoning`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Self-harm by asphyxiation (new) | Not in the research | ICD-10-CM | Verified as codes: T71.112, T71.122, T71.132, T71.152, T71.162, T71.192, T71.222, T71.232 (`safety.self_harm_asphyxiation`). Owner approved use in the gate 2026-11-27 | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Non-suicidal self-harm | R45.88; history Z91.52 | ICD-10-CM | Verified. Z91.5 has only Z91.51 and Z91.52 | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| History of suicidal behavior | Z91.51 | ICD-10-CM | Verified | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| PHQ-9 item 9 | LOINC 44260-8; positive at 1 or more | loinc.org | Unverified. Code and name consistent in search summaries. "1 or more" is protocol practice, not a validated cut | Search-index summary of loinc.org only, 2026-11-26 |
| PHQ-9 panel and total | LOINC 44249-1, 44261-6 | loinc.org | Unverified. Consistent in search summaries; 44257-4 is a deprecated panel code mapping to 44249-1 | Search-index summary of loinc.org only, 2026-11-26 |
| C-SSRS screener panel and risk level | LOINC 93373-9, 93374-7 | loinc.org | Unverified. 93373-9 is the screener (recent) panel; 93374-7 is "Suicide risk level" (answer list LL465-6: low, moderate, high). No total-score code exists | Search-index summary of loinc.org only, 2026-11-26 |
| Psychiatric inpatient and residential encounters; high-risk flags | No codes given; define by encounter class, type and service | US Core and local server | Site mapping (owner decision 2026-11-27): local codes are mapped per site in `data/site_codes/`. Only the project's own synthetic code system is mapped, which is verified by construction. A real site supplies its own mapping (Phase 8) | Agent, 2026-11-27 |

## Priority 2: exclusions and screening history (Phase 3)

| Item | Value in the research | Source to check | Status | Checked |
|---|---|---|---|---|
| ADHD diagnosis | F90.x | ICD-10-CM | Verified: F90.0, F90.1, F90.2, F90.8, F90.9 (`care.adhd_diagnosis`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Narcolepsy | G47.4x | ICD-10-CM | Verified: G47.411, G47.419, G47.421, G47.429 (`care.narcolepsy`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| AUDIT-C panel and total | LOINC 72109-2, 75626-2; positive at 4 or more for men, 3 or more for women | loinc.org; VA/DoD guideline | Unverified. Codes consistent in search summaries; 4/3 from the VA/DoD 2021 pocket card, but one summary says 5. Check the guideline PDF | Search-index summary of loinc.org only, 2026-11-26 |
| PC-PTSD-5 panel and total | LOINC 102010-6, 102017-1; positive at 3 or more | loinc.org; instrument source | Unverified. Codes consistent. **Cutoff finding:** current National Center for PTSD guidance recommends 4 by default and 3 for higher sensitivity (Bovin 2016). Owner decision needed | Search-index summary of loinc.org only, 2026-11-26 |
| Mental and behavioral chapter (problem list fallback) | Not in the research | ICD-10-CM | Verified: regex matches all 872 F leaf codes and nothing else (`mh.mental_behavioral_chapter`). Not used by any rule | CDC/NCHS ICD-10-CM tabular FY2027; agent check 2026-11-27 |
| C-SSRS risk level answers | Moderate or high counts (research) | loinc.org | Unverified. LA6751-7 Moderate and LA9193-9 High count; LA9194-7 Low does not (`cssrs_screener` answers) | Search-index summary of loinc.org only, 2026-11-26 |
| ASRS symptom checklist | LOINC 62750-5 | loinc.org | Corrected (pending loinc.org): 62750-5 is a PhenX protocol term, not a score | Search-index summary of loinc.org only, 2026-11-26 |
| ASRS-5 screener | No LOINC code found; cutoff 14 | loinc.org; instrument publication | Unverified. No LOINC code found; cutoff 14 (range 0-24) from the abstract | Search-index summary of loinc.org only, 2026-11-26 |
| PHQ-2 | No LOINC code confirmed; cutoff 3 | loinc.org; instrument source | Unverified. Search summaries show panel 55757-9 and total 55758-7; cutoff 3 from Kroenke 2003 abstract | Search-index summary of loinc.org only, 2026-11-26 |

## Priority 3: ADHD signals (Phases 4 and 5)

| Item | Value in the research | Source to check | Status | Checked |
|---|---|---|---|---|
| Stimulant-related disorders | F15.x, especially F15.8, F15.1x, F15.2x | ICD-10-CM | Corrected: there is no F15.8; F15.1, F15.2, F15.9. F15 includes caffeine (`sud.stimulant`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Alcohol involvement | F10.x; Y90.x; R78.0 | ICD-10-CM | Verified. Y90.0 (< 20 mg/100 ml) is effectively negative (`sud.alcohol`, `sud.blood_alcohol_level`, `sud.alcohol_in_blood`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Other substance use disorders | F11.x, F12.x, F14.x, F17.2x, F19.x | ICD-10-CM | Verified. F13, F16 and F18 are not in the list (`sud.other`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Motor-vehicle crash as driver | V40 to V49, V20 to V29, with the character that identifies the driver | ICD-10-CM | Verified: 4th character 0/5 for V40-V48, 0/4 for V49 and V20-V29; "(driver) (passenger)" codes excluded; all 72 driver codes matched and nothing else (`injury.motor_vehicle_driver`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Accidental injury | S00 to T34; W00 to X58 | ICD-10-CM | Corrected: S00-T34 contains T14.91 (suicide attempt), which is carved out; W00-X58 listed as explicit categories because of numbering gaps (`injury.injury_codes`, `injury.accidental_external_cause`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| TBI and history of TBI | S06.x; Z87.820 | ICD-10-CM | Verified; S06 includes S06.A (`injury.tbi`, `injury.history_tbi`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| PTSD | F43.10 to F43.12 | ICD-10-CM | Verified (`mh.ptsd`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Intermittent explosive disorder | F63.81 | ICD-10-CM | Verified (`mh.intermittent_explosive_disorder`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Depression and anxiety | F32, F33, F34.1, F41.1 | ICD-10-CM | Verified. F32 also holds F32.81 (premenstrual dysphoric disorder) and F32.A (`mh.depression`, `mh.generalized_anxiety`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Borderline personality disorder | F60.3 | ICD-10-CM | Verified (`mh.borderline_personality`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Insomnia and delayed sleep phase | G47.00, G47.01, G47.21, F51.0x | ICD-10-CM | Verified. G47.09 (other insomnia) exists and is not listed (`sleep.insomnia_delayed_phase`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Attention and executive-function symptoms | R41.840, R41.844 | ICD-10-CM | Verified. R41.840 carries Excludes1 F90.- (`symptom.attention_executive`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Legal problems | Z65.0 to Z65.3 | ICD-10-CM | Verified as exact codes (the Z65 prefix includes victim of crime) (`psychosocial.legal_problems`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Education and occupation problems | Z55.x, Z56.x | ICD-10-CM | Verified (`psychosocial.education_occupation`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Housing instability | Z59.0x | ICD-10-CM | Corrected: Z59.0x is homelessness; housing instability is Z59.81x (`psychosocial.homelessness`, `psychosocial.housing_instability`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Family history | Z81.8, Z82.x (mapping is an inference) | ICD-10-CM | Corrected: Z82.x covers physical disease and is dropped; family history of ADHD codes to Z81.8 (`family.mental_behavioral_history`) | CDC/NCHS ICD-10-CM tabular FY2027 and FY2026 (2026-04-01 update); agent check 2026-11-26, FY2027 re-check 2026-11-27 |
| Stimulant and non-stimulant ADHD medications | No list given; build an RxNorm ingredient value set | RxNorm | Verified: 7 stimulant and 2 non-stimulant ingredients (TTY IN, active), expanded to product codes (`med.adhd_stimulant`, `med.adhd_nonstimulant`). Guanfacine and clonidine left out (inference, ADR 0009) | NLM RxNav REST API, RxNorm release 02-Nov-2026 (API 3.1.358); agent check 2026-11-27 with `scripts/build_drug_classes.py` |
| Antidepressants | No list given; build an RxNorm ingredient value set | RxNorm | Verified: 28 ingredients (`med.antidepressant`). Trazodone, doxepin, amitriptyline, selegiline and milnacipran left out (inference, ADR 0009) | NLM RxNav REST API, RxNorm release 02-Nov-2026 (API 3.1.358); agent check 2026-11-27 with `scripts/build_drug_classes.py` |
| Sedative-hypnotics | No list given; build an RxNorm ingredient value set | RxNorm | Verified: 12 ingredients (`med.sedative_hypnotic`) | NLM RxNav REST API, RxNorm release 02-Nov-2026 (API 3.1.358); agent check 2026-11-27 with `scripts/build_drug_classes.py` |

## Priority 4: sensitive-data policy (Phase 6)

| Item | Value | Source | Status | Checked |
|---|---|---|---|---|
| Blood alcohol signal without Y90.0 | Y90.1-Y90.9 exact (`sud.blood_alcohol_level` 0.2.0) | ICD-10-CM | Verified (owner decision to exclude Y90.0, open question 10) | CDC/NCHS ICD-10-CM tabular FY2027; agent check 2026-11-27 |
| HIV | B20, Z21, R75 (`privacy.hiv`); used only by the privacy policy | ICD-10-CM | Verified | CDC/NCHS ICD-10-CM tabular FY2027; agent check 2026-11-27 |
| Sickle-cell disorders | D57 whole category, including trait D57.3 (`privacy.sickle_cell`); privacy policy only | ICD-10-CM | Verified (43 codes) | CDC/NCHS ICD-10-CM tabular FY2027; agent check 2026-11-27 |
| Security labels | v3-ActCode ETH, ETHUD, SUD, OPIOIDUD (substance use), HIV, SCA (`data/privacy.toml`) | HL7 terminology | Verified | terminology.hl7.org CodeSystem-v3-ActCode.json, version 11.0.0; agent check 2026-11-27 |

## Priority 5: experimental autism stub (Phase 8)

| Item | Value | Source | Status | Checked |
|---|---|---|---|---|
| Autism exclusion codes | F84.0, F84.5, F84.8, F84.9 exact (`care.autism_diagnosis`); F84.2 and F84.3 left out (owner decision 2026-11-27) | ICD-10-CM | Verified (4 leaf codes) | CDC/NCHS ICD-10-CM tabular FY2027; agent check 2026-11-27 |

The stub's placeholder signals reuse value sets verified above; no autism screening instrument (AQ-10, RAADS) is coded or verified.

## Follow-up verification

| # | Item | Needed by |
|---|---|---|
| F1 | ~~Compare the tabular file with a CDC/NCHS download; re-run against FY2027~~ Done 2026-11-27. Remaining: a human spot-check of the `safety.*` value sets (waived by the owner for development on 2026-11-27) | Release 1.0 (Phase 7 release blocker) |
| F2 | Verify every LOINC code on loinc.org directly (record the LOINC version), and the AUDIT-C, PC-PTSD-5, PHQ-2, PHQ-9 item 9 and ASRS-5 cutoffs against the primary publications. loinc.org blocks automated access and fhir.loinc.org needs a LOINC account; the owner chose on 2026-11-27 to leave LOINC unverified for now, so the PHQ-9 item 9 and C-SSRS checks are reported as not performed and no cutoff is applied | Before any LOINC-based check is active |
| F3 | Find how ASRS results are coded in FHIR data, since no LOINC score code was found. Phase 3 provides the means (a site maps its ASRS questionnaire in `data/site_codes/`); which codes real sites use is still open (open question 12) | Phase 5 |

## Rule logic that is inference, not evidence

These are design choices drawn from the research, not verified facts. They need the project owner's approval, and ideally a clinician's review, before release. Record the approval in the rule card.

| Item | Note |
|---|---|
| Combination rule (one high-weight signal with two modifiers, or two high-weight classes within about three years) | Described in the research as a starting heuristic to be calibrated |
| Antidepressant switch count as a modifier | Described as an untested inference |
| Occupational, educational and housing signals as modifiers | Described as inference |
| Safety gate look-back windows other than 90 and 365 days for discharge | Not specified in the research |
| Sex-specific thresholds | Recommended by the research; no values given |
| Drug class membership (which ingredients count) | Curated in `scripts/drug_class_spec.toml`; exclusions listed in ADR 0009 |
| Medication exposure parameters (30-day assumed supply, 30-day allowed gap, 30-day fill window) | Common pharmacoepidemiology choices, in `data/medication_timeline.toml` |
