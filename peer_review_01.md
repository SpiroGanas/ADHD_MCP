# Peer Review 01

| | |
|---|---|
| Date | 2026-11-27 |
| Reviewed | `main` at `9e14e02` (merge of PR #7): server 1.0.0rc1, tool contract 0.4.0, ADHD ruleset 1.0.0 (draft) |
| Reviewer | Claude Code agent, at the project owner's request. Not a clinician and not counsel |
| Scope | All of `src/adhd_mcp` (read in full), the clinical data files, the test suite, CI and packaging, and the documentation |
| Changes made | None to code, tests or data. This file and a status.md update only |

## How to read this

Findings have an identifier, a severity and a confidence.

- **Severity** says what happens if the software is used as it stands. *High*: the output can be wrong or misleading in a way a clinician could act on, or a safety control can be silently bypassed. *Medium*: wrong or fragile behavior with a limited effect, or a control that is weaker than the documents say. *Low*: small defects and hardening.
- **Confirmed** means I reproduced the behavior with a read-only experiment on synthetic data (Appendix A) or read both sides of a contradiction. **Read** means I found it by reading and did not run it.
- Clinical findings are questions for a clinical reviewer, not clinical judgments. I report what the software does; whether it should is theirs to decide.

Many limits are already written down honestly in [docs/limitations.md](docs/limitations.md), the rule cards and the [risk register](docs/clinical/risk_register.md). I do not repeat those as findings unless the behavior goes further than the document says, or I think the accepted position should be reopened.

## Summary

The engineering is careful and unusually disciplined for its age: a narrow read-only port, clinical knowledge held in versioned data, strict loading that refuses unverified codes, a safety gate that fails closed on unreadable data, outputs that cite resources, and 2,300 passing tests at 98.65% branch coverage. The documentation is candid about what is not known.

The main risk is not in the code quality. It is that **the project's safeguards are almost entirely self-referential**. One AI agent wrote the research summary, the rules, the value sets, the tests, the labelled cohort, the evaluation, the threat model and the safety reviews, and marked 401 clinical entries "verified", in about 30 hours. No pull request has a recorded human review; the pull request that added the safety gate was open for under six minutes. The tests prove the software does what its author intended. They cannot show that the intent is right, and this review found several places where it is doubtful.

The findings that matter most:

1. **The safety gate has two silent gaps.** A recent suicidal ideation or suicide attempt recorded only in SNOMED CT is reported as "not found", with the Condition category "available" and no warning (S1). And a PHQ-9 item 9 score of 3 recorded two weeks earlier, which the server reads and displays, does not stop a referral suggestion, because its LOINC code is "unverified" (S2).
2. **The look-back window does nothing for most real conditions.** Any condition not marked resolved counts as current forever. A 2010 blood-alcohol code and 2008 to 2009 depression and insomnia codes give "consider referral", each with the reason "Found within 1095 days" (C1).
3. **Related findings are counted as independent ones.** One emergency visit for a crash with a blood-alcohol code fires the "two high-weight classes" rule by itself. One fracture plus its follow-up visit is "two or more accidental injuries" (C2).
4. **Obvious context is ignored.** A child's record gets a suggestion for *adult* ADHD screening (C3). A patient with current methylphenidate dispenses and no F90 code is reported as "not in care" and gets the suggestion (C4).
5. **A withheld category is reported as absence.** Under a `withhold` policy the substance-use signals read "Not found in the record" and the result is `no_recommendation`, not `insufficient_data` (P1).
6. **Real-world viability is untested.** Every search reads a patient's whole history with no filter (all laboratory results and vital signs, to find a handful of social-history codes), performance was measured on 14 tiny personas, and one malformed timestamp anywhere in a patient's conditions blocks that patient's assessment (D1, D3).

None of this reaches a patient today: the software has only read synthetic data. But `1.0.0rc1` and "release candidate" say more than the evidence supports. My recommendation is in [Recommended order of work](#recommended-order-of-work): fix the confirmed defects test-first, get independent human and clinical review, and run a real model through the harness, before any 1.0.0 tag.

## What was done

- Read `status.md`, the plan, the rule cards, limitations, threat model, risk register, ADRs 0011 to 0014 and the integration notes.
- Read every module under `src/adhd_mcp` and every clinical data file except the long generated drug-class product lists.
- Ran `./scripts/check`: ruff, format, mypy, the synthetic-data guard and pytest all pass (2,300 passed, 287 integration tests deselected, coverage 98.65%).
- Wrote 17 small read-only experiments against the public tool interface with synthetic resources (Appendix A). They are not committed.
- Read the pull request history through the GitHub API.
- Two further read-only passes covered the test suite and CI (including a 30-mutant probe on a scratch copy), and the consistency of documents with data files. I checked their main claims before including them.

Not done: the integration tests locally (no Docker daemon here; they passed in CI on this pull request), any run against a real FHIR server, a check of the research report against primary literature, and any legal or regulatory assessment.

## Strengths

These are worth keeping as the project changes.

- **Fail-closed data handling.** A failed, partial or unsupported read is never treated as "nothing found": `evidence/common.py` separates `failed`, `incomplete`, `not_supported` and `empty`, and the gate becomes `data_unavailable` (`evidence/safety_gate.py:529`). Malformed Bundles fail the search instead of shortening it.
- **Invariants in the type system.** `models/domain.py` refuses a positive gate without evidence, a referral result with an unavailable gate, and a referral without a cited basis. `is_diagnosis` is `Literal[False]`.
- **Clinical content as data, strictly loaded.** Value sets, drug classes, instruments, cutoffs, wording and the ruleset are versioned TOML. Unverified LOINC codes really are refused, at the cost of losing the PHQ-9 and C-SSRS checks; that was the honest choice.
- **A narrow port.** `FhirReadPort` has `read_patient` and `search` only. Next links are pinned to the configured origin, redirects are not followed, patient ids are validated before they reach a URL, and the caller's token is never forwarded.
- **No free text crosses the boundary.** Normalization drops narrative and `text`; output labels come from the project's own value sets. The poisoned-twin injection test is a good design.
- **The safety gate reads around the privacy filter**, so a withhold policy cannot hide a self-harm signal.
- **Honest documentation.** The sex-balance review reports a result unfavourable to the ruleset (8 of 40 against 32 of 32) instead of burying it.

## Findings at a glance

| ID | Severity | Finding | Confidence |
|---|---|---|---|
| S1 | High | Conditions coded only in SNOMED CT (or ICD-10-CM without the dot) are silently "not found" by the safety gate and every signal | Confirmed |
| S2 | High | The safety gate that can run today is seven ICD-10-CM code checks. A recorded PHQ-9 item 9 score of 3 does not stop a suggestion, and a site has no supported way to supply its code mapping | Confirmed |
| C1 | High | The look-back window is ineffective for unresolved conditions, and the reason text states a recency that is not true | Confirmed |
| C2 | High | Correlated findings are counted as independent high-weight signals | Confirmed |
| C3 | High | No age or vital-status check: a child's record gets an adult screening suggestion | Confirmed |
| C4 | High | Current ADHD medication is neither an exclusion nor a note | Confirmed |
| C5 | Medium | Prescriptions that were never filled count toward "three or more distinct antidepressants"; the documents say "with exposure" | Confirmed |
| C6 | Medium | The expected flag rate is unknown and likely high: any alcohol code, nicotine dependence, depression and insomnia are enough | Read |
| C7 | Medium | Value-set scope questions for the clinical reviewer (drivers of pickups and vans, anxiety codes, unconfirmed diagnoses) | Confirmed in part |
| P1 | High | Under a `withhold` policy, withheld signals read "Not found in the record" and the result is `no_recommendation` | Confirmed |
| P2 | Medium | The default `cite` policy still discloses the protected category beside the resource reference | Confirmed |
| P3 | Medium | No patient-level authorization: a token with the scope can read any patient | Read |
| P4 | Medium | Authentication failures are not audited; a scope denial is audited as `internal_error` | Confirmed |
| P5 | Low | Plain http is accepted for a non-local FHIR server and for the public URL; the audit file takes the default file mode | Confirmed |
| D1 | High | Every search is unfiltered and unbounded in time: whole-history reads of all Observations | Confirmed |
| D2 | Medium | A 404 from a search crashes the tool with a masked internal error | Confirmed |
| D3 | Medium | One timestamp without a time zone makes a whole category unreadable and blocks the patient's assessment | Confirmed |
| D4 | Low | Start-up errors outside `ConfigError`; unvalidated site-code name; token response not validated | Confirmed |
| G1 | High | No independent review: one author for rules, tests, evaluation and safety review; no recorded human review on any pull request | Confirmed |
| G2 | High | "Verified" means verified by the authoring agent; the human spot-check is waived | Confirmed |
| G3 | Medium | The version label and "release candidate" overstate readiness | Read |
| G4 | Low | status.md is stale | Confirmed |
| T1 | High | The tests check the author's intent, so they cannot find an error of intent; the cohort's labels follow the rule | Confirmed |
| T2 | Medium | Property tests generate only inputs the code already understands | Confirmed |
| T3 | Medium | Missing cases: 404 on search, audit of refusals, `withhold` through the assessment, start-up errors | Confirmed |
| T4 | Medium | Never exercised: a real model, a real server, a realistic record | Acknowledged in part |
| T5 | Low | CI and packaging hardening; the plan's 100% branch rule for rules and gate is not enforced | Confirmed |
| T6 | Medium | Scope enforcement is tested for one tool of ten | Confirmed |
| T7 | Medium | The synthetic-data guard is easy to pass with real-looking data | Confirmed |
| T8 | Medium | Untested lines that matter (privacy reason codes and redaction, audit on failure) | Confirmed |
| T9 | Low | The history does not show tests written before code | Confirmed |
| T10 | Low | Tests read the shell environment; the report staleness check ignores engine changes | Confirmed |
| X1 | Medium | The evidence trail is weaker than the rule card's "Inference?" column says | Confirmed in part |
| X2 | Medium | Hash pinning covers `ruleset.toml` only; the catalog and value sets can change under a "released" ruleset | Confirmed |
| X3 | Medium | Statements stronger than the evidence (threat model, README, risk register) | Confirmed |
| X4 | Medium | architecture.md describes an earlier design | Confirmed |
| X5 | Low | Exclusion documents and data disagree | Confirmed |
| X6 | Low | Stale numbers and statuses | Confirmed |
| X7 | Medium | Gaps in the rule cards: equity, falls in older adults, history-of codes, differential notes, annual code updates | Read |

## Safety gate

### S1. Conditions without a dotted ICD-10-CM code are invisible, and nothing says so (High, confirmed)

**Evidence.** All 344 value-set entries use the system `http://hl7.org/fhir/sid/icd-10-cm`. `ValueSetEntry.matches` (`terminology/value_sets.py:58`) returns false for any other system. Nothing counts or reports conditions whose codings match no known system.

Experiment E8: a patient with two active Conditions dated within the last three months, coded only in SNOMED CT (6471006 suicidal thoughts, 82313006 suicide attempt). `check_safety_gate` returns every coded check `not_found`, Condition `available` with 2 records, 0 skipped, no warnings. The status is `clear_limited_data` only because the LOINC checks are not performed; once LOINC is verified the same record would be a plain `clear`. Experiment E8b: `R45851` (no dot) gives the same result. The dotless case is in the limitations; the SNOMED case is in no document.

**Why it matters.** US Core binds `Condition.code` to SNOMED CT as well as ICD-10-CM, and problem-list entries are commonly SNOMED CT. [docs/integration/lighthouse.md](docs/integration/lighthouse.md) line 54 records that Lighthouse returns "SNOMED CT and ICD-10-CM codings" and concludes "the main signal source works as designed". That conclusion is not supported. This is the one path found where the central safety control passes a record it should stop, with no completeness warning to alert the reader. It breaks the project's own rule that an unread record must never look like a clean one (risk C8).

**Recommendation.**
1. Make it loud first. Count Conditions that carry no coding in a system the value sets cover. If any exist, mark the Condition category `incomplete` with a warning such as `unrecognized_coding`; the gate then fails closed through the existing path. This needs no new clinical content.
2. Normalize ICD-10-CM codes that arrive without the dot (insert it after the third character) in `fhir/codes.py`. ADR 0007 deferred this to Phase 8 and Phase 8 closed without it.
3. Then decide with a clinician whether to add SNOMED CT value sets for the safety concepts, or to translate through a terminology service.
4. Correct the Lighthouse note.

### S2. Most of the gate cannot run on any real server, and a recorded positive PHQ-9 item 9 does not stop a suggestion (High, confirmed; partly acknowledged)

**Evidence.** Of eleven checks, PHQ-9 item 9 and C-SSRS are "not performed" (LOINC unverified, acknowledged). Psychiatric discharge and the high-risk flag need a site code mapping. `ADHD_MCP_SITE_CODES` is passed to `load_site_codes` (`tools/context.py:105`, `terminology/site_codes.py:116`), which loads only a file inside the installed package, and only `synthetic.toml` exists. `load_site_codes_file` exists but nothing calls it outside tests. The deployment guide tells a site to supply a mapping but there is no supported way to do it short of rebuilding the package.

Experiment E17: a patient with an Observation coded LOINC 44260-8 (PHQ-9 item 9) with value 3, dated two weeks before the as-of date, plus an alcohol, a depression and an insomnia code. `get_screening_history` recognizes the result and lists item 9 with score 3. `assess_referral_need` returns `consider_referral_for_formal_screening` with the gate `clear_limited_data`; the item 9 check says "Not performed: its codes or cutoffs are not verified yet."

**Why it matters.** The rule "an unverified fact is not used" is being applied in the less safe direction. For a signal, not using an unverified code loses a suggestion. For the gate, not using it lets a referral suggestion pass a record that the server itself has just read as holding a self-harm screening answer. The server recognizes the code well enough to display it, but not well enough to stop on it. Separately, recent psychiatric discharge is called the highest-priority signal in the gate's own data file and cannot run without a site mapping. On a real server the gate is seven diagnosis-code checks. `clear_limited_data` lets a suggestion through (`orchestration/assess.py:93`), so "limited" will be the permanent state and readers will stop noticing it.

**Recommendation.**
1. Decide, with the owner and a clinician, that the gate fails safe: when a record holds any result under a code the instrument file lists for a gate check, verified or not, the check is not "not performed". It either counts or makes the gate `data_unavailable`. No persona covers this case today; add one.
2. Treat LOINC verification (open question 14) as a blocker for 1.0.0, not a follow-up.
3. Add a file-path setting for site codes, validated like `ADHD_MCP_PRIVACY_POLICY`.
4. Consider saying in the recommendation text itself, not only in the check list, when the discharge and flag checks did not run.

## Clinical logic

### C1. The window does not limit unresolved conditions, and the reason text is untrue (High, confirmed)

**Evidence.** `_entry_interval` (`rules/signals.py:68`) treats an entry as open-ended unless its latest record has clinical status `resolved` or `inactive` (`evidence/problem_list.py:25`). Abatement dates are parsed but never used. The finding's reason is the fixed text "Found within {window} days." (`rules/signals.py:97`).

Experiment E1: three Conditions with no clinical status: Y90.3 recorded 2010-03-01, F32.9 recorded 2009, G47.00 recorded 2008; as-of 2026-06-15. Result: `consider_referral_for_formal_screening`, rule `high_with_modifiers`, each signal "Found within 1095 days." The same holds with status `active` (E1b).

**Why it matters.** The rule card does say "a condition counts if it is active (open-ended)", and a test pins it (`test_an_active_condition_recorded_long_ago_is_current`), so this is designed. I think the design is wrong for real data, for three reasons. Encounter diagnoses are rarely ever marked resolved, so for most records the 1,095-day window is not applied at all. Y90 and R78.0 describe a single measurement on a single day; they are not ongoing problems and cannot sensibly be "active" sixteen years later. And the reason text tells the clinician something false about recency, in the field meant to let them check the basis. The ruleset's citation says signals should appear "within about three years".

**Recommendation.** Ask the clinical reviewer to choose a rule; for example: an encounter diagnosis counts by its latest recorded date; only a problem-list item with an active status is open-ended; event codes always count by date. Use `abatement` when present. Whatever is chosen, replace the fixed reason with the actual dates ("last recorded 2010-03-01; counted as current because not marked resolved").

### C2. Correlated findings are counted as independent signals (High, confirmed)

**Evidence.** `decide` (`rules/engine.py:20`) counts present high-weight signals. Nothing checks that they come from different events.

- E2: one emergency encounter with V43.52XA (driver), Y90.4 (blood alcohol) and S06.0X0A. Result: `crash_as_driver` and `alcohol_involvement` are both present, `two_high_classes` fires, and the suggestion is made on that single visit with no modifier.
- E2b: two emergency visits for crashes as driver, nothing else. Each crash is also an injury visit, so `crash_as_driver` and `repeated_accidental_injury` are both present and `two_high_classes` fires.
- E14: one fracture seen in the emergency department (S52.501A), then a re-check ten days later (S52.501D, subsequent encounter). That is "2 found within 730 days", so `repeated_accidental_injury` is present. `injury.injury_codes` matches by prefix and ignores the seventh character.

**Why it matters.** The rule says "two or more high-weight signal *classes*". Two views of one event are not two classes of evidence. The rule card's evaluation section does not mention this, and the cohort does not test it.

**Recommendation.** Count injury episodes, not visits: require the initial-encounter seventh character where the code has one, or merge visits for the same code family within a short interval. Do not let one encounter supply two high-weight signals. Decide whether a crash visit counts toward both the crash signal and the injury count. Add personas for each case with the outcome a clinician expects.

### C3. No age or vital-status check (High, confirmed)

**Evidence.** `birthDate` is normalized (`fhir/normalize.py:141`) and never used. Experiment E7: a patient born 2017 with three matching codes gets "Consider referral for formal ADHD screening" and the next step "Offer an adult ADHD screen (for example the ASRS-5)". `deceasedBoolean` and `deceasedDateTime` are not read.

**Why it matters.** The intended-use statement, the tool description and the ASRS-5 next step are all for adults. "No age logic is applied" is in the limitations, but an out-of-scope patient should get an out-of-scope answer, not a recommendation with a caveat somewhere else. The data is already in hand.

**Recommendation.** Add an outcome for records outside the intended population (under 18 at the as-of date, birth date missing, or deceased) and return it before any rule runs. This changes the output schema, so it needs an owner decision and a contract version.

### C4. Current ADHD medication is ignored by the exclusion check (High, confirmed)

**Evidence.** `check_existing_care` looks for an F90 code on a Condition or as a medication *reason* (`evidence/existing_care.py:236`), and for mapped referrals, procedures and care plans. It does not look at the medication itself. Experiment E4: an active methylphenidate order with a matching dispense six weeks before the as-of date, no F90 code. Result: `excluded: false`, `consider_referral_for_formal_screening`, and no note about the medication. The timeline tool classifies the drug correctly as `med.adhd_stimulant`; the assessment does not use it.

**Why it matters.** A diagnosis made elsewhere, coded in SNOMED CT (see S1), or simply not coded is common. Suggesting a screening referral for someone currently dispensed an ADHD medication is the kind of visible error that costs a tool its users' trust. The rule card treats narcolepsy medication carefully but is silent on this case.

**Recommendation.** Ask the clinical reviewer whether current exposure to an ADHD medication, without a narcolepsy reason, should exclude, make `excluded` unknown, or add a note. Any of the three is better than silence.

### C5. Unfilled prescriptions count as distinct antidepressants (Medium, confirmed)

**Evidence.** The catalog header says "distinct ingredients of drug_class with exposure in the window", and the rule card says "with exposure in 1095 days". `assemble_medication_timeline` adds every prescription's date to an agent's dates whatever its fill status (`evidence/medication_timeline.py:284`). Experiment E3: three orders (sertraline, fluoxetine, bupropion), all `not_filled` against complete dispensing data, no exposure periods. Result: `med.antidepressant` count 3, `multiple_antidepressants` present, rule fired.

**Why it matters.** The signal is meant to stand for repeated treatment change. Orders never filled are different evidence. The owner's decision B1 covered servers with no dispenses at all; this is the case where dispenses exist and contradict the orders. Separately, the count ignores indication: bupropion for smoking cessation, duloxetine for pain and nortriptyline for neuropathy all count.

**Recommendation.** Make the code and the documents agree. Either count only agents with an exposure period when dispensing data is complete, or change the wording to "ordered or taken".

### C6. Expected flag rate is unknown and probably high (Medium, read)

**Evidence.** `sud.alcohol` is the whole F10 family at high weight. `sud.other` includes F17.2, nicotine dependence, as a modifier (`data/value_sets/sud.other.toml:42`). Depression and insomnia are modifiers. So any alcohol-related code plus nicotine dependence plus a depression code fires `high_with_modifiers`, and under C1 none of them needs to be recent. Risk C5 records "real-world flag rate unknown". The cohort cannot estimate it: its mix of presentations is designed, not sampled.

**Why it matters.** Evaluation capacity is the scarce resource the tool spends. If a large share of a mental-health caseload is flagged, the suggestion carries no information.

**Recommendation.** Before release, estimate the flag rate from published comorbidity prevalence or from a population generator such as Synthea, and put the number with its assumptions in the rule card. Ask the clinical reviewer specifically about nicotine dependence as a modifier. The deployment guide's silent-mode period is the right final check; this is the cheap first one.

### C7. Value-set scope questions for the clinical reviewer (Medium)

- **Drivers.** `injury.motor_vehicle_driver` covers V40 to V49 (car) and V20 to V29 (motorcycle). Drivers of pickup trucks and vans (V50 to V59) and heavy vehicles (V60 to V69) are not included. Experiment E15: V53.5XXA gives no crash signal. The signal's title is "Motor-vehicle crash as driver". No document mentions the omission. (Confirmed.)
- **Anxiety.** `mh.generalized_anxiety` is F41.1 only. F41.9 (unspecified) and F41.0 (panic) do not count, although the signal exists partly to catch presentations first labelled as anxiety, and the ruleset already under-flags internalizing presentations. (Read.)
- **Unconfirmed diagnoses.** Conditions with verification status `provisional`, `differential` or `unconfirmed` count the same as confirmed ones, for signals and for the ADHD exclusion. Only `refuted` and `entered-in-error` are dropped (`fhir/normalize.py:43`). A refuted ADHD diagnosis, which shows an evaluation took place, leaves no trace. (Read.)
- **As-of dates.** `as_of` filters by date, but statuses are today's. A condition resolved after the as-of date is treated as resolved at it. This matters if `as_of` is ever used for back-testing. (Read.)

## Privacy and security

### P1. A withheld category is reported as "not found" (High, confirmed)

**Evidence.** With `withhold`, `PrivacyPort.search` drops the resources before assembly (`privacy/policy.py:178`). The orchestration then sees a complete Condition category. `apply_privacy` relabels the category `withheld` only after the decision is made (`tools/common.py:138`). Experiment E6: F15.20, F10.20, F32.9, G47.00 with `substance_use = "withhold"`. Result: `no_recommendation`; the three substance-use signals each say "Not found in the record."; Condition is `withheld`; the privacy note says 2 records withheld.

**Why it matters.** Two of the four high-weight signals were not evaluated, yet the result is `no_recommendation`, not `insufficient_data`. A read failure in the same category would give `insufficient_data`. The per-signal reason is false. The intended-use statement says "missing or withheld data is always disclosed"; at the level of the signal it is contradicted.

**Recommendation.** Tell the orchestration which signals depend on a withheld category. Give those signals the reason "Not checked: withheld by the privacy policy" and treat their source as unreadable, so a rule that could not be evaluated leads to `insufficient_data`.

### P2. `cite` still discloses the category (Medium, confirmed; residual risk acknowledged)

**Evidence.** Under the default policy the code is replaced by `restricted`, but the output still pairs the signal title ("Stimulant-related disorder", "Alcohol involvement") with `Condition/<id>` and a date (E6b). This is the documented design.

**Why it matters.** Under 42 CFR Part 2 and 38 U.S.C. 7332 the protected fact is that the record exists, not the fourth character of its code. The default therefore protects little, while its name suggests otherwise. Risk P3 leaves the legal review to "a real site"; meanwhile a site that does nothing gets `cite`. Classification is also by ICD-10-CM code and security label only: AUDIT-C results, drug screens, and medications such as buprenorphine or antiretrovirals are not recognized (noted in the Lighthouse review).

**Recommendation.** Do not ship a permissive default for real servers. When `ADHD_MCP_FHIR_BASE_URL` points to a non-local host, require an explicit `ADHD_MCP_PRIVACY_POLICY` and refuse to start without one. Say plainly in the configuration guide what `cite` does and does not hide.

### P3. No patient-level authorization (Medium, read)

**Evidence.** A valid token with the right scope may name any patient id (`tools/common.py`, `server.py:37`). The server then uses its own system-level FHIR credentials. With Lighthouse it mints a patient-scoped token for whichever ICN the caller supplied (`fhir/lighthouse.py`). The threat model covers over-scoped access (T5) and token reuse across patients inside the server (T18), but not a legitimate caller reading a patient they have no relationship with.

**Recommendation.** Add this threat to the threat model as an explicit trust assumption, with the audit trail as the compensating control. Consider an optional check of a patient or launch-context claim in the caller's token.

### P4. Gaps in the audit trail (Medium, confirmed)

**Evidence.** Experiment E16. A request with an invalid token gets 401 and writes no audit record. A call refused for insufficient scope is audited as `outcome: error, error_code: internal_error`, the same as a crash, and the client is told "Unknown tool". `test_insufficient_scope_is_refused` does not look at the audit sink.

**Recommendation.** Give authorization refusals their own error code. Decide whether failed authentication is logged here or at the gateway, and write the answer in the deployment guide. Also note that each record lists every resource read; with unfiltered searches (D1) one record can hold tens of thousands of references.

### P5. Transport and file-mode hardening (Low, confirmed)

- A plain `http://` FHIR base URL to a non-local host is accepted when no SMART credentials are set (`fhir/http_adapter.py:83`), and so is an `http://` `ADHD_MCP_PUBLIC_URL` (`config.py:126`). Experiment E13.
- `JsonlAuditSink` opens the file with the process default mode (`audit/records.py:60`). The file links patient ids to outcomes, including `address_safety_gate_first`, so it is sensitive. Create it `0600`.
- Actions in `.github/workflows/ci.yml` are pinned by tag (`actions/checkout@v4`, `astral-sh/setup-uv@v6`, `gitleaks/gitleaks-action@v2`), not by commit. Base images in the `Dockerfile` are pinned by tag, not digest. No job audits dependencies for known vulnerabilities.

## Data access and robustness

### D1. Searches are unfiltered and read the whole history (High for real use, confirmed)

**Evidence.** `_search_params` (`fhir/http_adapter.py:254`) sends `patient` and `_count` only. No caller passes `since`. Experiment E9: `get_psychosocial_context` issues `Observation?patient=z&_count=100`, with no `category` and no `code`. The adapter then follows up to 1,000 pages.

**Why it matters.**
- *Minimum necessary.* To find coded social-history values and (later) a few screening scores, the server reads every laboratory result and vital sign the patient has. That is hard to defend in a privacy review.
- *Latency.* A long-term patient can have tens of thousands of Observations. The 2-second target was measured only on the 14 personas, each a handful of resources ([docs/evaluation/performance.md](docs/evaluation/performance.md)). On Lighthouse, referenced Medications are then fetched one at a time.
- *Audit size.* Every resource read is listed in the audit record.

**Recommendation.** Search Observations by category (`survey`, `social-history`) and, where the server allows, by code. Apply `since` wherever the longest window permits; keep the full read only where "any time" is required (the ADHD exclusion, the open-ended conditions if C1 keeps them). Add a benchmark with a large synthetic record. Record a count and a hash in the audit record when the list is long.

### D2. A 404 from a search crashes the tool (Medium, confirmed)

**Evidence.** `_get` raises `ResourceNotFoundError` for any 404 or 410 (`fhir/http_adapter.py:166`), including searches. `read_category` catches `FhirRequestError` and `SearchNotSupportedError` only (`evidence/common.py:86`). Experiment E5: a server that answers 404 to `GET /Flag?patient=...` makes `check_safety_gate` and `assess_referral_need` fail with a masked error, audited as `internal_error`. The same server answering 400 is handled properly: the gate is `data_unavailable`.

**Why it matters.** Several servers answer 404 for a resource type they do not support. The `generic` profile assumes every type is offered and never reads the CapabilityStatement. The failure is safe, but the tool is unusable on such a server and the error does not say why.

**Recommendation.** In `search`, turn a 404 into a failed read (or `not_supported`). Read `/metadata` once at start-up for the `generic` profile and derive the offered types. Add the case to the fault-injection suite; it has sixteen fault types and not this one.

### D3. One malformed timestamp blocks a patient (Medium, confirmed)

**Evidence.** `parse_fhir_date` requires a time-zone offset whenever a time is present (`fhir/dates.py:16`). Experiment E10: a Condition with `recordedDate` `2026-05-01T10:00:00` is skipped as malformed, the category becomes `incomplete`, the gate becomes `data_unavailable` and the assessment is `insufficient_data`. The skipped record here is a suicidal ideation code, so failing closed is right in principle.

**Why it matters.** Only the calendar date is ever used; the docstring says times and zones are ignored. So the strictness buys nothing, and timestamps without offsets are a common defect in real feeds. One such record anywhere in a patient's history makes the tool permanently unable to assess that patient. Nobody has measured how often this happens.

**Recommendation.** Accept a `dateTime` without an offset and take its date. Keep skipping values that are truly unparseable. Report skip rates by reason in the evaluation so the cost of strictness is visible.

### D4. Smaller robustness points (Low, confirmed)

- A bad `ADHD_MCP_FHIR_BASE_URL` raises `ValueError` from the adapter, which `main` does not catch: the operator gets a traceback, not the "configuration error" message (E11). The same happens for a bad `ADHD_MCP_SITE_CODES`, which is also joined into a package path without checking (E12).
- `SmartBackendAuth._request_token` calls `response.json()` and `body.get` without guarding against a non-JSON or non-object body (`fhir/smart.py:103`). The error would escape as an internal error instead of a failed read.
- A `next` link whose host differs from the configured base (a reverse proxy that does not rewrite links) fails every multi-page search. Failing is right; the deployment guide should say so.
- `main` calls `load_settings` twice (once directly, once inside `context_from_environment`).

## Tests, evaluation and CI

The suite is large, fast enough, and clean: no skipped or expected-failure tests, no real clock or network in unit tests, warnings treated as errors, strict markers, strict mypy on tests as well as source, and a 90% coverage floor that the suite clears at 98.65%. The findings below are about what the tests can and cannot tell you, not about their quality as written.

### T1. The tests check the author's intent, so they cannot find an error of intent (High, confirmed)

Every defect in the clinical-logic section passes the suite, and several are pinned by it as correct behavior:

- `test_an_active_condition_recorded_long_ago_is_current` (`tests/unit/rules/test_signals.py:68`) pins C1.
- The labelled cohort (`tests/evals/cohort.py`) states each archetype's expected outcome "under ADHD ruleset 1.0.0 ... what the code must do". The labels are typed by hand, not computed, so the check is not circular; but agreement of 184 of 184 is a regression check, and the effective number is 23: each archetype is copied across two sexes and four age bands that the ruleset ignores. The file says so honestly, but status.md, the README and risk register entries C5 and C7 quote the numbers as if they measured something about the rules (X3).
- The cohort's age bands start at 24. No test anywhere builds a patient under 18 (C3), a SNOMED-only condition (S1), a single visit carrying two high-weight signals (C2), a follow-up injury visit (C2), an unfilled-orders-only agent count (C5) or a current ADHD medication without a code (C4).

**Recommendation.** Have someone other than the author write adversarial personas from clinical experience, with the outcome they expect, before looking at what the code returns. Appendix A is a starting list.

### T2. Property tests generate only inputs the code already understands (Medium, confirmed)

`tests/property/test_safety_gate_invariant.py` draws condition codes with `st.sampled_from(SELF_HARM_CODES + OTHER_CODES)`, and `test_assessment_invariants.py` from `SIGNAL_CODES + SELF_HARM + EXCLUDING`: dotted ICD-10-CM codes taken from the value sets. The invariant "a self-harm signal is never lost" is thus checked only over representations the matcher is known to accept. A generator that also varied the code system, the dot, letter case, the verification status and the date format would have found S1 and D3 on the first run.

**Recommendation.** Generate at the FHIR-resource level, not the value-set level: the same clinical fact in several legal encodings, with the invariant "the gate is positive, or it says it could not read something".

### T3. Missing cases in otherwise good suites (Medium, confirmed)

- Fault injection (`tests/tools/test_fault_injection.py`) covers sixteen fault types but not a 404 on a search (D2).
- `test_insufficient_scope_is_refused` and `test_bad_tokens_are_rejected_with_401` (`tests/tools/test_http_auth.py`) do not assert what the audit trail holds (P4).
- No test runs a `withhold` policy through `assess_referral_need` and checks the recommendation and the per-signal reasons (P1).
- No test covers start-up with an invalid base URL or site-code name (D4).

### T4. What has never been exercised (Medium; acknowledged in part)

- **A real model.** The model-in-the-loop harness has run only against two scripted stand-ins written by the same author. The hard rule that matters most to a clinician, that nothing is phrased as a diagnosis, is tested on the server's fixed strings; the text a clinician reads comes from the client's model.
- **A real server.** Integration tests need Docker and run only in CI against HAPI with the personas. They were not run in this review (287 deselected). No Lighthouse, Oracle Health or Epic sandbox has been read.
- **A realistic record.** The benchmark and the latency test use the 14 personas (D1).
- **The wording guard on realistic prose.** It is a deny-list of regular expressions over a fixed list of condition names. It is tested against examples its author wrote.

### T5. CI and packaging hardening (Low, confirmed)

- Third-party actions are pinned by tag, not commit; base images by tag, not digest. `hatchling` is the one unpinned build dependency.
- No dependency vulnerability audit or image scan runs, and jobs have no time limit. Dependencies are pinned exactly, which is good for reproducibility and means updates arrive only when someone looks.
- The plan requires "100% of branches in the rules and safety gate modules" (`project_plan.md:59`). Only the 90% total is enforced. Those modules are at 100% today; nothing keeps them there. Add a per-module gate, and include `orchestration/` and `privacy/`.
- Coverage measures `adhd_mcp` only. `scripts/verify_icd10cm_value_sets.py`, whose `check` function stands behind every `verified = true` ICD-10-CM entry, has no test of that function and does not run in CI.
- The container smoke test overrides the entry point with `python`, so the real `adhd-mcp` command and HTTP mode are never started in CI.
- CI and `./scripts/check` run the same steps, as the script claims.

### T6. Scope enforcement is tested for one tool of ten (Medium, confirmed)

The only insufficient-scope test calls `assess_referral_need` (`tests/tools/test_http_auth.py:150`). A mutation probe on a scratch copy replaced `auth=scope_check(...)` with `auth=None` in `draft_referral.py`, `problem_list.py` and `safety_gate.py`; the tool, contract and configuration tests stayed green. A dropped scope check on an evidence tool, or on the tool that drafts a referral, would ship unnoticed.

**Recommendation.** One parametrized test over every tool with three tokens (no scope, evidence only, assess only), asserting the whole allow and deny table, and the audit record for each denial (P4).

### T7. The synthetic-data guard is easy to pass with real-looking data (Medium, confirmed)

`scripts/check_synthetic_data.py` is the only automated control behind the "synthetic data only" hard rule. It inspects Patient resources at the top level or directly inside a Bundle, in `.json` and `.ndjson` files only; it ignores files it cannot decode or parse; and its SSN pattern needs the dashes. Thirteen probe files came back clean, among them a JSON array of Patients, a `.jsonl` file, a contained Patient, a Parameters wrapper, FHIR XML, a Practitioner with a realistic name and record number, and an undashed nine-digit number. It also runs in CI, which is after the push.

**Recommendation.** Detect JSON by content, walk every object, fail closed on a `.json` file that does not parse, check every resource type that carries a name or identifier, and offer a pre-commit hook.

### T8. Untested lines that matter (Medium, confirmed)

The same mutation probe (30 hand-made mutants, 20 caught) found these survivors:

- `privacy/policy.py:88`: removing reason codes from classification is not noticed. No test has an Encounter or medication whose *reason* is in a protected category.
- `privacy/policy.py:226` and `:228` (redaction of a screening answer and of a medication ingredient) are never executed.
- `evidence/safety_gate.py:346`: a flag ending exactly on the as-of date has no boundary test.
- `audit/middleware.py:150`: the resources read during a failed call are not asserted.
- `orchestration/assess.py:167`: "unreadable, not absent" is not asserted for psychosocial signals.

Every window-edge mutant in the engine, the signal evaluation and the gate's discharge windows was caught, which is to the suite's credit.

### T9. The record does not show tests written first (Low, confirmed)

`tests/golden/test_assessment_golden.py` says the expectations were "written by hand ... before the engine existed". Commit `3062650` added the engine and the golden snapshots together and changed six personas' expected recommendation from `"pending"` in the same commit. The cohort, its harness and the report also arrived in one commit. The tests may well have been written first within the session; the history cannot show it, so the red step of the project's test-driven rule cannot be audited.

**Recommendation.** Commit a failing test separately from the code that passes it, at least for clinical rules.

### T10. Two ways the suite can mislead its own maintainers (Low, confirmed)

- **Environment leak.** `tests/conftest.py:25` calls `create_server()` with no context, which reads `os.environ`. With `ADHD_MCP_TRANSPORT=http` set in the shell, all five contract tests error. With `ADHD_MCP_EXPERIMENTAL_CONDITIONS=autism`, running `UPDATE_SNAPSHOTS=1` would write the wrong contract into the snapshots. Clear `ADHD_MCP_*` in an autouse fixture.
- **Report staleness.** The "report is stale" test fingerprints the data files and the cohort (`tests/evals/report.py:59`), not the engine. A logic change that alters the sensitivity figures leaves the committed evaluation report looking current.

## Documentation

From a dedicated pass comparing documents with each other, with the data files and with the research. I re-read the cited lines for every item below unless it is marked "not re-checked". No wording that states or implies a diagnosis was found in any document, prompt, resource or tool description. Environment-variable names, file paths and the test names cited in the threat model all check out.

### X1. The evidence trail is weaker than the rule card's "Inference?" column says (Medium, confirmed in part)

The rule card marks ten counted signals "No" under "Inference?". For several, the cited source does not support use as a sign that precedes an ADHD diagnosis:

- **Intermittent explosive disorder.** "Nock 2014" is an odds ratio for suicide attempts in soldiers (research report line 35), not an association with ADHD.
- **Legal problems.** "Medication about 13% less criminality" is a treatment effect in people already diagnosed, and the research itself says "percentages from press coverage; exact IRRs need checking" (line 37).
- **Other substance use.** "ASRS validated in SUD" is a statement about a screener's accuracy.
- **Repeated accidental injury.** Dalsgaard 2015 is a mortality study.
- **Stimulant and alcohol (the two strongest signals).** The catalog cites one prediction model. Its code F15.8 does not exist in ICD-10-CM (verification backlog line 59), and the value sets were then widened to all of F15 (including caffeine) and all of F10. (The description of that model's control group was not re-checked.)

status.md says of the weights "all marked inference in the rule card". The rule card does not do that.

**Recommendation.** Mark every weight and every source that is indirect as inference, and say in the rule card which signals have direct evidence of preceding an ADHD diagnosis. On my reading that is at most two.

### X2. "A released ruleset cannot change silently" is overstated (Medium, confirmed)

`parse_ruleset` hashes `ruleset.toml` only (`rules/ruleset.py:75`). The signal catalog (weights, counts, windows), every value set, the drug classes, `existing_care.toml` and `safety_gate.toml` are not pinned, and any of them changes recommendations. The claim appears in the ruleset header, ADR 0010 and threat T14. ADR 0013 says a reader can "tell from any output whether two results were produced by the same rules"; that is not yet true.

**Recommendation.** Pin a fingerprint of all clinical content a ruleset depends on, and report it in the output's `versions`.

### X3. Statements stronger than the evidence (Medium, confirmed)

- [Threat model](docs/security/threat_model.md), last section: model-side risks "are covered by the wording guard and the Phase 7 model-in-the-loop evaluation". No real model has been run.
- README line 7: "Every planned 1.0 feature is built and evaluated on synthetic data." Plan item 5 of Phase 7 and the Lighthouse live run are open.
- Risk register C5 and C7 cite "0 of 32 look-alikes flagged" as mitigation. The cohort's labels follow the rule (see T findings), so this shows consistency, not specificity.
- README line 11: "under-diagnosed, especially in veterans". The limitations page says no estimate is veteran-specific.
- status.md line 11: "all match their intended outcomes", with no caveat.

### X4. architecture.md describes an earlier design (Medium, confirmed)

- Lines 213 to 215 list PHQ-9 item 9 and C-SSRS as gate signals (not performed today), and "non-prescribed stimulant evidence" and "TBI with attention complaints" as high-weight signals (neither is in the catalog; TBI is a note).
- The tool table says `draft_referral_proposal` reads "none"; it runs the whole assessment. The `check_existing_care` row omits MedicationRequest and MedicationStatement.
- Line 249, the configuration guide and status.md describe `cite` as "existence and date only". `privacy.toml` adds "the signal or family it belongs to", which is the disclosure in P2.

### X5. Exclusion documents and data disagree (Low, confirmed)

- `existing_care.toml:12` counts any ServiceRequest whose reason is an attention-symptom code (R41.840, R41.844) as an ADHD referral. The rule card's exclusion row and the tool reference do not say so.
- Any F90 code of any age or status gives `already_in_care` with the text "An ADHD code ... is already recorded". A childhood code long resolved is the adult group the research is most concerned with.
- [docs/reference/tools.md](docs/reference/tools.md) line 138 calls stimulants and non-stimulants "drug classes the referral rules use". The rules do not use them (C4).

### X6. Stale numbers and statuses (Low, confirmed)

- Tool contract "0.3.0" in the ADHD rule card line 10 and the threat model line 3; the code says 0.4.0. (status.md said the same and is corrected with this review.)
- Safety gate rule card: "10 personas"; there are 14. Project plan: "nine tools"; there are ten.
- ADR 0010 gives ruleset statuses as "`draft` or `released`"; `experimental` exists.
- ADRs 0013 and 0014 are still "Proposed". 0014 says the owner "accepts this record with the Phase 8 pull request", which is merged.
- "Open question 19" names two different questions.
- The risk register says "Last reviewed ... Phase 7" and contains Phase 8 entries. The threat model says to review again before release; it has not been.
- Phases 4 and 5 are "Done", but their exit criteria require an owner-reviewed catalog and an approved rule card (`reviewed_by_owner = false`).

### X7. Gaps in the rule cards (Medium; clinical questions)

- **Equity.** Bias is analysed for sex only. Legal problems, homelessness, and education or employment problems are modifiers, and they are proxies for socioeconomic status and, in practice, race. No document discusses it.
- **Falls in older adults.** `injury.accidental_external_cause` includes falls (W00 to W19). With no age logic, two fall visits plus depression and insomnia codes in an 80-year-old give the suggestion.
- **History of self-harm.** Z91.51 and Z91.52 count for 365 days from the recorded date, while the same rule card calls prior self-harm the strongest predictor. A "history of" code is by nature about the past.
- **"Until the signals have been addressed."** The approved text for a positive gate uses these words, but nothing detects that anything has been addressed; the gate clears with time.
- **Differential notes.** Only TBI gets one. The research says the ASRS "may not separate ADHD symptoms from PTSD symptoms"; PTSD is a modifier with no note.
- **Annual code updates.** Value sets are verified against FY2027. No document requires re-verification each October.
- **A signal that cannot be evaluated reads as absent.** Injury visits need the emergency class or a site mapping. Lighthouse documents neither, so `repeated_accidental_injury` would read "Not found in the record" there, not "not performed". (Read; not run.)

## Governance and process

### G1. No independent review (High, confirmed)

**Evidence.** The history holds 72 commits on two days, 64 by the agent. Seven pull requests were merged in about 30 hours. The GitHub API returns no reviews for the two I sampled in full (PR #5 and PR #7). Time open before merge: PR #4 (the safety gate) 5 minutes 36 seconds; PR #7, 16 minutes; PR #2, 24 seconds. PR #5 carried three plan phases, against the project's own rule of one work item per pull request. The threat model, the clinical safety reviews and this review are by the same kind of author as the code.

**Why it matters.** The findings above passed every one of those checks. Several are pinned by tests as intended behavior. This is what a single point of view produces, however careful: internally consistent work whose assumptions nobody questioned. Risk J2 ("no clinician is available") is rated medium likelihood; on the evidence it has already happened.

**Recommendation.**
1. Protect `main`: require a review from a person other than the author before merge.
2. Name a clinical reviewer. Until there is one, do not tag 1.0.0 and do not set any ruleset to `released`.
3. Have someone with security experience review the threat model and ADR 0012.
4. Keep pull requests to one work item, as CLAUDE.md already says.

### G2. "Verified" means checked by the author (High, confirmed)

**Evidence.** All 401 `checked_by` fields in the data files name the Claude Code agent. The strict loader accepts an entry when `verified = true` and three provenance fields are filled in. The human spot-check of the `safety.*` value sets is "waived until release". Verification means "this code exists in the FY2027 tabular with this meaning"; it does not mean "this is the right set of codes for the concept", which is where C7 and the driver omission sit.

**Recommendation.** Split the flag in two: `exists_in_source` (a script can establish it) and `reviewed_by` (a named person). Let the strict loader require the second for the `safety.*` sets before a ruleset can be `released`. Do the waived spot-check now; it is 20 entries.

### G3. The version label overstates readiness (Medium, read)

`1.0.0rc1`, a Dockerfile, a deployment guide and a release checklist tell a reader the software is nearly ready. The clinical content is unreviewed, no real model has used the tools, no real server has been read, and the central hard rule (never diagnose) is enforced on the server's fixed strings while the words a clinician reads are written by the client's model. I suggest `0.x` until three things are true: a clinician has signed the rule cards, the model-in-the-loop run has passed with a real model, and the server has run against at least one real sandbox.

### G4. status.md is stale (Low, confirmed)

status.md says PR #7 is open and names branch `claude/tender-lamport-y0qpyy`. PR #7 was merged at `9e14e02`. Corrected in the same change as this review.

## Recommended order of work

Each fix should start as a failing test, per the project's rules. The experiments in Appendix A are close to ready-made test cases.

**Before tagging 1.0.0**

1. G1, G2: branch protection, a named clinical reviewer, the `safety.*` spot-check.
2. S1 steps 1 and 2 and S2 step 1: make unrecognized codings loud; normalize dotless ICD-10-CM; make the gate fail safe on a recorded screening result.
3. P1: withheld is not "not found".
4. C3: out-of-population outcome.
5. C1 reason text: stop stating a recency that is not true (the window rule itself needs the clinician).
6. D2, D3: 404 handling; tolerant timestamps.
7. Clinical decisions, with the reviewer: C1 window rule, C2 episode counting, C4 medication, C5 fill status, C7 scope.
8. S2: LOINC verification; a file path for site codes.
9. The model-in-the-loop run with a real model (open question 4).
10. Corrections to documents (X findings) and tests (T findings): start with T6 (scope tests) and T7 (the synthetic-data guard).

**Before any use with real data**

11. D1: filtered searches and a large-record benchmark.
12. P2, P3, P4, P5: explicit privacy policy, patient-level authorization position, audit of refusals, transport and file modes.
13. C6: flag-rate estimate, then a silent-mode period on local data.
14. A run against a real sandbox (open question 5).

## Appendix A: experiments

All experiments used synthetic resources built in memory, the public tools through an in-memory MCP client, `FixedClock` at 2026-06-15, and the `synthetic` site codes unless stated. Nothing was written to the repository. Codes are ICD-10-CM unless stated.

| # | Input | Observed |
|---|---|---|
| E1 | Conditions, no clinical status: Y90.3 (2010-03-01), F32.9 (2009), G47.00 (2008) | `consider_referral_for_formal_screening`; `high_with_modifiers`; each signal "Found within 1095 days." |
| E1b | As E1 with F10.129 and status `active` | Same |
| E2 | One EMER encounter 2026-01-10 with V43.52XA, Y90.4, S06.0X0A | `consider_referral...`; `two_high_classes`; `alcohol_involvement` + `crash_as_driver` |
| E2b | Two EMER encounters, each V43.52XA + an S code | `consider_referral...`; `two_high_classes`; `crash_as_driver` + `repeated_accidental_injury` |
| E3 | F10.20, F32.9; orders for sertraline, fluoxetine, bupropion, none dispensed; one unrelated dispense present | Timeline: three `not_filled`, no exposures, antidepressant count 3. Assessment: `multiple_antidepressants` present; rule fired |
| E4 | F10.20, F32.9, G47.00; methylphenidate order 2026-05-01 with linked dispense; no F90 | `excluded: false`; `consider_referral...`; no medication note |
| E5 | HTTP adapter, generic profile; server returns 404 for `Flag` search | `check_safety_gate` and `assess_referral_need` error; audit `internal_error`. With 400 instead: gate `data_unavailable` |
| E6 | F15.20, F10.20, F32.9, G47.00; policy `substance_use = withhold` | `no_recommendation`; three substance-use signals "Not found in the record."; Condition `withheld` |
| E6b | As E6, default policy | Signal titles shown beside `Condition/<id>` and date |
| E7 | Patient born 2017-01-01; F10.20, F32.9, G47.00 | `consider_referral...`; next step names an adult screen |
| E8 | Conditions coded only in SNOMED CT: 6471006 (2026-05-01), 82313006 (2026-04-01) | All coded gate checks `not_found`; Condition `available`, 2 records, no warnings; `clear_limited_data` |
| E8b | `R45851` (no dot), 2026-05-01 | Same |
| E9 | `get_psychosocial_context` through the HTTP adapter | Requests: `Patient/z`, `Condition?patient=z&_count=100`, `Observation?patient=z&_count=100` |
| E10 | R45.851 with `recordedDate` `2026-05-01T10:00:00` | Condition `incomplete` (1 skipped); gate `data_unavailable`; assessment `insufficient_data` |
| E11 | Start with `ADHD_MCP_FHIR_BASE_URL=ftp://x` | Uncaught `ValueError` traceback |
| E12 | Start with `ADHD_MCP_SITE_CODES=../privacy` | Loads `data/privacy.toml`; uncaught validation traceback |
| E13 | `ADHD_MCP_FHIR_BASE_URL=http://ehr.internal.example/fhir`; `ADHD_MCP_PUBLIC_URL=http://...` | Both accepted |
| E14 | EMER 2026-01-10 S52.501A + W01.0XXA; EMER 2026-01-20 S52.501D; F32.9, G47.00 | `repeated_accidental_injury` "2 found within 730 days"; `consider_referral...` |
| E15 | EMER with V53.5XXA (pickup or van driver, traffic) | No crash signal |
| E16 | HTTP with auth: (a) token lacking the assess scope calls `assess_referral_need`; (b) invalid token | (a) audited as `error / internal_error`, client told "Unknown tool"; (b) 401, no audit record |
| E17 | Observation LOINC 44260-8, value 3, 2026-06-01; F10.20, F32.9, G47.00 | `get_screening_history` lists PHQ-9 item 9 = 3. Assessment: `consider_referral...`; gate `clear_limited_data`; item 9 check "not performed" |

## Appendix B: checked and found sound

So that later reviews need not repeat them:

- The poisoning regular expressions in `safety.intentional_self_poisoning` and `safety.undetermined_intent_poisoning` match the intent character in both five- and six-character code shapes, and I found no code in T36 to T65 they would match wrongly. (Read, not exhaustively tested.)
- `R45.851` is matched exactly, so homicidal ideation (R45.850) is not caught by the suicidal-ideation check; `T14.91` does not match `T14.90`.
- Prefix matching stops at the dot boundary (`F15` does not match `F150`).
- A check that finds a signal reports `found` even when another category it needs failed, so a partial read cannot hide a positive.
- The request cache is per call, copies results, and does not cache failures.
- SMART assertions carry `jti`, a five-minute expiry and the configured audience; tokens are refreshed before expiry and once after a 401; Lighthouse tokens are held per patient in a bounded cache.
- Released rulesets are hash-pinned and a draft cannot be mistaken for one.
- `draft_referral_proposal` builds no id, sends nothing, and refuses experimental rulesets.
