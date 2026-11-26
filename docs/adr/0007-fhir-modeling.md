# ADR 0007: Narrow internal FHIR models

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Project owner (options proposed by the developer)

## Context

Phase 2 needs typed access to FHIR R4 data. The options were a full FHIR model library for every resource, or raw JSON at the adapter boundary converted to small models the project owns. Real servers (VA Lighthouse, Oracle Health) are expected to send resources that are valid enough to use but not always valid against a strict full model.

## Decision

- Adapters return raw FHIR JSON (`dict`). They never parse resources into a full model library.
- `adhd_mcp.fhir.normalize` converts raw resources into narrow, frozen Pydantic records (`adhd_mcp.fhir.records`) that hold only what rules need: codes, statuses, dates, values, and the resource reference and version.
- Records omit names, identifiers, addresses and free text. A free-text observation value is recorded only as "text present".
- `fhir.resources` (R4B models, version 8.3.0) is a development dependency, used only in tests to check that persona bundles are valid FHIR. No R4 package is published for that library version; R4B differs from R4 mainly in resources this project does not read, and the integration tests also load every persona into a HAPI FHIR R4 server, which validates them as R4.

Normalization rules recorded here because later phases depend on them:

| Topic | Rule |
|---|---|
| Dates | `date`, `dateTime`, `instant` and `Period` all become a `DateRange` (start, end, precision). Partial dates cover their whole year or month. A dateTime keeps its calendar date as written; time zones are not converted |
| Codes | System OIDs and URL variants map to one canonical URI (data file `terminology/code_systems.toml`). ICD-10-CM codes are upper-cased. Codes are otherwise kept as sent; an undotted ICD-10-CM code is not repaired |
| Status | `entered-in-error` resources are excluded; refuted conditions are excluded. All other statuses are kept and labelled for later phases to judge |
| Unusable data | A resource with no id, a malformed value, or an unsupported type is skipped and reported, never silently dropped and never guessed |
| Medications | `medicationCodeableConcept`, contained `Medication` and referenced `Medication` (from the same search's `_include`) all resolve to medication codes |

## Alternatives considered

| Option | Why not |
|---|---|
| `fhir.resources` for every resource at runtime | Rejects resources that are usable but imperfect; heavier and slower; couples the code to one library's release cycle |
| Internal models only, with a hand-written validator for personas | Duplicates work a mature library already does for test fixtures |

## Consequences

- Each new field a rule needs is added deliberately to a record, with a test.
- Undotted ICD-10-CM codes from a real server would not match value sets. Revisit when Phase 8 shows real data shapes.
