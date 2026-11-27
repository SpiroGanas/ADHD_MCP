# Deployment guide

Phase 8, item 7. What a health system would need to run ADHD_MCP. It is written for the people who would decide whether and how to host it: an informatics lead, a security engineer, a privacy officer and a clinical sponsor.

**Read this first.** ADHD_MCP is not clinically validated. It has only ever read synthetic data. Nothing here makes it ready for clinical use; it lists what a site would have to put in place before even a silent pilot. Its outputs are suggestions to consider referral for formal screening, never a diagnosis ([intended use](../clinical/intended_use.md)).

## 1. Boundary and hosting assumptions

```
 Clinician's AI assistant ──MCP over HTTPS (OAuth bearer)──▶ gateway ──▶ ADHD_MCP ──FHIR GET (server's own token)──▶ EHR FHIR API
        (inside the boundary)                                 TLS, rate limits     (container)                     (Lighthouse, Oracle Health, ...)
                                                                                     │
                                                                                     └──▶ audit store (append-only JSON Lines, or the site's own)
```

| Assumption | Why | Where it is enforced |
|---|---|---|
| The server, the MCP client and any language model the client uses all run **inside the organization's authorized boundary** for protected health information | Tool outputs contain evidence from the record; sending them to an external model service would move PHI outside the boundary (risk P4) | Deployment decision; the server itself calls no model |
| A **gateway** in front of the server terminates TLS and applies rate limits | The server speaks plain HTTP and leaves rate limiting to the host (threat model T12, risk S6) | Gateway configuration |
| The server runs as the **container image** built from the repository's `Dockerfile` (non-root user, no development dependencies) | Reproducible, minimal runtime | `docker build -t adhd-mcp .`; CI builds and smoke-tests it |
| **One server per FHIR back end**, configured with that back end's profile (`generic` or `lighthouse`) and the site's code mapping | Profiles and site codes describe one server | `ADHD_MCP_FHIR_SERVER_PROFILE`, `ADHD_MCP_SITE_CODES` |
| The server has **read-only** credentials to the FHIR API | The server never writes (standing invariant 4), and least privilege protects against a defect anyway | Request only `.read` or `.rs` system scopes |
| Nothing is published to a public registry | Owner decision for 1.0 (open question 18) | The site builds its own image |

Out of scope: patient-facing use, CDS Hooks, automated orders, and any use that lets a model decide eligibility.

## 2. Authentication

Two independent trust relationships ([ADR 0012](../adr/0012-authentication.md)). The server never forwards a caller's token to the FHIR server.

### Callers to the server (OAuth resource server)

