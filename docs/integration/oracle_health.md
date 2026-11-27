# Oracle Health Millennium FHIR R4: desk review

Phase 8, item 3. A desk review of Oracle Health's Millennium Platform FHIR R4 API against the server's read-only FHIR port (`fhir/port.py`), listing the gaps. VA's Federal EHR runs on Oracle Health, so this is the second VA back end after Lighthouse. 2026-11-27, by the Claude Code agent.

**No adapter was built.** The plan says to build one only if sandbox access is available. Oracle runs an **open sandbox that needs no credentials** (`https://fhir-open.cerner.com/r4/ec2458f2-1e24-41c8-b71b-0e701af7583d/`), but its host is not reachable from the development environment, and this phase did not ask to add it. Building an `oracle` server profile against that sandbox is proposed in the [next-stage plan](../next_stage_plan.md).

## Sources (read 2026-11-27)

- FHIR R4 APIs for Oracle Health Millennium Platform, `https://docs.oracle.com/en/industries/health/millennium-platform-apis/mfrap/`: R4 overview, service root URL, REST endpoints, and the search operation page of each resource type below. (`fhir.cerner.com/millennium/r4/` now redirects to these pages.)
- Not read: the "Authorization Framework" pages (on wiki.cerner.com), which describe system accounts.

## Resource coverage

| Port search type | Oracle R4 | Notes |
|---|---|---|
| Condition | Search | Categories problem-list-item, encounter-diagnosis, health-concern, sdoh. **No date search parameter** (only `_lastUpdated`) |
| Observation | Search | `date` (eq, ge, gt, le, lt); `_count` default 50, **maximum 200**; social history is all on the first page |
| QuestionnaireResponse | Search | **Only `_id` or `patient`**: no date search |
| MedicationRequest | Search | **No date search** (`_lastUpdated` only, with prefixes) |
| MedicationDispense | Search | Date parameter is **`date`** (handed over), not `whenhandedover`; single value, `ge` or `gt` only; **cannot be combined with `_lastUpdated`** |
| MedicationStatement | **Not offered** | |
| Encounter | Search | `date` with a prefix; examples carry a time component |
| Procedure | Search | `date` over `performedDateTime` or `performedPeriod`; "with a prefix and time component" |
| ServiceRequest | Search | `authored`: "**Must include a time**"; first page holds all referral data |
| CarePlan | Search | `date` "**must use both `ge` and `le` prefixes in the same search**"; search also by `category` |
| Flag | **Not offered** | |
| Medication (referenced) | **No Medication resource** | Medication requests and dispenses are expected to carry the code inline (`medicationCodeableConcept`); to be confirmed on sandbox data |
| `_include` | Not offered | Only `_revinclude=Provenance:target` |

## Gaps against the port, and what an `oracle` profile would need

The `ServerProfile` built for Lighthouse already covers types not offered (`not_supported`), types without date search (filtered in the adapter) and the page size limit. Oracle needs three more capabilities:

1. **A date parameter name per type** (MedicationDispense uses `date`), not only "has one or not".
2. **Date value formats**: a time component on some types (`ge2025-01-01T00:00:00.000Z`), and both bounds on CarePlan. The simplest correct choice is to search those types without a date and filter in the adapter, as for Lighthouse's MedicationRequest.
3. **Parameter exclusivity**: MedicationDispense's `date` and `_lastUpdated` cannot be combined. The tools never send `_lastUpdated` today, so this matters only if `updated_since` is ever used.

Everything else fits: `next` links (with `pageContext` and `direction=NEXT`) are followed, same origin; ids are FHIR ids; OperationOutcome issues are returned on errors.

## Authentication

- OAuth 2.0 with SMART v1 and v2 scopes; every search used here supports the **System** authorization type, and system scopes exist for all nine types (for example `system/Condition.read`, `system/MedicationDispense.rs`).
- Discovery through `/.well-known/smart-configuration` and the CapabilityStatement's security extensions.
- Whether Oracle system accounts use the SMART backend-services `private_key_jwt` assertion (which `SmartBackendAuth` implements) or a client secret was not established from the pages read. If it is a client secret, a small `ClientSecretAuth` would be needed; that is a decision for the next stage.
- Tenant-specific service roots: `https://fhir-ehr-code.cerner.com/r4/{tenant}/` (secure sandbox, non-patient), `https://fhir-open.cerner.com/r4/{tenant}/` (open sandbox).

## Write operations

Oracle's API supports create, update and patch on several types, and a **method override** (`POST ...?_method=patch` or the `X-HTTP-Method-Override` header). The server is unaffected: the port has no write method, the HTTP adapter issues only GET, and the one allowlisted POST goes to the token endpoint (standing invariant 4, `tests/unit/fhir/test_read_only.py`). A deployment's credentials should still be read-only system scopes (`.read` or `.rs`), never `.write` or `.crus`.

## Security labels and filtering

- Oracle's own examples carry `meta.security` labels (v3-ActCode `PHY` "physician requested information sensitivity", `PRS` "patient requested information sensitivity"). The sensitive-data policy does not use these codes; it uses `ETH`, `ETHUD`, `SUD`, `OPIOIDUD`, `HIV` and `SCA`. Whether Oracle labels 38 U.S.C. 7332 data with those codes is unknown.
- "Encounter or organization security, privileges, and preference may filter data based on the build in the domain": records can be filtered upstream without notice. As with Lighthouse, a missing record is weak evidence of absence.
- Entered-in-error resources may be masked with a data-absent reason for patient personas; the server already skips entered-in-error records.

## Summary

| Item | Status |
|---|---|
| Types the tools search | 9 of 11 offered (no Flag, no MedicationStatement); more than Lighthouse, including QuestionnaireResponse, ServiceRequest, CarePlan and MedicationDispense |
| Adapter | Not built; an `oracle` profile needs per-type date parameter names and adapter-side filtering for types with unusual date rules |
| Sandbox | Open sandbox without credentials exists; host not yet allowed in the development environment |
| Authentication | SMART system scopes; system-account credential type to confirm |
