# Limitations

What ADHD_MCP 0.9.0 cannot do, and why. Every item here is also in the relevant rule card, ADR or risk register entry.

## Clinical

- **Not clinically validated.** The ruleset is a starting heuristic from published research ([rule card](clinical/rule_card_adhd_1.0.md)). It has been tested only on synthetic data designed to match the rules. Nothing is known about its real-world sensitivity, specificity or effect on care.
- **Never a diagnosis.** A suggestion means "consider referral for formal screening". A clinician decides; formal screening and evaluation follow.
- **Internalizing presentations are under-flagged.** Every high-weight signal is externalizing (substance-related disorders, crashes, injuries), and no rule fires on modifiers alone. On the cohort, 8 of 40 internalizing suggestive presentations are flagged against 32 of 32 externalizing ones; women are more often first seen as depressed or anxious, so women are likely under-flagged ([sex-balance review](evaluation/sex_balance_review.md)).
- **No screening scores are used.** LOINC codes and screening cutoffs are not yet verified, so PHQ-9 item 9 and C-SSRS gate checks are "not performed", no gate can be plain "clear", and no ruleset signal uses AUDIT-C, PC-PTSD-5, PHQ or ASRS scores ([verification backlog](clinical/verification_backlog.md)). A PHQ-9 item 9 or C-SSRS result recorded in the past year cannot be interpreted, so it stops the safety gate: such a patient gets `insufficient_data` until LOINC is verified.
- **Not a suicide risk assessment.** The safety gate surfaces self-harm signals that are already coded; it does not estimate risk.
- **Evidence base.** The anchor estimates are civilian or service-member, many from secondary sources; none is veteran-specific. Apart from the adult-only check (under 18, no birth date or deceased gives `outside_intended_population`), no age logic is applied: the signals and weights are the same at 19 and at 80.
- **Drafts awaiting review.** The signal catalog, rule card, clinician wording and drug-class curation are drafts until the project owner and a clinical reviewer approve them.

## Data

- **Coded data only.** Free-text notes are not read. Psychosocial problems, family history and TBI are under-coded, and a missing code is weak evidence of absence.
- **Code systems.** Value sets are ICD-10-CM only. A Condition coded only in SNOMED CT (or with text only) cannot be matched, so it makes the Condition category incomplete and the assessment `insufficient_data` rather than being silently ignored. The same is not yet true of an Encounter reason code: a self-harm reason coded only in SNOMED CT on an Encounter is not recognized by the safety gate.
- **Withholding by security label.** Under a `withhold` policy, a record removed because of a security label in a category no output names (HIV, sickle-cell disease) can hide a signal that does not belong to that category (for example a depression code carrying an HIV label), and nothing says so, by design (ADR 0011): naming the category would reveal that such a record exists. A substance-use label on a non-substance record makes the result `insufficient_data`, but that signal's own reason still reads "Not found". ICD-10-CM codes sent without the dot are repaired ([ADR 0007](adr/0007-fhir-modeling.md)). Retired RxNorm product codes are not matched ([ADR 0009](adr/0009-rxnorm-drug-classes.md)).
- **Not read.** Missed appointments (no Appointment search); coded social-history observation values are reported but not counted by the rules.
- **VA Lighthouse.** Built from public documentation and never run against the sandbox with credentials. Lighthouse offers no screening instruments (its Observations are labs, vital signs and social history), no flags, referrals, care plans, dispenses or statements, and only inpatient and outpatient encounters, so many checks are "not performed" there ([Lighthouse](integration/lighthouse.md)).
- **Local codes.** Psychiatric stays, high-risk flags and ADHD referrals or evaluations rely on a site code mapping; only the synthetic site exists, so on a real server those checks report "not performed".
- **One condition.** ADHD only; the plugin interface allows more later.

## Operational

- **What is read.** The safety gate searches Observations by the codes the instrument files list, as the Observation's code or any component's code (`combo-code`, sent without a system so an aliased code system is not missed); a server without `combo-code` (VA Lighthouse) is read unfiltered for the gate. The screening history adds survey, social-history and SDOH Observations; psychosocial context reads those categories and the site's military separation codes. On a server with `combo-code`, laboratory results and vital signs are never read. An Observation with none of those categories and none of those codes (for example an uncategorized SDOH answer) is not seen by the evidence tools. Other resource types are read whole: the safety gate counts undated items, so a date filter would hide them. A server that ignores the filters is filtered again locally.
- **Synthetic data only so far.** The server has never read real patient data. Hosting it for real use needs a site's privacy, security and governance review.
- **Audit file.** The development audit file has no tamper evidence (risk P5, accepted); rate limiting is left to the hosting gateway (risk S6, accepted). See the [threat model](security/threat_model.md).
- **Model use not yet evaluated live.** How real language models use the tools has been tested only with scripted stand-ins ([model-in-the-loop](evaluation/model_in_the_loop.md)).
- **Latency measured in process.** The 2 s target is checked against a local HAPI server by the CI integration job (it passed on the Phase 7 pull request), never against a production EHR ([performance](evaluation/performance.md)).
