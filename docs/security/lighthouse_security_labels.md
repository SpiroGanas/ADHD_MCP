# Sensitive-data policy against VA Lighthouse labelling

Phase 8, item 4: a desk review of the Phase 6 sensitive-data policy ([ADR 0011](../adr/0011-audit-tracing-and-privacy.md), `src/adhd_mcp/data/privacy.toml`) against what VA Lighthouse exposes. 2026-11-27, by the Claude Code agent, from the public sandbox CapabilityStatement and OpenAPI description ([Lighthouse](../integration/lighthouse.md)). No sandbox data was read (no credentials).

## What Lighthouse documents

- No security labels. `meta.security` appears only in the generic FHIR `Meta` schema; no example resource carries a label, and the descriptions never mention confidentiality codes, 38 U.S.C. 7332, 42 CFR Part 2 or withheld data.
- No statement on whether 7332-protected records (substance use, HIV, sickle-cell disease) are included, withheld or redacted in the Patient Health API, in the sandbox or in production.
- The API is described as "suitable for patient-facing use cases" and "VA benefits adjudication"; client credentials access needs VA employment or a VA agreement.

## What the policy does with that

The policy classifies a resource by its security labels **or** by a code in the category's verified value sets. With no labels, classification falls back to codes alone, which the policy already does; no configuration change is needed. The end-to-end Lighthouse test confirms that substance-use Conditions on Lighthouse-shaped data (absolute references, no labels) are cited as `substance_use` (`tests/adapters/test_lighthouse_adapter.py::test_an_assessment_runs_end_to_end_against_lighthouse_shaped_data`).

## Gaps (recorded in the risk register, P3)

| Gap | Why it matters | Mitigation |
|---|---|---|
| Code-only classification | A protected record whose code is outside the value sets is not recognised: for example a substance-use medication (buprenorphine), a drug screen or HIV laboratory result, or a local code. The ADHD rules read none of these, but `get_medication_timeline` reports unclassified records as a count | The policy is a site setting: a VA deployment must add value sets (medications, LOINC lab codes) after its privacy review |
| Unknown upstream filtering | If Lighthouse already withholds 7332 data, the record is silently thinner; if it does not, the server receives protected data under the deploying site's agreement | Ask VA during registration; record the answer in [Lighthouse](../integration/lighthouse.md) |
| No consent signal | Nothing in the API says whether a patient has authorised disclosure of 7332 data | Outside the server; the deploying site's legal review decides each category's action (`allow`, `cite` or `withhold`) |

## To finish

With sandbox access, read the sandbox test patients' resources for `meta.security` and for substance-use, HIV and sickle-cell codes, and record what appears here. A real deployment needs the site's privacy officer to choose the action per category.
