# VA Lighthouse Patient Health API (FHIR R4)

Phase 8, items 1 and 2. How ADHD_MCP connects to VA Lighthouse, and every difference from a generic FHIR R4 server that matters to it.

**Status (2026-11-27):** built and tested from the public documentation only. The project has no Lighthouse sandbox credentials (open question 5), so no request has reached the sandbox with a token and the exit criterion "an assessment runs end to end against Lighthouse sandbox patients" is not met. What is tested: the adapter passes the shared adapter suite against a Lighthouse-shaped fake server, its profile matches the sandbox's recorded CapabilityStatement, and a full assessment runs through it end to end on synthetic personas.

## Sources

| Source | Fetched | Kept |
|---|---|---|
| Sandbox CapabilityStatement, `https://sandbox-api.va.gov/services/fhir/v0/r4/metadata` (software `health-api-fhir-r4`, FHIR 4.0.1) | 2026-11-27 | [tests/adapters/recorded/lighthouse_sandbox_metadata.json](../../tests/adapters/recorded/lighthouse_sandbox_metadata.json); a test checks the profile against it |
| Sandbox OpenAPI description, `https://sandbox-api.va.gov/services/fhir/v0/r4/openapi.json` ("US Core R4 v1") | 2026-11-27 | Not kept (about 290 KB); facts quoted below |
| developer.va.gov, client credentials grant page (the page script) | 2026-11-27 | Facts quoted below |

The per-API CCG details (exact scopes, the assertion audience URL) come from a developer.va.gov metadata service that could not be read from the development environment. They are settings, marked unverified below.

## Configuration

```bash
ADHD_MCP_FHIR_BASE_URL=https://sandbox-api.va.gov/services/fhir/v0/r4 \
ADHD_MCP_FHIR_SERVER_PROFILE=lighthouse \
ADHD_MCP_SMART_TOKEN_URL=<token URL from the registration> \
ADHD_MCP_SMART_AUDIENCE=<assertion audience (aud) from the registration> \
ADHD_MCP_SMART_CLIENT_ID=<client id> \
ADHD_MCP_SMART_KEY_ID=<key id of the registered public JWK> \
ADHD_MCP_SMART_SCOPE="launch system/Patient.read system/Condition.read system/Observation.read system/Encounter.read system/Procedure.read system/MedicationRequest.read system/Medication.read" \
ADHD_MCP_SMART_PRIVATE_KEY_FILE=/path/to/private-key.pem \
uv run adhd-mcp
```

