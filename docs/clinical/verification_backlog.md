# Verification Backlog

The research report was written with full-text access blocked for many sources, so most codes and cutoffs are marked unverified there. **Nothing on this list may be used in an active ruleset until it is checked against an authoritative source and marked verified here.** The terminology loader enforces this in strict mode.

The full list of items to verify, including effect sizes and regulatory facts, is in the research report under "Evidence limitations and items to verify". This file tracks only what the planned ADHD ruleset and safety gate need.

## How to verify

1. Check the item against the authoritative source named below.
2. Record the source, its version or date, the date checked and who checked it.
3. Set the status. If the item is wrong, record the correct value and correct the data file in the same pull request.

Authoritative sources: the CDC ICD-10-CM browser and current fiscal-year tabular list for diagnosis codes; loinc.org for LOINC; the NLM RxNorm browser for medications; instrument manuals or the publisher for cutoffs.

**Status values:** Unverified, Verified, Corrected, Dropped.

## Priority 1: safety gate (needed for Phase 3)

| Item | Value in the research | Source to check | Status | Checked (who, when, source version) |
|---|---|---|---|---|
| Suicidal ideation | ICD-10-CM R45.851 | ICD-10-CM | Unverified | |
| Suicide attempt | T14.91XA and related characters; external causes X71 to X83 | ICD-10-CM | Unverified | |
| Intentional self-poisoning | T36 to T65 with sixth character 2; undetermined intent with 4 | ICD-10-CM | Unverified | |
| Non-suicidal self-harm | R45.88; history Z91.52 | ICD-10-CM | Unverified | |
| History of suicidal behavior | Z91.51 | ICD-10-CM | Verified in research (CMS tables); re-confirm for the current year | |
| PHQ-9 item 9 | LOINC 44260-8; positive at 1 or more | loinc.org | Unverified | |
| PHQ-9 panel and total | LOINC 44249-1, 44261-6 | loinc.org | Unverified | |
| C-SSRS screener panel and risk level | LOINC 93373-9, 93374-7 | loinc.org | Unverified | |
| Psychiatric inpatient and residential encounters | No codes given; define by encounter class, type and service | US Core and local server | Unverified | |

## Priority 2: exclusions and screening history (Phase 3)

| Item | Value in the research | Source to check | Status | Checked |
|---|---|---|---|---|
| ADHD diagnosis | F90.x | ICD-10-CM | Unverified | |
| Narcolepsy | G47.4x | ICD-10-CM | Unverified | |
| AUDIT-C panel and total | LOINC 72109-2, 75626-2; positive at 4 or more for men, 3 or more for women | loinc.org; VA/DoD guideline | Unverified | |
| PC-PTSD-5 panel and total | LOINC 102010-6, 102017-1; positive at 3 or more | loinc.org; instrument source | Unverified | |
| ASRS symptom checklist | LOINC 62750-5 | loinc.org | Unverified | |
| ASRS-5 screener | No LOINC code found; cutoff 14 | loinc.org; instrument publication | Unverified | |
| PHQ-2 | No LOINC code confirmed; cutoff 3 | loinc.org; instrument source | Unverified | |

## Priority 3: ADHD signals (Phases 4 and 5)

| Item | Value in the research | Source to check | Status | Checked |
|---|---|---|---|---|
| Stimulant-related disorders | F15.x, especially F15.8, F15.1x, F15.2x | ICD-10-CM | Unverified | |
| Alcohol involvement | F10.x; Y90.x; R78.0 | ICD-10-CM | Unverified | |
| Other substance use disorders | F11.x, F12.x, F14.x, F17.2x, F19.x | ICD-10-CM | Unverified | |
| Motor-vehicle crash as driver | V40 to V49, V20 to V29, with the character that identifies the driver | ICD-10-CM | Unverified | |
| Accidental injury | S00 to T34; W00 to X58 | ICD-10-CM | Unverified | |
| TBI and history of TBI | S06.x; Z87.820 | ICD-10-CM | Unverified | |
| PTSD | F43.10 to F43.12 | ICD-10-CM | Unverified | |
| Intermittent explosive disorder | F63.81 | ICD-10-CM | Unverified | |
| Depression and anxiety | F32, F33, F34.1, F41.1 | ICD-10-CM | Unverified | |
| Borderline personality disorder | F60.3 | ICD-10-CM | Unverified | |
| Insomnia and delayed sleep phase | G47.00, G47.01, G47.21, F51.0x | ICD-10-CM | Unverified | |
| Attention and executive-function symptoms | R41.840, R41.844 | ICD-10-CM | Unverified | |
| Legal problems | Z65.0 to Z65.3 | ICD-10-CM | Unverified | |
| Education and occupation problems | Z55.x, Z56.x | ICD-10-CM | Unverified | |
| Housing instability | Z59.0x | ICD-10-CM | Unverified | |
| Family history | Z81.8, Z82.x (mapping is an inference) | ICD-10-CM | Unverified | |
| Stimulant and non-stimulant ADHD medications | No list given; build an RxNorm ingredient value set | RxNorm | Unverified | |
| Antidepressants | No list given; build an RxNorm ingredient value set | RxNorm | Unverified | |
| Sedative-hypnotics | No list given; build an RxNorm ingredient value set | RxNorm | Unverified | |

## Rule logic that is inference, not evidence

These are design choices drawn from the research, not verified facts. They need the project owner's approval, and ideally a clinician's review, before release. Record the approval in the rule card.

| Item | Note |
|---|---|
| Combination rule (one high-weight signal with two modifiers, or two high-weight classes within about three years) | Described in the research as a starting heuristic to be calibrated |
| Antidepressant switch count as a modifier | Described as an untested inference |
| Occupational, educational and housing signals as modifiers | Described as inference |
| Safety gate look-back windows other than 90 and 365 days for discharge | Not specified in the research |
| Sex-specific thresholds | Recommended by the research; no values given |