- Run with `ADHD_MCP_TRANSPORT=http` and the `ADHD_MCP_AUTH_*` settings ([configuration](configuration.md#http-with-oauth)): the site's authorization server issues tokens whose audience is this server's resource URL.
- Grant scope `adhd.evidence.read` for the evidence tools and `adhd.referral.assess` for `assess_referral_need` and `draft_referral_proposal`, only to clinician-facing assistants approved by the site.
- `ADHD_MCP_ALLOW_UNAUTHENTICATED_HTTP` is for a developer's own machine only and is refused unless bound to 127.0.0.1.

### The server to the FHIR API

| Back end | Setting | Notes |
|---|---|---|
| A generic FHIR R4 server | SMART backend services: `ADHD_MCP_SMART_*` | Register a confidential client with a public JWK; signs with RS384 or ES384 |
| VA Lighthouse | `ADHD_MCP_FHIR_SERVER_PROFILE=lighthouse`, `ADHD_MCP_SMART_*` and `ADHD_MCP_SMART_AUDIENCE` | Client credentials grant with patient-scoped tokens; production access needs VA employment or a VA agreement ([Lighthouse](../integration/lighthouse.md)) |
| Oracle Health | Not built | [Desk review](../integration/oracle_health.md) |

Keep the private key in a file readable only by the server's user, mounted from the site's secret store; the setting names the file, never the key. Rotate keys on the site's schedule; the `kid` setting selects the active one.

## 3. Data and privacy configuration

- **Sensitive-data policy.** Copy `src/adhd_mcp/data/privacy.toml`, have the privacy officer choose `allow`, `cite` or `withhold` per category (substance use, HIV, sickle-cell disease), add value sets for site codes, medications and laboratory tests the site considers protected, and point `ADHD_MCP_PRIVACY_POLICY` at it. On Lighthouse no security labels are documented, so classification is by code alone ([review](../security/lighthouse_security_labels.md)).
- **Site code mapping.** Psychiatric stays, high-risk flags and ADHD referrals, evaluations and care plans use local codes. Without a mapping (`ADHD_MCP_SITE_CODES`) those checks are reported "not performed". A mapping is clinical content: it needs the same review as a value set.
- **Clinical content.** The ruleset must be `released` (hash-pinned) before any clinical use; ruleset `adhd 1.0.0` is still a draft. Experimental stubs (`ADHD_MCP_EXPERIMENTAL_CONDITIONS`) and the dummy scorer (`ADHD_MCP_SCORER=dummy`) must stay off.

## 4. Audit and retention

- Set `ADHD_MCP_AUDIT_FILE` (required over HTTP). Each tool call writes one record: time, trace id, tool, caller (token subject and client id), outcome and error code, patient reference, resource references read with versions, the server, contract, ruleset, scorer and privacy policy versions, the recommendation code and a sha256 of the output. Records never contain clinical values or free text ([ADR 0011](../adr/0011-audit-tracing-and-privacy.md)).
- The file is append-only from the server's side but has no tamper evidence (risk P5). Ship it to the site's audit store (write-once storage, or a FHIR AuditEvent sink, which is future work) and restrict who can read it: references and hashes are still PHI-adjacent.
- **Retention** follows the site's records schedule for clinical decision support audit trails. Keep records at least as long as the outputs could be questioned, and long enough to re-derive any output: with the record versions and the output hash, an output can be checked against a re-run on the same versions.
- Correlate with the client's logs through the W3C `traceparent` trace id, which the server also sends to the FHIR API.

## 5. Monitoring

| Signal | Source | Alert when |
|---|---|---|
| Availability and latency | Gateway metrics; the 2 s p95 target for a full assessment ([performance](../evaluation/performance.md)) | Sustained p95 above target, or errors |
| FHIR failures | Audit records with outcome `error` and error code `fhir_unavailable`; outputs whose data completeness reports `failed` or `incomplete` | A rise above the site's baseline: assessments then end as `insufficient_data` |
| Authentication failures | Gateway 401 and 403 counts; token errors toward the FHIR API | Any sustained rise |
| Recommendation mix | Audit `recommendation` codes per day | A shift without a change in ruleset version, which suggests a data or mapping change upstream |
| Version drift | Audit versions | Any version the site has not approved |
| Logs | Python logging to standard error | Logs carry references and hashes only; a canary test guards this (risk P2) |

There is no built-in health endpoint; probe the MCP endpoint through the gateway, or call `get_server_info`, which reads no patient data.

## 6. Governance documents required before any clinical use

None of these exist yet. Each is the deploying organization's, not this project's.

| Document | Owner | Content |
|---|---|---|
| Intended use and clinical safety case | Clinical sponsor, clinical safety officer | The setting, users and decisions supported; hazards (false reassurance from a "no recommendation", alert fatigue, missed self-harm signals) with controls; based on the [intended use](../clinical/intended_use.md), [risk register](../clinical/risk_register.md) and rule cards |
| Clinical content approval | Clinical reviewer | Sign-off of the signal catalog, rule card, wording, value sets, drug classes and site code mapping; ruleset status `released` |
| Local validation protocol | Clinical sponsor, research office | Evaluation on local data before use: agreement with chart review, rates by sex, age and race, and a silent-mode period; ethics review where required |
| Privacy impact assessment | Privacy officer | Lawful basis for reading the record, the sensitive-data policy (38 U.S.C. 7332, 42 CFR Part 2), audit access, retention |
| Security authorization | Information security | Threat model review ([threat model](../security/threat_model.md)), hosting, key management, gateway, penetration test, the authority to operate the site's process requires |
| AI model use statement | Informatics, privacy | Which language model the client uses, where it runs, what it may receive, and how its use is monitored (the server's outputs are designed for a model to relay, but the model is outside this project) |
| Regulatory position | Regulatory counsel | Whether the deployment stays within non-device clinical decision support; patient-facing use or opaque scores would change it |
| Operations runbook | Operations | Start, stop, key rotation, ruleset and version upgrades, incident response, rollback |
| Monitoring and review plan | Clinical sponsor | Who reviews recommendation trends and overrides, how often, and when to suspend use |

## 7. Upgrades

Each release reports three version lines: server, tool contract and ruleset ([ADR 0013](../adr/0013-versioning-and-release.md)). A new tool contract may change what clients and prompts see; a new ruleset version is a clinical content change that needs approval before deployment. Run `uv run python scripts/release_check.py` on the tagged version, and keep the previous image for rollback.
