# ADR 0004: Synthetic data first behind a FHIR abstraction

- **Status:** Accepted
- **Date:** 2026-11-26
- **Decided by:** Project owner

## Context

The project has no access to real health records and must never hold any in this repository. The long-term target is the VA, which runs two FHIR back ends (VistA-derived data through Lighthouse, and Oracle Health) with differences that are not yet known.

## Decision

Develop and test entirely on synthetic FHIR R4 data. All data access goes through a read-only FHIR port with interchangeable adapters: file fixtures, a generic FHIR R4 server over HTTP, and later VA Lighthouse. Every adapter must pass one shared behavioral test suite.

## Alternatives considered

| Option | Why not |
|---|---|
| Target VA Lighthouse from the start | Needs credentials and approval; ties early design to one vendor's quirks |
| Generic FHIR only, no VA consideration | Would ignore known requirements such as specially protected data and dual back ends |

## Consequences

- Hand-built personas carry the clinical meaning; generated synthetic populations are used only for volume.
- Results on synthetic data show the code matches the intended rules, not real-world accuracy.
- Normalization must tolerate differing representations of the same fact, such as screening instruments as observation panels or questionnaire responses.
- VA-specific work is deferred to Phase 8 and may reveal gaps in the port.
