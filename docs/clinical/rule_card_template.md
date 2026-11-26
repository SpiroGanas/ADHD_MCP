# Rule Card Template

A rule card is the plain-language record of one released ruleset: what it does, what it rests on, and where it should not be trusted. Copy this file for each ruleset version (for example `rule_card_adhd_1.0.md`). If a statistical model is ever added through the scorer slot, it gets a model card with the same sections plus training data and performance.

---

# Rule Card: [condition] ruleset [version]

| | |
|---|---|
| Ruleset identifier and version | |
| Effective date | |
| Status | Draft / Released / Superseded by |
| Author | |
| Clinical reviewer and date | |
| Server versions that can load it | |

## Intended use

One paragraph. Refer to the [intended use statement](intended_use.md). State that the ruleset recommends referral for screening and does not diagnose.

## Population

Who the ruleset is meant for (age range, setting) and who is excluded.

## Safety gate

| Signal | Definition (value set, window) | Source | Verified |
|---|---|---|---|
| | | | |

## Exclusions

| Exclusion | Definition | Rationale |
|---|---|---|
| | | |

## Signals

| Signal | Weight class | Definition (value set, window) | Supplied by tool | Evidence source | Verified |
|---|---|---|---|---|---|
| | | | | | |

## Decision logic

The combination rule in plain language, with every threshold and window stated.

## Outputs

The possible recommendations and the suggested next step for each.

## Evidence base

The studies the rules rest on, the population each studied (veteran, service member, civilian), and how strong each is. State plainly which parts are inference.

## Evaluation

| Item | Result |
|---|---|
| Cohort used (always synthetic unless stated) | |
| Agreement with intended outcomes | |
| Recommendation rate by sex | |
| Recommendation rate by age band | |
| Threshold sensitivity | |

Required statement: *Results on a designed synthetic cohort show that the software applies the rules as intended. They are not evidence of clinical accuracy.*

## Known limitations and biases

For example: signals that skew by sex; conditions that mimic the target; dependence on coding quality; data categories that may be withheld.

## Change log

| Version | Date | Change | Reason |
|---|---|---|---|
| | | | |
