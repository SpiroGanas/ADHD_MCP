# Rule Card: autism ruleset 0.0.1 (experimental stub)

**Not for clinical use.** This ruleset exists only to prove that a second condition can be added as a plugin without changing the engine, the evidence tools or the ADHD ruleset (Phase 8, item 5; [ADR 0005](../adr/0005-adhd-first-condition-plugins.md)). Its signals are placeholders. It has not been reviewed, calibrated or validated, and it is never released.

| | |
|---|---|
| Ruleset identifier and version | `autism` 0.0.1, catalog `autism.signal_catalog` 0.0.1 |
| Effective date | 2026-11-27 |
| Status | Experimental (cannot be released) |
| Author | Claude Code agent, delegated by the project owner, 2026-11-27 |
| Clinical reviewer and date | None |
| Server versions that can load it | 0.9.0 and later development versions (tool contract 0.5.0) |
| Enabled by | `ADHD_MCP_EXPERIMENTAL_CONDITIONS=autism`; off by default |

## Intended use

None. The stub shows that `assess_referral_need` with `condition: "autism"` runs the same safety gate, exclusion step, evidence assembly, rules engine, output and audit path as ADHD. Every text it returns starts "Experimental stub, not for clinical use". Like every output of this server, it never states or implies a diagnosis.

## Safety gate

The shared safety gate, unchanged ([rule card](rule_card_safety_gate.md)). A positive gate takes precedence exactly as for ADHD.

## Exclusions

| Exclusion | Definition | Verified |
|---|---|---|
| `existing_autism_code` | An autism code recorded on a Condition on or before the as-of date (`care.autism_diagnosis`: F84.0, F84.5, F84.8, F84.9). F84.2 (Rett's syndrome) and F84.3 (other childhood disintegrative disorder) are not included (owner decision 2026-11-27). A failed Condition read leaves the exclusion unknown; a server that does not offer Condition leaves it not performed | Yes, ICD-10-CM FY2027 ([check](verification/icd10cm_fy2027_check.md)) |

## Signals (placeholders)

All three are modifiers, look back 1095 days, reuse value sets verified for the ADHD work, and are marked inference. They were chosen only because the research report's autism section mentions these labels as possible masks; they are not a reviewed autism signal set.

| Signal | Value sets |
|---|---|
| `ptsd_code` | `mh.ptsd` |
| `depression_or_anxiety_code` | `mh.depression`, `mh.generalized_anxiety` |
| `borderline_personality_code` | `mh.borderline_personality` |

## Rule

| Rule | Fires when |
|---|---|
| `all_placeholder_modifiers` | All three placeholder modifiers are present |

## Known limitations

- No evidence supports this rule. The research report says no adult autism EHR model exists, and that a flag anchored on depression would miss about half of the highest-risk autistic adults (Croen 2015).
- No autism screening instrument (AQ-10, RAADS-14) is coded or verified, so no screening history is used.
- `get_mh_problem_list` does not have an autism family; autism codes appear under the chapter 5 fallback family.

## Before any real autism ruleset

A real ruleset needs its own planning round: a reviewed signal catalog, verified codes and instruments, a labelled cohort, a sex-balance review (masking is reported as more common in women), clinician wording approved by the project owner, and a released status with a pinned hash.