The scope string above is a guess in the documented `launch` plus resource-scope form; **check it against the registration** (the developer portal lists the scopes for this API's CCG). No site code mapping exists for VA, so checks that need local codes report "not performed".

## Differences from a generic FHIR R4 server

| Area | Generic server (`generic` profile) | Lighthouse (`lighthouse` profile) | How the adapter handles it |
|---|---|---|---|
| Resource types the tools search | All 11 | Condition, Observation, Encounter, Procedure, MedicationRequest (and Medication by id). **Not offered:** QuestionnaireResponse, Flag, ServiceRequest, CarePlan, MedicationDispense, MedicationStatement | `SearchNotSupportedError` before any request; data completeness `not_supported`; dependent checks "not performed" |
| Date search | One parameter per type (`fhir/search.py`) | Condition `recorded-date` (also `onset-date`, `abatement-date`); Observation, Encounter, Procedure `date`. **MedicationRequest has none** | MedicationRequest is read whole and filtered in the adapter with the same `since` semantics |
| `_include` | `MedicationX:medication` | Not offered (no `searchInclude` in the CapabilityStatement) | Referenced Medication resources are read one by one (`GET Medication/{id}`), once each, same origin only. A missing or foreign one adds a `not-found` warning: the category is `incomplete`, never silently unclassified |
| References | Relative `Type/id` | Absolute URLs (`https://sandbox-api.va.gov/services/fhir/v0/r4/Patient/1000005`) | Normalization accepts absolute `.../Type/id` references (a generic fix) |
| Paging | `next` links | `next` links with `-pageToken`; `_count` default 100, **maximum 200**; `page` deprecated | Next links followed, same origin only; the adapter refuses a page size over 200 |
| `_lastUpdated` | Supported | Supported on every type | Unchanged |
| Patient ids | Any FHIR id | ICN: ten digits, `V`, six digits (the developer portal's own example is a sandbox test ICN); fits the FHIR id pattern | Unchanged |
| Authentication | SMART backend services: one system token, assertion audience = token URL, RS384 or ES384 | OAuth client credentials grant (CCG, "restricted access"). With `launch` in the scopes, each token request carries `launch` = base64 of `{"patient":"<ICN>"}`, so **each token is for one patient**. Assertion audience is an authorization-server URL given at registration. The documented example signs with RS256. Assertion `exp` at most 300 s after `iat`; `jti` optional (makes the assertion single-use). Tokens live 5 minutes | `LighthouseCcgAuth`: tokens kept per patient (at most 128, oldest dropped), refreshed 60 s before expiry; RS256 default (RS384, ES384 allowed); `ADHD_MCP_SMART_AUDIENCE` required. Tokens are patient-scoped only when the scope list contains the word `launch` exactly, as the portal's own page decides; any other scope list gets one system-level token |
| Token endpoint | Configured | CapabilityStatement: `https://sandbox-api.va.gov/oauth2/token`; the CCG page builds `https://sandbox-api.va.gov{baseAuthPath}/token` per API (production `https://api.va.gov{baseAuthPath}/token`) | A setting; check against the registration |
| Rate limits | n/a | Not stated in the OpenAPI description or CapabilityStatement | 429 is retried with backoff, honouring `Retry-After` (existing behaviour) |
| Data freshness | n/a | Condition: "available within 24 - 48 hours" | Stated in the limitations; an as-of date of today may miss the last two days |
| Production access | n/a | "To get production access using client credentials grant, you must either work for VA or have specific VA agreements in place" | Deployment guide |

## What the resource types contain (OpenAPI descriptions)

| Type | Lighthouse returns | Effect on ADHD_MCP |
|---|---|---|
| Condition | Problem-list items and encounter diagnoses; SNOMED CT and ICD-10-CM codings, ICD-10-CM written with the dot (`J01.21`) | The main signal source works as designed |
| Observation | "Only antibiotic sensitivity, bacteriology, lab chemistry, mycobacteriology, mycology and parasitology lab records, vital signs, and social history." Categories `laboratory`, `social-history`, `vital-signs` | **No screening instruments** (PHQ-9, PHQ-2, AUDIT-C, PC-PTSD-5, C-SSRS, ASRS): `get_screening_history` finds none. See data-shape findings below |
| Encounter | "Only inpatient and outpatient encounters" | No emergency class is documented, so acute-care and injury visits that rely on the `EMER` class may be under-counted; crash and injury codes on Conditions still count. To be checked on sandbox data |
| Procedure | "An inpatient surgery only" | The ADHD evaluation procedure check finds nothing (and needs a site mapping anyway) |
| MedicationRequest | "Only CPRSOrders and outpatient prescriptions. IV medications are not returned" | Orders are the whole medication record; the timeline uses them (no dispenses) and fill status is unknown |
| Patient | Demographics of anyone with a VA visit | Unchanged |

## Data-shape findings (item 2)

The research report's first integration question was whether screening instruments appear as LOINC-coded observations or need mapping from local codes. For the Lighthouse Patient Health API the answer, from its own documentation, is **neither: they are not exposed**. Its Observation endpoint returns laboratory results, vital signs and social history only, and it offers no QuestionnaireResponse. No mapping was added, because there is nothing to map.

Consequences:

- The PHQ-9 item 9 and C-SSRS safety gate checks would stay "not performed" on Lighthouse even after LOINC is verified (open question 14).
- ASRS results (open question 12) cannot come from this API. A deployment that needs them needs another VA data source, which is outside this plan.
- Social-history Observations may carry housing or employment findings; the psychosocial tool already reads coded social-history values. Which codes VA uses is unknown until sandbox data can be read.

Still unknown without sandbox access: whether sandbox patients carry any mental health codes, whether `meta.security` labels appear (see the [security label review](../security/lighthouse_security_labels.md)), and how emergency visits are classed.

## Tests

- `tests/adapters/test_lighthouse_adapter.py`: the shared adapter suite against `tests/helpers/fake_lighthouse.py` (offered types only, 400 on any parameter Lighthouse does not offer, no `_include`, absolute references, `-pageToken` links); the profile against the recorded CapabilityStatement; medication reads; the CCG with patient-scoped tokens; a full assessment end to end.
- No test needs credentials or network.

## To finish the exit criterion

1. Register for Lighthouse sandbox CCG access to the Patient Health API (open question 5): a JWK public key, then the client id, scopes, token URL and audience.
2. Start the server with the settings above and call `assess_referral_need` for a sandbox test patient (test ICNs are on the developer portal's test data page), for example from the MCP Inspector ([client guide](../guide/clients.md)).
3. Record any difference found here, and add sandbox responses (synthetic patients only) under `tests/adapters/recorded/`.
