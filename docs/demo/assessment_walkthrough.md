# Walkthrough: three assessments with an MCP client

A demonstration script (Phase 5 exit criterion). It uses the synthetic persona catalog and the MCP Inspector or any MCP client. All data is synthetic. Results are suggestions for a clinician, never a diagnosis.

## Start the server

```bash
ADHD_MCP_FIXTURE_DIR=tests/personas/bundles uv run adhd-mcp
```

The persona catalog is dated 2026-06-15, so pass `"as_of": "2026-06-15"` in each call below.

## 1. A referral suggestion: p01

Call `assess_referral_need` with `{"patient_id": "p01-patient", "as_of": "2026-06-15"}`.

- `safety_gate.status` is `clear_limited_data`: no self-harm signal was found, but the PHQ-9 item 9 and C-SSRS checks are not performed while their LOINC codes are unverified. Point this out: limited data is not reassurance.
- `recommendation` is `consider_referral_for_formal_screening`, with the approved text and the suggested next step (an adult ADHD screen, then clinician evaluation if positive).
- `basis` lists four high-weight signals (alcohol involvement, crash as driver, repeated accidental injury, stimulant-related disorder) and two modifiers (insomnia, education or employment problems), each with its Condition or Encounter ids and date.
- `decision_trace` shows both rules fired and which signals each counted.
- `notes` says the rule is a starting heuristic, not clinically validated.

Then call `draft_referral_proposal` with the same arguments: it returns a ServiceRequest with `status: draft`, `intent: proposal`, the basis as `reasonReference` and `supportingInfo`, and `stored: false`.

## 2. Safety first: p03

Call `assess_referral_need` for `p03-patient`.

- `safety_gate.status` is `positive`, with evidence (suicidal ideation code, psychiatric discharge 66 days earlier, high-risk flag) and the fixed guidance on suicide risk evaluation and lethal-means counseling.
- `recommendation` is `address_safety_gate_first`. The stimulant dependence code is still listed in `basis`, but no screening referral is suggested until the safety signals are addressed.
- `draft_referral_proposal` returns no draft and says why.

## 3. A narrow miss: p13

Call `assess_referral_need` for `p13-patient`.

- `recommendation` is `no_recommendation`.
- `signals_checked` shows alcohol involvement (high) and legal problems (modifier) present. `crash_as_driver` is absent: the crash is recorded on 2023-06-15, one day outside the 1095-day window, so its reason reads "0 found within 1095 days; 1 required."
- `decision_trace` shows neither rule fired: one high-weight signal with one modifier, and one high-weight class.

Ask the client's assistant to use the `summarize_checks` prompt for `p13-patient` to get a plain-language summary of what was checked and what was missing.

## Reference material

Read the resources `adhd-mcp://rulesets/adhd`, `adhd-mcp://signal-catalogs/adhd` and `adhd-mcp://intended-use` to see the exact rules, signals and intended use the results came from.
