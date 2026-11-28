# Tool reference

Generated from the contract snapshots in `tests/contract/snapshots/` by `uv run python scripts/build_tool_reference.py`; do not edit by hand. Tool contract version **0.5.0**.

Every tool is read-only. No result is a diagnosis: every patient tool returns `is_diagnosis: false` and a notice. The tool is not clinically validated.

| Tool | Title | Read-only |
|---|---|---|
| [`assess_referral_need`](#assess_referral_need) | Assess Referral Need | yes |
| [`check_existing_care`](#check_existing_care) | Check Existing Care | yes |
| [`check_safety_gate`](#check_safety_gate) | Check Safety Gate | yes |
| [`draft_referral_proposal`](#draft_referral_proposal) | Draft Referral Proposal | yes |
| [`get_medication_timeline`](#get_medication_timeline) | Get Medication Timeline | yes |
| [`get_mh_problem_list`](#get_mh_problem_list) | Get Mh Problem List | yes |
| [`get_psychosocial_context`](#get_psychosocial_context) | Get Psychosocial Context | yes |
| [`get_screening_history`](#get_screening_history) | Get Screening History | yes |
| [`get_server_info`](#get_server_info) | Get Server Info | yes |
| [`get_utilization_summary`](#get_utilization_summary) | Get Utilization Summary | yes |

## assess_referral_need

Suggest whether a clinician should consider referring a patient for formal adult ADHD screening, with the evidence behind it. Runs the safety gate first: if self-harm signals are found the result is address_safety_gate_first and no screening referral is suggested. Then checks whether the patient is already in ADHD care, reads diagnoses, psychosocial codes, visits and medications, and applies the versioned ADHD ruleset (one high-weight signal with two or more modifiers, or two high-weight signal classes, within 1095 days). Returns one of consider_referral_for_formal_screening, no_recommendation, address_safety_gate_first, already_in_care or insufficient_data; the safety gate; every signal checked with its FHIR resources; each rule and whether it fired; exclusions; notes; and data completeness. Read-only. The ruleset is a starting heuristic from published research, not clinically validated. The result is never a diagnosis; a clinician decides.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `condition` | string | no | Condition to assess: 'adhd'. An experimental stub such as 'autism' only when the server enables it; stubs are not for clinical use. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes |  |
| `basis` | list of object | no |  |
| `condition_to_screen` | string | yes |  |
| `data_completeness` | list of object | no |  |
| `decision_trace` | list of object | yes | Each rule, whether it fired, and the signals it counted |
| `excluded` | boolean or null | yes | Already in care for the condition: true, false, or null when unknown |
| `exclusions_checked` | list of object | no |  |
| `is_diagnosis` | `false` | no |  |
| `notes` | list of string | yes | Further points for the clinician, e.g. TBI overlap |
| `notice` | string | yes | The standard notice: a suggestion, never a diagnosis |
| `patient_id` | string | yes |  |
| `privacy` | object | yes | What the sensitive-data policy withheld or restricted |
| `recommendation` | `consider_referral_for_formal_screening` \| `no_recommendation` \| `address_safety_gate_first` \| `already_in_care` \| `insufficient_data` | yes |  |
| `recommendation_text` | string | yes | The recommendation in approved wording |
| `ruleset` | string | yes | Ruleset id, version and status; never clinically validated |
| `safety_gate` | object | yes | The gate's status agrees with its checks (owner decision 2026-11-27): * positive if and only if a check found a signal; * otherwise data_unavailable if a check failed; * otherwise clear only if every check ran; clear_limited_data is used when a check was not performed or the record holds too little data. |
| `scorer` | object or null | no |  |
| `signals_checked` | list of object | yes | Every catalog signal, present or not |
| `suggested_next_step` | string or null | no |  |
| `versions` | object | yes |  |

## check_existing_care

Check whether a patient is already in ADHD care, so a referral is not duplicated: an ADHD code (F90) on a Condition or as a medication reason; an ADHD referral, evaluation or care plan that is open or was completed within 365 days. Older, revoked or cancelled items are listed but do not count. Medication ordered for narcolepsy is reported separately and is never an exclusion. Returns excluded (true; false only when every check ran on complete data; otherwise null, meaning unknown), each check with its outcome and resources, and the care items found. Read-only. An ADHD code in the record is a prior entry, not a diagnosis by this tool.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes | The date the record was read as of |
| `care_items` | list of object | yes |  |
| `data_completeness` | list of object | yes | Each data category read: available, empty, incomplete or failed. An empty record is not a clean record. |
| `definition_version` | string | yes |  |
| `excluded` | boolean or null | yes | True if already in ADHD care; false only if every check ran on complete data and found nothing; null otherwise (unknown) |
| `exclusions_checked` | list of object | yes |  |
| `is_diagnosis` | `false` | no | Always false: these results are never a diagnosis |
| `narcolepsy` | object or null | yes |  |
| `notice` | string | yes | Standard notice on how to read these results |
| `patient_id` | string | yes |  |
| `privacy` | object | yes | What the sensitive-data policy withheld or restricted |
| `versions` | object | yes |  |

## check_safety_gate

Check a patient's FHIR record for self-harm signals that must be addressed before any screening referral: suicidal ideation, suicide attempt and self-harm codes (including intentional and undetermined-intent poisoning), history of suicidal behavior, PHQ-9 item 9, C-SSRS risk level, psychiatric inpatient or residential discharge within 365 days (90 days is highest priority) and active high-risk flags. Call it first, before any other assessment. Returns positive, clear, clear_limited_data or data_unavailable, every check with its outcome (found, not found, not performed, failed), and the FHIR resources behind each signal. A positive result carries fixed guidance on suicide risk evaluation and lethal-means counseling. Read-only. It reports what the record contains; it does not assess suicide risk and is not a diagnosis. clear_limited_data means some checks could not run or the record is empty, so absence of signals is not reassurance.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes | The date the record was read as of |
| `data_completeness` | list of object | yes | Each data category read: available, empty, incomplete or failed. An empty record is not a clean record. |
| `gate_definition_version` | string | yes | Version of the safety gate definition |
| `is_diagnosis` | `false` | no | Always false: these results are never a diagnosis |
| `notice` | string | yes | Standard notice on how to read these results |
| `patient_id` | string | yes |  |
| `privacy` | object | yes | What the sensitive-data policy withheld or restricted |
| `safety_gate` | object | yes | The gate's status agrees with its checks (owner decision 2026-11-27): * positive if and only if a check found a signal; * otherwise data_unavailable if a check failed; * otherwise clear only if every check ran; clear_limited_data is used when a check was not performed or the record holds too little data. |
| `versions` | object | yes |  |

## draft_referral_proposal

Draft a referral for formal adult ADHD screening from an assessment, for a clinician to review. Runs assess_referral_need; only when it suggests a referral, returns a FHIR R4 ServiceRequest with status 'draft' and intent 'proposal' that cites the evidence (reasonReference for conditions and observations, supportingInfo for visits and medications). Otherwise the draft is null and the reason is given. The draft is returned only: it has no id, is never stored and is never sent to the health record. Never drafts for an experimental condition. Not a diagnosis and not an order.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `condition` | string | no | Condition to assess: 'adhd'. An experimental stub such as 'autism' only when the server enables it; stubs are not for clinical use. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes |  |
| `draft` | object or null | yes | A FHIR R4 ServiceRequest with intent 'proposal' and status 'draft', or null when the assessment does not suggest a referral |
| `is_diagnosis` | `false` | no |  |
| `notice` | string | yes |  |
| `patient_id` | string | yes |  |
| `privacy` | object | yes | What the sensitive-data policy did. Always present, so a withheld category is never silent. |
| `recommendation` | string | yes |  |
| `stored` | `false` | no | Always false: the draft is returned only, never stored |
| `why_no_draft` | string or null | no |  |

## get_medication_timeline

Summarize a patient's exposure to the drug classes the referral rules use: stimulant and non-stimulant ADHD medications, antidepressants and sedative-hypnotics (RxNorm ingredient classes). Builds exposure periods from dispenses and medication statements (and from orders only when the record has no dispensing data), merging overlapping fills and splitting at gaps longer than 30 days; a missing days supply is assumed to be 30 days and flagged. Lists each order with its fill status (filled, not filled, unknown), the count of distinct agents per class (dose and brand variants count once), and marks medication ordered for narcolepsy. Medications in no class are counted, not named. Read-only. A medication in the record is not a diagnosis.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes | The date the record was read as of |
| `classes_checked` | list of string | yes |  |
| `data_completeness` | list of object | yes | Each data category read: available, empty, incomplete or failed. An empty record is not a clean record. |
| `definition_version` | string | yes |  |
| `distinct_agents` | list of object | yes | One entry per class checked |
| `drug_class_versions` | list of string | yes | '<class id> <version>' for each class |
| `exposures` | list of object | yes | By class, then ingredient, then start date |
| `is_diagnosis` | `false` | no | Always false: these results are never a diagnosis |
| `notice` | string | yes | Standard notice on how to read these results |
| `patient_id` | string | yes |  |
| `prescriptions` | list of object | yes |  |
| `privacy` | object | yes | What the sensitive-data policy withheld or restricted |
| `unclassified_records` | integer | yes | Medication records in no class checked (not named, to keep output focused) |
| `versions` | object | yes |  |

## get_mh_problem_list

List the mental health and related codes in a patient's FHIR Condition resources (ICD-10-CM), grouped into the families the referral rules use: ADHD codes, attention symptoms, depression, anxiety, PTSD, personality, substance use, sleep, narcolepsy, head injury, family history, and other chapter 5 codes. Each entry gives the code, first onset and recorded dates, the clinical status of its latest record (resolved entries are kept and labelled), an onset order, and every Condition it was found in; codes repeated across encounters appear once. Read-only. Use it to see what has been coded and in what order. A code listed here is a record entry, not a diagnosis made by this tool. Self-harm codes are reported by check_safety_gate.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes | The date the record was read as of |
| `data_completeness` | list of object | yes | Each data category read: available, empty, incomplete or failed. An empty record is not a clean record. |
| `definition_version` | string | yes |  |
| `families` | list of object | yes | Families with at least one coded condition, in a fixed order |
| `families_checked` | list of string | yes | Every family looked for |
| `is_diagnosis` | `false` | no | Always false: these results are never a diagnosis |
| `notice` | string | yes | Standard notice on how to read these results |
| `patient_id` | string | yes |  |
| `privacy` | object | yes | What the sensitive-data policy withheld or restricted |
| `versions` | object | yes |  |

## get_psychosocial_context

Report a patient's psychosocial context from coded data: homelessness or housing instability (Z59.0, Z59.81), legal problems (Z65.0-Z65.3), and education or employment problems (Z55, Z56), from Condition codes and coded social-history Observation values; and the date of separation from military service where the site records it. Each domain is found, not_found, or unknown when data could not be read; a missing separation date is unknown, never assumed. Coded data under-records these problems, so not_found is weak evidence of absence. Read-only. Not a diagnosis.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes | The date the record was read as of |
| `data_completeness` | list of object | yes | Each data category read: available, empty, incomplete or failed. An empty record is not a clean record. |
| `definition_version` | string | yes |  |
| `domains` | list of object | yes |  |
| `is_diagnosis` | `false` | no | Always false: these results are never a diagnosis |
| `military` | object | yes |  |
| `notice` | string | yes | Standard notice on how to read these results |
| `patient_id` | string | yes |  |
| `privacy` | object | yes | What the sensitive-data policy withheld or restricted |
| `versions` | object | yes |  |

## get_screening_history

Return a timeline of screening instrument results in a patient's FHIR record (PHQ-9, PHQ-2, C-SSRS risk level, AUDIT-C, PC-PTSD-5, ASRS-5 where coded), read from Observation panels, standalone results and QuestionnaireResponses. Each entry gives the date, score or coded answer, the cutoff that applies (sex-specific where the instrument has one) and whether it was applied, and the resource it came from. Unknown survey instruments are listed but not scored. A cutoff is applied only when its code and value are verified; code_verified and cutoff.status say so. Read-only. A score meeting a cutoff is a screening result for a clinician to review, not a diagnosis. No instrument item text is returned.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes | The date the record was read as of |
| `data_completeness` | list of object | yes | Each data category read: available, empty, incomplete or failed. An empty record is not a clean record. |
| `entries` | list of object | yes | Timeline, oldest first; undated last |
| `instruments_checked` | list of string | yes |  |
| `is_diagnosis` | `false` | no | Always false: these results are never a diagnosis |
| `notice` | string | yes | Standard notice on how to read these results |
| `patient_id` | string | yes |  |
| `privacy` | object | yes | What the sensitive-data policy withheld or restricted |
| `versions` | object | yes |  |

## get_server_info

Return this server's name, versions (server, tool contract, active referral ruleset) and its intended-use notice. Reads no patient data. Use it to check which versions produced a result. This server suggests when a clinician might consider referral for formal ADHD screening; it never diagnoses.

**Inputs**

None.

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `intended_use` | string | yes | The standard intended-use notice. |
| `ruleset_version` | string or null | yes | Active referral ruleset: id, version and status (draft until the project owner approves it). No ruleset is clinically validated. |
| `server_name` | string | yes |  |
| `server_version` | string | yes |  |
| `tool_contract_version` | string | yes |  |

## get_utilization_summary

Summarize a patient's health care use: emergency and urgent care visits, accidental injury visits (one per visit however many injury codes it carries; visits with a self-harm code are not counted as accidental), motor-vehicle crashes as driver (passenger codes do not count), and psychiatric inpatient or residential stays. Counts each in windows of 0-30, 31-180 and 181-730 days before the as-of date, and reports overall record volume (all encounters and distinct visit days) so frequent attendance can be told apart from specific events. Missed appointments are not read yet. Read-only. A visit in the record is not a diagnosis.

**Inputs**

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) or null | no | Read the record as of this date (YYYY-MM-DD); data dated later is ignored. Defaults to today. Must not be in the future. |
| `patient_id` | string | yes | FHIR id of the Patient resource: 1 to 64 letters, digits, '-' or '.' |

**Output** (top-level fields)

| Field | Type | Required | Description |
|---|---|---|---|
| `as_of` | string (date) | yes | The date the record was read as of |
| `counts` | list of object | yes | Events per window before the as-of date. any_encounter is the overall record volume, so a rule can avoid simply rewarding frequent attendance |
| `data_completeness` | list of object | yes | Each data category read: available, empty, incomplete or failed. An empty record is not a clean record. |
| `definition_version` | string | yes |  |
| `events` | list of object | yes | Every event found, oldest first (undated last), by kind |
| `is_diagnosis` | `false` | no | Always false: these results are never a diagnosis |
| `missed_appointments` | `"not_read"` | yes | Missed appointments are recorded in Appointment resources, which this server does not read yet |
| `notice` | string | yes | Standard notice on how to read these results |
| `patient_id` | string | yes |  |
| `privacy` | object | yes | What the sensitive-data policy withheld or restricted |
| `psychiatric_stays_checked` | boolean | yes | False when the site maps no psychiatric encounter codes |
| `versions` | object | yes |  |
| `visit_days_730` | integer | yes | Distinct days with any encounter in 730 days |

## Resources

| URI | Title | Description |
|---|---|---|
| `adhd-mcp://drug-classes` | Drug classes | RxNorm drug classes (ADR 0009): ingredients with provenance and the number of product codes each covers. |
| `adhd-mcp://instruments` | Screening instrument metadata | Instrument names, codes and cutoffs with verification status. No item text is included (some instruments are copyrighted). |
| `adhd-mcp://intended-use` | Intended use statement | What this server is for and not for. It never diagnoses. |
| `adhd-mcp://rulesets/adhd` | Active ADHD referral ruleset | Ruleset adhd 1.0.0 (draft): rules, exclusions and citations. Not clinically validated. |
| `adhd-mcp://signal-catalogs/adhd` | ADHD signal catalog | Signal catalog adhd.signal_catalog 1.0.0: each signal's weight, definition, window, supplying tool and evidence. |
| `adhd-mcp://value-sets` | Value set index | Every packaged value set: id, version and title. |
| `adhd-mcp://value-sets/{value_set_id}` | Value set | One value set with every entry and its verification provenance. |

## Prompts

| Prompt | Arguments | Description |
|---|---|---|
| `explain_recommendation` | `patient_id` | Explain, for a clinician, why assess_referral_need gave its result for a patient, from the evidence it returned. |
| `summarize_checks` | `patient_id` | Summarize which checks an assessment ran, which could not run, and which data was missing or incomplete. |
