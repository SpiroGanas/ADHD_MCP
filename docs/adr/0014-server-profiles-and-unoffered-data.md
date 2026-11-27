# ADR 0014: FHIR server profiles, data a server does not offer, and patient-scoped tokens

- **Status:** Proposed (owner decisions of 2026-11-27 cover the behaviour; the owner accepts this record with the Phase 8 pull request)
- **Date:** 2026-11-27
- **Decided by:** Project owner (behaviour), Claude Code agent (design)

## Context

Phase 8 connects the server to VA Lighthouse, whose Patient Health API offers only 5 of the 11 resource types the tools search, has no `_include`, no date search on MedicationRequest, absolute references, and an OAuth client credentials grant whose tokens are scoped to one patient ([Lighthouse](../integration/lighthouse.md)). Oracle Health differs again ([desk review](../integration/oracle_health.md)). ADR 0004 requires one port with interchangeable adapters; ADR 0012 assumed one system-level SMART token.

## Decision

1. **Server profiles as data.** One HTTP adapter serves every back end; a `ServerProfile` (`fhir/profiles.py`, `data/fhir_servers/`) states the types offered, types without date search (filtered in the adapter with the shared semantics), whether medications can be included (otherwise read by id, same origin, valid ids only) and the page size limit. Every profile must offer Condition and Encounter.
2. **`not_supported` is its own data status** (tool contract 0.4.0). A type the server does not offer raises `SearchNotSupportedError` before any request and is reported `not_supported`. Logic sees it as unknown, never as empty: a check that needs it is "not performed"; a missing Condition fails the safety gate; an empty record is still insufficient data. One owner-approved exception: without dispenses and statements, medication orders are the medication record, and the antidepressant signal says it was counted from orders only.
3. **Auth knows the patient.** `FhirAuth.access_token(patient_id)`; `LighthouseCcgAuth` keeps one token per patient (bounded cache) when the scopes include `launch`, sends the `launch` parameter, and uses a configured assertion audience. Every request carries the token for the patient it concerns; a 401 renews only that patient's token. This amends ADR 0012, which assumed one system token.

## Alternatives considered

| Option | Why not |
|---|---|
| A separate adapter class per vendor | Duplicates paging, retries, origin pinning and fault handling, which are the hard, tested parts |
| Report unoffered types as `failed` | Every Lighthouse assessment would be insufficient data, and the output would claim an outage that is really a permanent gap |
| Report unoffered types as `empty` | A check would say "not found" about data that cannot exist on the server: partial data passing as clean |
| One system token for Lighthouse | Not what Lighthouse's client credentials grant issues when `launch` is in the scopes |

## Consequences

- Adding a back end is mostly a data file plus a recorded CapabilityStatement test; an `oracle` profile needs per-type date parameter names first.
- Outputs on thin back ends are honest but limited: many checks "not performed", the gate at best `clear_limited_data`.
- The token cache holds up to 128 patient tokens in memory for at most their 5-minute lifetime; it is never written anywhere.
- Threat T18 (a token used for another patient) is tested; the scope-word rule for patient scoping is documented.
