# Sex-balance review: ADHD ruleset 1.0.0

Phase 7, work item 3. Status: **findings and options for the project owner; no ruleset change has been made** (owner decision 2026-11-27: measure and propose). Numbers come from the generated report [adhd_ruleset_1.0.0.md](adhd_ruleset_1.0.0.md).

> Results on a designed synthetic cohort show how the rules treat designed presentations. They say nothing about real-world accuracy, and nothing here is clinically validated.

## Question

The research report predicts that injury, crash and legal signals under-flag women: women with ADHD are more often first labelled depressed or anxious, and the high-weight signals of ruleset 1.0.0 skew male. The research recommends sex-specific thresholds but gives no values.

## Method

- **Cohort.** 184 synthetic patients from 23 hand-written archetypes ([tests/evals/cohort.py](../../tests/evals/cohort.py)), each built for both sexes and four age bands. Nine archetypes are *suggestive* presentations: four *externalizing* (substance-related disorders, crashes, injuries, legal and work problems) and five *internalizing* (depression, anxiety, insomnia, attention symptoms, borderline personality, antidepressant changes, with or without other modifiers). Look-alikes (TBI, PTSD, bipolar disorder, substance use without ADHD signals) and controls are *not suggestive*.
- **Labels.** Research profile and style are the cohort designer's reading of the research report, not ground truth.
- **Reweighting.** The ruleset never reads sex, and the cohort gives every archetype to both sexes, so measured rates by sex are equal by construction. To show what that means for a population, the report reweights the two styles with an *illustrative* mix: women's suggestive presentations 70% internalizing, men's 30%. The mix is an assumption, not an estimate.
- **Options.** Each option is a variant of ruleset 1.0.0 applied to the whole cohort by the harness ([tests/evals/harness.py](../../tests/evals/harness.py), `OPTIONS`).
- **A caution on the options.** The same designer wrote the archetypes and the options. Whether an option flags a look-alike depends on how many modifiers each archetype was given (here at most three for look-alikes, four for three of the internalizing archetypes), so the cohort cannot show an option's real false-positive rate; it only shows how the option treats these designed records.

## Findings

| Group | Flagged by ruleset 1.0.0 |
|---|---|
| Suggestive, externalizing | 32 of 32 (100%) |
| Suggestive, internalizing | 8 of 40 (20%) |
| Not suggestive (look-alikes and controls) | 0 of 64 |
| Women's suggestive presentations, under the assumed mix (not measured) | 44% |
| Men's suggestive presentations, under the assumed mix (not measured) | 76% |

1. **The gap comes from the rule structure, not from a threshold.** All four high-weight signals are externalizing. Every rule needs at least one high-weight signal, so modifiers alone never fire a rule, however many there are. The only internalizing archetype flagged (I3) has alcohol involvement.
2. **Internalizing presentations carry several modifiers.** The missed internalizing archetypes have three (I2) or four (I1, I4, I5) distinct modifiers.
3. **The antidepressant count does not matter on its own.** Lowering it from three to two agents changes nothing, because it is a modifier, and modifiers alone never fire a rule.
4. **Age.** The ruleset reads no age and the cohort is balanced, so rates by age band are equal (12 of 46 in every band). The cohort cannot show age effects of real coding practice.

## Options

| Option | Suggestive flagged | Internalizing flagged | Look-alikes or controls flagged | Illustrative mix: women / men | Notes |
|---|---|---|---|---|---|
| A. No change; document the limitation | 40 of 72 | 8 of 40 | 0 of 64 | 44% / 76% | The current state. Clinicians are told the rule under-flags internalizing presentations |
| B. Add a sex-blind rule: four or more distinct modifiers | 64 of 72 | 32 of 40 | 0 of 64 | 86% / 94% | Flags I1, I4, I5; not I2 (three modifiers). The PTSD look-alike (three modifiers) and the TBI look-alike (two modifiers; TBI itself is a note and never counts) stay unflagged. Modifiers are non-specific: in real records with many psychiatric codes this rule may flag many more patients than the cohort shows |
| C. Add a sex-blind rule: three or more distinct modifiers | 72 of 72 | 40 of 40 | 8 of 64 | 100% / 100% | Also flags the PTSD look-alike (PTSD, depression, insomnia). Probably too broad |
| D. Two antidepressants instead of three | 40 of 72 | 8 of 40 | 0 of 64 | 44% / 76% | No effect (finding 3) |
| E. One high-weight signal with one modifier | 40 of 72 | 8 of 40 | 0 of 64 | 44% / 76% | Helps only the boundary cases (alcohol with PTSD; the crash just outside the window). Does nothing for internalizing presentations |
| F. Sex-specific thresholds (for example option B for records with sex female only) | Not run | As B for women | As B for women | about 86% / 76% | The research suggests it but gives no values. Needs the engine to read recorded sex, which the ruleset format does not support. Records with sex unknown or other, and the difference between recorded sex and gender, need a decision. Raises equity questions of its own |

## Recommendation (proposal for the owner)

1. Keep ruleset 1.0.0 as it is (option A) and keep the limitation stated in the rule card and in every report.
2. If the owner wants a change, the strongest candidate on this cohort is **option B as a new draft ruleset 1.1.0**: sex-blind, closes most of the internalizing gap, and flags no look-alike here (a result that follows from the modifier counts the designer gave the archetypes; see the caution under Method). Before adopting it, a clinical reviewer should judge whether four non-specific modifiers is a reasonable trigger, and it should be checked against real (de-identified, approved) data when that becomes possible, because the cohort cannot show its real false-positive rate.
3. Do not adopt C, D or E for sex balance. Revisit F only with clinical advice and published thresholds.

Decision needed: open question 16 in [status.md](../../status.md). Adopting any option means a new ruleset version, its own tests and cohort expectations, a re-run of the evaluation, and a new rule card.
