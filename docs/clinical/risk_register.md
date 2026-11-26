# Risk Register

Clinical safety, privacy, security and project risks. Review at the end of every phase and whenever a new risk is found. Add risks; do not delete them. Close them with a note.

**Scales.** Likelihood and impact: Low, Medium, High. Status: Open, Mitigated, Accepted, Closed.

**Last reviewed:** 2026-11-26 (initial version)

## Clinical safety

| ID | Risk | L | I | Mitigation | Phase | Status |
|---|---|---|---|---|---|---|
| C1 | A recommendation is read as a diagnosis by a clinician, an AI assistant or a patient | M | H | Fixed wording; not-a-diagnosis marker in the schema; output wording guard test; intended-use notice in every result; model-in-the-loop evaluation | 1, 5, 7 | Open |
| C2 | An ADHD referral distracts from or displaces a self-harm concern | M | H | Safety gate always runs and is presented first; ADHD recommendation withheld while the gate is positive | 3, 5 | Open |
| C3 | A "clear" safety gate is read as "no suicide risk" | M | H | Output states the gate reflects recorded signals only; lists what was checked; negative PHQ-9 item 9 never clears alone | 3 | Open |
| C4 | A rule uses a wrong or outdated code or cutoff | H | M | Verification backlog; strict loader refuses unverified entries; sources cited per value set | 1 to 4 | Open |
| C5 | The heuristic flags too many patients, wasting scarce evaluation capacity | M | M | Negative-case tests; threshold sensitivity analysis; rule card states limits | 5, 7 | Open |
| C6 | Women are under-flagged because key signals skew male | H | M | Measure on the designed cohort; document; bring options to the project owner | 7 | Open |
| C7 | ADHD-like presentations from TBI, PTSD or substance use are flagged without context | M | M | Look-alike personas; TBI overlap note routes to neuropsychological evaluation | 5, 7 | Open |
| C8 | An empty or partial record is treated as a clean record | M | H | Data-completeness note in every output; "insufficient data" outcome; fault-injection tests | 3, 7 | Open |
| C9 | Synthetic evaluation results are presented as evidence of accuracy | M | H | Required limitation text in every report and in the README | 7 | Open |
| C10 | The tool is used with real patients before validation | L | H | Intended-use statement; README notice; deployment guide lists required governance | 7, 8 | Open |

## Privacy

| ID | Risk | L | I | Mitigation | Phase | Status |
|---|---|---|---|---|---|---|
| P1 | Real patient data is committed to the repository | L | H | Synthetic-only rule; contributor guide; CI checks | 1 | Open |
| P2 | Clinical content leaks into logs, audit records or error messages | M | H | References and hashes only; canary-value test | 6 | Open |
| P3 | Specially protected data (substance use and similar) is disclosed beyond what is permitted | M | H | Configurable sensitive-data policy; disclosure of withheld categories; legal review before real use | 6, 8 | Open |
| P4 | Clinical content is sent to a language model outside the authorized boundary | M | H | Deployment guide; the server itself calls no external model in version 1.0 | 6, 8 | Open |

## Security

| ID | Risk | L | I | Mitigation | Phase | Status |
|---|---|---|---|---|---|---|
| S1 | Prompt injection through text in FHIR records or tool descriptions | M | H | Record text treated as data and delimited; injection twin-persona test; contract snapshots pin descriptions | 5, 6 | Open |
| S2 | A caller's token is forwarded to the FHIR server (confused deputy) | L | H | Server uses its own credentials; test asserts no passthrough | 6 | Open |
| S3 | An unauthenticated or over-scoped caller reads patient data | M | H | OAuth with audience checks and per-tool scopes; rejection tests | 6 | Open |
| S4 | A tool is changed to write to the record | L | H | Port has no write operation; test asserts no write requests; ADR 0002 | 2 | Open |
| S5 | Secrets committed or printed | L | H | Secret scanning in CI; configuration validation that never echoes secrets | 1, 6 | Open |

## Project

| ID | Risk | L | I | Mitigation | Phase | Status |
|---|---|---|---|---|---|---|
| J1 | MCP specification or FastMCP changes break the design | M | M | Pinned versions; ADRs; check documentation at the start of each phase | all | Open |
| J2 | No clinician is available to review clinical content | M | H | Open question 1 in status.md; rule cards mark review status | 3 | Open |
| J3 | An AI agent loses context between sessions and repeats or contradicts earlier work | M | M | status.md kept current; ADRs; `/resume` command | all | Open |
| J4 | Scope grows toward diagnosis, writes or patient-facing features | M | H | Hard rules in CLAUDE.md; ask before departing from the plan | all | Open |
| J5 | Lighthouse sandbox access is delayed or its data is too thin | M | L | Apply during Phase 6; recorded responses for tests | 8 | Open |
