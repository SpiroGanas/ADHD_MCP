# MCP + HL7 FHIR as the technical foundation for an EHR-reading mental-health referral-screening server (ADHD / autism / other MH), and its fit in a VA Learning Health System

Research date: 2026-11-26. Spec versions and dates are stated next to each claim.

Method note for the report writer: In this session WebSearch worked, but direct page fetches were blocked for several primary hosts: modelcontextprotocol.io, hl7.org, arxiv.org, department-of-veterans-affairs.github.io, verily.com and cov.com. The official MCP changelogs were read in full from the spec's GitHub source on raw.githubusercontent.com, and the MCP blog was readable. Most FHIR, LOINC, regulatory and paper details come from search-result extracts of the primary pages cited. Treat exact wording as "verify before quoting."

## Q1. What is the Model Context Protocol and what does the current spec define (primitives, client features, transports, authorization, structured output, security, governance)?

### Takeaway
MCP is an open JSON-RPC protocol that connects LLM hosts and clients to external "servers." Servers expose three primitives: tools, resources and prompts. Anthropic introduced it in Nov 2024, and it has been governed under the Linux Foundation's Agentic AI Foundation since 9 Dec 2025. As of Nov 2026 the latest released spec is **2026-07-28**. That revision makes the protocol stateless: no `initialize` handshake and no sessions. It deprecates Roots, Sampling, Logging, the old HTTP+SSE transport and OAuth Dynamic Client Registration. Elicitation stays, now delivered through "Multi Round-Trip Requests." Authorization is OAuth 2.1-based, with MCP servers acting as OAuth resource servers. A FHIR-reading server should target 2026-07-28 and stay backward compatible with 2025-11-25 clients.

### Cited Findings
**Origin, adoption, governance**
- MCP marked its first anniversary on 25 Nov 2025, the same day the 2025-11-25 spec was released, which dates the Anthropic launch to Nov 2024. — [MCP blog, "First MCP anniversary" (2025-11-25)](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/)
- Adoption at that release: "thousands of active MCP servers"; the MCP Registry had nearly 2,000 entries, a 407% increase from the initial batch onboarded in Sept 2025. Governance: 58 maintainers supporting 9 core/lead maintainers; 2,900+ Discord contributors; 17 SEPs handled in about a quarter; Working and Interest Groups formalized in SEP-1302. — [MCP blog (2025-11-25)](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/)
- On 9 Dec 2025 Anthropic donated MCP to the **Agentic AI Foundation (AAIF)**, a directed fund under the Linux Foundation co-founded by Anthropic, Block and OpenAI, with Google, Microsoft, AWS, Cloudflare and Bloomberg as supporters. The other founding projects are Block's goose and OpenAI's AGENTS.md. Existing maintainers keep technical decision-making through the SEP process; the LF provides neutral infrastructure and does not set technical direction. David Soria Parra is Lead Core Maintainer. Stats at donation: more than 97M monthly SDK downloads, about 10,000 active servers, and first-class client support in ChatGPT, Claude, Cursor, Gemini, Microsoft Copilot and VS Code. — [MCP blog, "MCP joins the Agentic AI Foundation" (2025-12-09)](https://blog.modelcontextprotocol.io/posts/2025-12-09-mcp-joins-agentic-ai-foundation/); [Linux Foundation press release](https://www.linuxfoundation.org/press/linux-foundation-announces-the-formation-of-the-agentic-ai-foundation)
- The 2025-11-25 release also added a formal governance structure (SEP-932), communication practices (SEP-994), Working and Interest Groups (SEP-1302) and an SDK tiering system (SEP-1730). — [MCP 2025-11-25 changelog (spec source)](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2025-11-25/changelog.mdx)

**Spec revision timeline (date-versioned: 2024-11-05 → 2025-03-26 → 2025-06-18 → 2025-11-25 → 2026-07-28)**
- **2025-06-18:** added structured tool output (`structuredContent`, with tools able to declare an output schema) and elicitation (`elicitation/create`, where the server asks the user for input against a JSON schema; servers must not request sensitive information this way). MCP servers were classified as **OAuth resource servers** that publish protected resource metadata for authorization-server discovery. Clients were required to implement **RFC 8707 resource indicators** so a malicious server cannot obtain tokens meant for another resource. — [MCP 2025-06-18 changelog](https://modelcontextprotocol.io/specification/2025-06-18/changelog); [Cisco DevNet summary](https://blogs.cisco.com/developer/whats-new-in-mcp-elicitation-structured-content-and-oauth-enhancements); [Speakeasy release notes](https://speakeasy.com/mcp/release-notes); [dev.to summary](https://dev.to/forgecode/mcp-2025-06-18-spec-update-security-structured-output-elicitation-1pin)
- **2025-11-25 (major):**
  - OpenID Connect Discovery 1.0 for authorization-server discovery (PR #797).
  - Icons metadata for tools, resources, resource templates and prompts (SEP-973).
  - Incremental scope consent via `WWW-Authenticate` (SEP-835).
  - Tool-naming guidance (SEP-986).
  - Standardized enum schemas for elicitation (SEP-1330).
  - **URL-mode elicitation** (SEP-1036).
  - **Tool calling inside sampling** via `tools` and `toolChoice` (SEP-1577).
  - **OAuth Client ID Metadata Documents (CIMD)** as the recommended client registration method (SEP-991).
  - **Experimental Tasks** for durable, pollable requests (SEP-1686).

  — [2025-11-25 changelog](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2025-11-25/changelog.mdx)
- **2025-11-25 (minor):**
  - stdio servers may log everything to stderr.
  - Invalid `Origin` headers on Streamable HTTP must get HTTP 403 (PR #1439).
  - Input-validation failures are returned as **Tool Execution Errors, not Protocol Errors**, so the model can self-correct (SEP-1303).
  - SSE polling and server-side disconnect (SEP-1699).
  - Protected Resource Metadata discovery aligned with **RFC 9728**, with a `.well-known` fallback (SEP-985).
  - Elicitation defaults (SEP-1034).
  - **JSON Schema 2020-12** is the default dialect (SEP-1613).
  - Request payloads decoupled into standalone parameter schemas (SEP-1319).

  — [2025-11-25 changelog](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2025-11-25/changelog.mdx)
- The 2025-11-25 blog post also lists authorization extensions: **Enterprise authorization / Cross-App Access** (SEP-990), so users sign in once and reach authorized servers; **OAuth client-credentials for machine-to-machine** use (SEP-1046, an extension); client security requirements for local server installation (SEP-1024); and default scopes (SEP-835). Extensions are optional, additive and independently versioned. The MCP Apps extension was announced separately. — [MCP blog (2025-11-25)](https://blog.modelcontextprotocol.io/posts/2025-11-25-first-mcp-anniversary/)
- **2026-07-28 (current release), major changes:**
  - **Protocol-level sessions and the `Mcp-Session-Id` header removed** (SEP-2567). Cross-call state uses server-minted handles passed back as tool arguments.
  - **`initialize` handshake removed** (SEP-2575). Protocol version and client capabilities travel in each request's `_meta`.
  - New required **`server/discover`** RPC for versions, capabilities and identity.
  - `subscriptions/listen` replaces the HTTP GET stream and `resources/subscribe`.
  - `ping`, `logging/setLevel` and roots list-changed notifications removed.
  - SSE resumability (`Last-Event-ID`) removed.
  - **Tasks moved to an official extension** (`io.modelcontextprotocol/tasks`, SEP-2663) using `tasks/get` and `tasks/update`.
  - **Multi Round-Trip Requests (MRTR, SEP-2322)** replace server-initiated `elicitation/create`, `sampling/createMessage` and `roots/list`. The server returns `resultType: "input_required"`, and the client retries with `inputResponses`.

  — [2026-07-28 changelog (spec source)](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/changelog.mdx); [MCP blog, "The 2026-07-28 Specification"](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- **2026-07-28, minor and schema changes:**
  - `extensions` field added to client and server capabilities.
  - **OpenTelemetry trace-context propagation in `_meta`** (SEP-414).
  - Deterministic ordering for `tools/list`.
  - Required `Mcp-Method` and `Mcp-Name` headers on Streamable HTTP POSTs, so gateways can route without parsing JSON (SEP-2243).
  - Cacheable results with `ttlMs` and `cacheScope` on list and read calls (SEP-2549).
  - Resource-not-found error code changed from -32002 to -32602 (SEP-2164).
  - `inputSchema` and `outputSchema` loosened to full JSON Schema 2020-12, and `structuredContent` may be any JSON value (SEP-2106).
  - URL-elicitation completion notification removed.
  - Error codes -32020 to -32099 reserved for MCP.

  — [2026-07-28 changelog](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/changelog.mdx)
- **2026-07-28 deprecations:** **Roots, Sampling and Logging deprecated** (SEP-2577). The **HTTP+SSE transport** and the `includeContext` values "thisServer" and "allServers" deprecated (SEP-2596). **OAuth 2.0 Dynamic Client Registration (RFC 7591) deprecated in favor of CIMD** (PR #2858). A formal deprecation policy sets a minimum 12-month window (SEP-2596), and the SEP workflow became PR-based (SEP-1850). The blog states explicitly: "Elicitation is not removed. It continues through MRTR." Tasks, MCP Apps and Enterprise Managed Authorization (EMA) are named extensions. The TypeScript, Python, Go and C# SDKs support 2026-07-28; Rust support is in beta. — [2026-07-28 changelog](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/changelog.mdx); [MCP blog (2026-07-28)](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- **2026-07-28 authorization changes:** authorization servers SHOULD return the RFC 9207 `iss` parameter and clients MUST validate it, closing the authorization-server mix-up gap (SEP-2468). Clients declare `application_type` at registration so localhost redirects from desktop and CLI apps are not rejected (SEP-837). Client credentials are bound to their issuing authorization server (SEP-2352). — [2026-07-28 changelog](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/changelog.mdx)
- The release was widely reported as "MCP went stateless," so any server instance behind a plain load balancer can serve a request. Google's developer blog described it at one point as a release candidate; the official blog treats it as released. — [WorkOS](https://workos.com/blog/mcp-stateless-spec-2026-07-28); [Google Developers Blog](https://developers.googleblog.com/scaling-ai-agent-infrastructure-with-the-mcp-stateless-updates/); [Equixly security analysis](https://equixly.com/blog/2026/08/05/stateless-mcp/)

**Primitives, client features and transports in the current spec**
- Server primitives are tools (`tools/list`, `tools/call`), resources (`resources/list`, `resources/read`, resource templates) and prompts (`prompts/list`). In 2026-07-28 all list and read results carry caching fields. Client features have changed: sampling and roots are now deprecated, and elicitation (form mode plus URL mode) continues through MRTR. — [2026-07-28 changelog](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/changelog.mdx); [2025-11-25 changelog](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2025-11-25/changelog.mdx)
- The current transports are **stdio** and **Streamable HTTP**. The legacy HTTP+SSE transport is deprecated with a one-year migration window. — [MCP blog (2026-07-28)](https://blog.modelcontextprotocol.io/posts/2026-07-28/)

**Authorization model**
- MCP server = OAuth 2.1 resource server; MCP client = OAuth 2.1 client; a separate authorization server issues tokens. Servers MUST implement RFC 9728 Protected Resource Metadata, which includes `authorization_servers`. Clients MUST use RFC 8414 authorization-server metadata. Clients send the RFC 8707 `resource` parameter, and **servers MUST validate that tokens were issued specifically for them (audience)**. PKCE is required for public clients (third-party guides say S256; I did not see the exact normative PKCE text). — [MCP authorization spec 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization); [MCP authorization 2025-06-18](https://modelcontextprotocol.io/specification/2025-06-18/basic/authorization); [WorkOS explainer](https://workos.com/blog/what-is-mcp-authorization)

**Security best practices**
- **Token passthrough is explicitly forbidden**: MCP servers MUST NOT accept tokens that were not issued for the MCP server, and must not forward client tokens downstream. **Confused deputy**: MCP proxy servers that front third-party APIs MUST implement per-client consent. The 2025-11-25 and 2026-07-28 security pages expand the confused-deputy and consent sections. — [MCP Security Best Practices (2025-11-25)](https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices); [draft version](https://modelcontextprotocol.io/specification/draft/basic/security_best_practices)
- OWASP advises treating the **entire tool schema** as a prompt-injection surface, pinning reviewed tool definitions by cryptographic hash, validating every tool input (inputs are LLM output that may be adversarially shaped), and watching for exfiltration through legitimate channels. The Cloud Security Alliance (May 2026) defines **tool poisoning** as indirect prompt injection carried in server metadata, and recommends eliminating token passthrough and scoping tokens per invocation with least privilege. — [OWASP MCP Security Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/MCP_Security_Cheat_Sheet.html); [CSA whitepaper (2026-05-16)](https://labs.cloudsecurityalliance.org/research-rb/csa-whitepaper-mcp-security-agentic-attack-surface-20260516/)

### Inferences
- A FHIR-backed MCP server should not act as a token-passthrough proxy to the EHR. It should hold its own SMART credentials (or do a token exchange), validate the MCP token's audience, and enforce per-client consent. That is the confused-deputy/token-passthrough pattern the spec forbids, and it maps directly onto "MCP server in front of FHIR."
- The 2026-07-28 statelessness suits a horizontally scaled, VA-hosted service. Per-request `_meta` with OpenTelemetry trace context (SEP-414) and `server/discover` identity and version give natural hooks for audit and model-version logging (see Q8).
- Because sampling is deprecated, LLM reasoning should run in the host or client, or in a server-side model the server calls directly with explicit governance, rather than through MCP sampling.
- Structured tool output (`outputSchema` plus `structuredContent`) lets a screening tool return machine-checkable results, such as a FHIR `RiskAssessment`-shaped JSON, instead of free text.

### Gaps
- modelcontextprotocol.io pages could not be fetched, so the normative wording of the 2026-07-28 authorization and security pages (PKCE text, exact MUSTs) was not read directly. The changelogs were read from the GitHub spec source.
- I found no official statement of a post-2026-07-28 release. Only a "draft" changelog exists, and its contents were not retrieved.
- The details of the Enterprise Managed Authorization extension and the MCP Apps extension were not retrieved.

## Q2. Which FHIR R4 / US Core resources and USCDI data elements are needed for a mental-health referral-screening server?

### Takeaway
The server needs read access to roughly 15 resource types:
- Patient, Encounter, Condition (problem-list and encounter-diagnosis categories)
- Observation (screening and assessment scores via the US Core Observation Screening Assessment profile; social history; vitals)
- QuestionnaireResponse
- MedicationRequest / MedicationDispense / MedicationStatement
- Procedure, AllergyIntolerance
- DocumentReference (notes), CarePlan

It would write, or propose, ServiceRequest (the referral), RiskAssessment, Flag or DetectedIssue, and Provenance, with AuditEvent for logging. US Core 8.0.x aligns with USCDI v5. US Core 9.0.0 is reported as the current published release. USCDI v6 (July 2025) carries Health Status Assessments: Mental/Cognitive Status, Alcohol Use, Substance Use, Physical Activity and SDOH Assessment.

### Cited Findings
- **US Core versions:** US Core 8.0.0 (STU8) references USCDI v5 (July 2024). The Jan 2025 ballot added USCDI v5 elements, for example route of administration on MedicationRequest and MedicationDispense, and Immunization.lotNumber. 8.0.0 added the US Core Observation ADI Documentation and ADI DocumentReference profiles, the Authentication Time extension and the Interpreter Needed extension. 8.0.1 fixed a breaking issue by adding an Individual Sex extension and deprecating the old Sex extension. — [US Core changes (2025Jan ballot)](https://hl7.org/fhir/us/core/2025Jan/changes.html); [US Core 8.0.1 changes](https://build.fhir.org/ig/HL7/US-Core/branches/8.0.1/changes.html)
- The hl7.org US Core change log reports **US Core 9.0.0 (STU9)**, on FHIR R4, as the current published version, balloted Jan 2026. — [US Core change log](https://hl7.org/fhir/us/core/changes.html)
- US Core publishes a PHQ-9 example as an Observation panel (LOINC 44249-1), showing screening instruments represented as Observation panels with member item Observations. — [US Core 8.0.1 example Observation PHQ9 panel](https://hl7.org/fhir/us/core/STU8.0.1/Observation-PHQ9-panel-example-44249-1.xml.html)
- US Core also publishes an **AUDIT-C Questionnaire** and item Observation examples (75626-2), illustrating the Questionnaire → QuestionnaireResponse → Observation pattern. — [US Core AUDIT-C Questionnaire](https://hl7.org/fhir/us/core/Questionnaire-AUDIT-C.html); [AUDIT-C item example](https://build.fhir.org/ig/HL7/US-Core/branches/8.0.1/Observation-AUDIT-C-item-example-75626-2.xml.html)
- **USCDI:** v4 added 20 data elements, including **Alcohol, Substance Use and Physical Activity Assessments**, treatment-intervention and care-experience preferences, and medication adherence. v5 was published 16 July 2024 with 16 new data elements and 2 new data classes. **v6 (July 2025)** lists the Health Status Assessments class (Mental/Cognitive Status, Alcohol Use, Substance Use, Physical Activity, SDOH Assessment) and adds SDOH Problems/Health Concerns and SDOH Interventions (under Procedures). — [USCDI v6 (July 2025) PDF](https://isp.healthit.gov/sites/default/files/2025-07/USCDI-Version-6-July-2025.pdf); [USCDI v5 (July 2024) PDF](https://healthit.gov/wp-content/uploads/2025/03/USCDI-Version-5-July-2024-Final.pdf); [USCDI v4 tech forum slides](https://healthit.gov/wp-content/uploads/2023/11/USCDIv4_Update_CertProgram_TechForum_508.pdf); [USCDI Health Status Assessments class](https://isp.healthit.gov/uscdi-data-class/health-status-assessments?page=1)
- In USCDI, "SDOH Assessment" is defined as a screening-questionnaire-based, structured evaluation for an SDOH-related risk, and "Substance Use" as an evaluation of reported non-medical use of drugs or other substances. — [USCDI Health Status Assessments](https://isp.healthit.gov/uscdi-data-class/health-status-assessments?page=1)
- **Gravity Project SDOH Clinical Care IG**, current release **2.3.0 (STU 2.3)** on FHIR R4, covers screening, assessment/diagnosis, goals and interventions. **Referrals are tracked with Task + ServiceRequest.** Task moves from "requested" to "received" as the receiver confirms, and intermediaries create their own ServiceRequest pointing to the source request. For referrals to further assessment, `Task.output` references the findings (QuestionnaireResponse, Observations), and completed services are reported as Procedures. It depends on US Core 3.1.1, 6.1.0 and 7.0.0. It differs from BSeR, which exchanges self-contained Bundles. — [SDOH Clinical Care IG](https://hl7.org/fhir/us/sdoh-clinicalcare/); [exchange workflow](https://hl7.org/fhir/us/sdoh-clinicalcare/exchange_workflow.html)
- **AI-output representation:** the HL7 **AI Transparency on FHIR** IG (STU1 ballot, 2026Jan) requires that every AI-influenced resource SHALL carry a `meta.security` label (AIAST code), which it calls the authoritative indicator. Provenance is optional and records model, inputs (including the AI input prompt as an entity) and human verifier as agents. Consumers SHALL NOT infer that AI was not involved from the absence of Provenance. Model details go in a Device resource plus a Model-Card DocumentReference. The IG is built on R4 and is forward-compatible with R5 and R6, and NIST contributes to it. — [AI Transparency on FHIR (2026Jan ballot)](https://hl7.org/fhir/uv/aitransparency/2026Jan/index.html); [general guidance](https://build.fhir.org/ig/HL7/aitransparency-ig/en/general_guidance.html); [NIST project page](https://www.nist.gov/programs-projects/hl7-ai-transparency-fast-healthcare-interoperability-resources-fhir)

### Inferences
- A minimal read set for ADHD, autism and MH referral screening:
  - Patient (age, sex)
  - Condition, both categories: problem-list (F90, F84, F43.1, depression, SUD) and encounter-diagnosis
  - Observation, category survey / screening-assessment: PHQ-2/9, PC-PTSD-5, C-SSRS, AUDIT-C, ASRS
  - QuestionnaireResponse (item-level answers)
  - MedicationRequest / MedicationDispense (stimulants, atomoxetine, SSRIs, antipsychotics, naltrexone)
  - Encounter (MH clinic visits, ED visits)
  - Procedure (psychotherapy, prior neuropsych testing)
  - DocumentReference (free-text notes, the main NLP input)
  - CarePlan / ServiceRequest (to avoid recommending an already-placed referral)
  - Flag (e.g., a VA High Risk for Suicide flag, if exposed)
- For outputs, the cleanest FHIR-native pattern is: a **RiskAssessment** (prediction, probability, basis = referenced evidence) + a **proposed ServiceRequest** (intent = proposal) or a CDS Hooks suggestion + **Provenance** with AI-Transparency labels. Write-back should only happen after clinician acceptance.
- Resource definitions for RiskAssessment, DetectedIssue, Flag, Provenance and AuditEvent are in the base FHIR R4 spec (https://hl7.org/fhir/R4/riskassessment.html, https://hl7.org/fhir/R4/provenance.html, https://hl7.org/fhir/R4/auditevent.html). These canonical pages could not be fetched in this session, so element-level detail is not quoted here.

### Gaps
- hl7.org was not fetchable, so I could not confirm the exact name and version history of the "US Core Observation Screening Assessment" and "US Core Simple Observation" profiles (believed introduced in US Core 6.x). I also could not confirm whether US Core 9.0.0 aligns to USCDI v6.
- I did not retrieve which USCDI version ONC/ASTP currently requires as the certification baseline, or how the HTI-5 deregulatory proposal affects it.
- I did not confirm whether US Core publishes PHQ-9 item 9 or C-SSRS-specific profiles beyond examples.

## Q3. Terminologies: ICD-10-CM, SNOMED CT, LOINC, RxNorm, value sets

### Takeaway
Validated screening instruments have well-defined LOINC panels and score codes that a FHIR server can query directly. The ones verified this session are PHQ-9, PHQ-9 item 9, PC-PTSD-5, the C-SSRS screener, AUDIT-C and the ASRS v1.1 symptom checklist. Instrument and LOINC text is copyrighted (Pfizer for PHQ, Dr. Kelly Posner for C-SSRS, Regenstrief for LOINC), which matters for redistribution in prompts and resources.

### Cited Findings
- **PHQ-9:** panel **44249-1** (PHQ-9 quick depression assessment panel); total score **44261-6** (range 0–27); item 9 **44260-8** ("Thoughts that you would be better off dead, or of hurting yourself in some way in last 2 weeks"). Items are scored 0–3. Severity bands are 1–4 minimal, 5–9 mild, 10–14 moderate, 15–19 moderately severe and 20–27 severe. The PHQ is copyright Pfizer Inc. — [LOINC 44249-1](https://cdn.loinc.org/44249-1); [LOINC 44261-6](https://cdn.loinc.org/44261-6); [findacode 44261-6](https://www.findacode.com/loinc/44261-6--patient-health-questionnaire-9-item-phq-9-total-score-reported.html); [LOINC 79540-1 HEDIS value set page](https://loinc.org/79540-1/panel)
- **PC-PTSD-5:** panel **102010-6**; score **102017-1** (0–5); item 1 (trauma exposure) **102011-4**. A positive screen requires further assessment. — [LOINC 102010-6 panel](https://cdn.loinc.org/102010-6/panel); [LOINC 102017-1](https://cdn.loinc.org/102017-1); [findacode 102011-4](https://www.findacode.com/loinc/102011-4--have-you-experienced-a-frightening-horrible-or-traumatic-event-pc-ptsd-5.html)
- **C-SSRS screener (recent):** panel **93373-9** (class PANEL.SURVEY.CSSRS). Items include 93246-7 (wish to be dead, 1 month), 93250-9 (plan/intent) and 93267-3/93269-9 (preparatory acts and 3-month timing). **93374-7** is the suicide risk level (low/moderate/high; answer list LL465-6). Copyright Dr. Kelly Posner, used with permission. — [LOINC 93373-9 panel](https://cdn.loinc.org/93373-9/panel); [LOINC 93374-7](https://cdn.loinc.org/93374-7)
- **AUDIT-C:** panel **72109-2**; total **75626-2** (0–12, {score}); items 75623-9, 75624-7 and 75625-4 (answer lists LL2179-1, LL2180-9, LL2181-7). Positive screen is ≥4 for men and ≥3 for women. **Conflict:** one source lists 75624-7 as an AUDIT-C item, while the full AUDIT panel (72110-0) labels 75624-7 as the full AUDIT total score. Verify on loinc.org. — [findacode 75626-2](https://www.findacode.com/loinc/75626-2--total-score-audit-c.html); [findacode 72109-2](https://www.findacode.com/loinc/72109-2--alcohol-use-disorder-identification-test-consumption-audit-c.html); [LOINC 72110-0](https://cdn.loinc.org/72110-0); [CASRAI AUDIT-C guide](https://casrai.org/guides/audit-c-score)
- **ASRS v1.1 (adult ADHD):** the 18-item ASRS v1.1 Symptom Checklist is represented by the PhenX panel **62750-5** ("attention deficit hyperactivity disorder symptoms protocol - adult"). Item codes fall in the 6523x–6524x range, e.g., 65240-4 and 65235-4. — [findacode 62750-5](https://www.findacode.com/loinc/62750-5--phenx-attention-deficit-hyperactivity-disorder-symptoms-protocol-adult-121501.html); [LOINC 65240-4](https://loinc.org/65240-4); [Wikipedia ASRS](https://en.wikipedia.org/wiki/Adult_ADHD_Self-Report_Scale)

### Inferences
- The server can implement deterministic pre-filters as FHIR searches (`Observation?patient=X&code=http://loinc.org|44261-6,...`) before invoking any LLM. This lowers cost and hallucination risk and makes the logic auditable as CQL or PlanDefinition (Q4).
- Many VA screens (PHQ-2/9, AUDIT-C, PC-PTSD-5, C-SSRS) are VistA/CPRS clinical reminders. Whether they surface as LOINC-coded Observations through VA APIs needs confirmation (see Q5 gaps).

### Gaps
- **Not verified this session:** GAD-7 LOINC codes (commonly cited as panel 69737-5, total 70274-6), PHQ-2 codes, the separate ASRS 6-item screener (Part A) panel code, adult autism screening instruments (e.g., AQ-10, RAADS-R), and whether LOINC codes exist for M-CHAT-R/F or adult autism tools.
- **Not verified this session:** ICD-10-CM codes for ADHD (F90.-), autism spectrum disorder (F84.0), PTSD (F43.1-), suicidal ideation (R45.851) and personal history of self-harm (Z91.51/Z91.52). Verify against the CDC/CMS FY2026/FY2027 ICD-10-CM tabular. SNOMED CT concept IDs, RxNorm classes (ATC N06BA psychostimulants) and VSAC value-set OIDs for mental health were not researched.

## Q4. Access patterns: SMART on FHIR, CDS Hooks, Bulk Data, Clinical Reasoning, RiskAssessment

### Takeaway
Three standard channels fit the server's three modes. **SMART App Launch 2.2** covers per-patient, clinician-context reads (user/ or patient/ granular scopes) and, through **Backend Services**, server-to-server access with `system/*.rs` scopes. **Bulk Data 2.0** `$export` (Group-level) covers population-level model training and evaluation. **CDS Hooks 2.0.1** delivers referral suggestions into the EHR workflow and, through its **Feedback API**, returns accept/override outcomes, which is the closing link in an LHS loop. Rule logic can be encoded as **CPG PlanDefinition + CQL**; `$apply` returns proposals, not actions.

### Cited Findings
- **SMART App Launch v2.2.0 (STU 2.2)** is the current published release on FHIR R4 and incorporates Backend Services, previously part of the Bulk Data IG. Backend clients request `system/` scopes such as `system/Observation.rs` (read + search). `system/*.cruds` means "full access" relative to the server's pre-configured client policy. A FHIR Jira ticket discusses renaming `system/` to `client/` scopes; its adoption is unconfirmed. — [SMART Backend Services](https://hl7.org/fhir/smart-app-launch/backend-services.html); [SMART scopes and launch context](https://hl7.org/fhir/smart-app-launch/scopes-and-launch-context.html); [FHIR-32186](https://jira.hl7.org/browse/FHIR-32186)
- SMART clinical scope grammar: `('patient'|'user') '/' (resource|'*') '.'` followed by permissions. Patient-specific scopes start with `patient/`. — [SMART scopes](https://hl7.org/fhir/smart-app-launch/STU2/scopes-and-launch-context.html)
- **Bulk Data Access IG 2.0:** export providers SHOULD use the SMART Backend Services authorization profile. Group-level export can cover groups with non-patient members. Oracle Health supports Group `$export` per Bulk Data v2.0.0, but client developers must coordinate with the healthcare organization to identify exportable groups. — [Bulk Data changes](https://www.hl7.org/fhir/uv/bulkdata/changes.html); [Bulk Data STU2 authorization](https://hl7.org/fhir/uv/bulkdata/STU2/authorization.html); [Oracle Bulk Data Access docs](https://docs.oracle.com/en/industries/health/health-ai-application-suite/aibda/bulk_data_access.html)
- **CDS Hooks:** the current published version is **v2.0.1 (STU2)** on FHIR R4, licensed CC-BY 4.0. Version 2.0 added system actions, a **Feedback** mechanism (formerly the "analytics endpoint") that carries **override reasons**, `isRecommended` and `topic` elements, prefetch pagination, and HTTPS for production FHIR servers. 2.0.1 added a required card `selectionBehavior`. Cards can be informational, offer accept/reject suggestions, or launch a SMART app. Example services include `patient-view` and `order-select` (with a MedicationRequest prefetch). A 3.0.0 ballot track exists. — [CDS Hooks home](https://cds-hooks.hl7.org/); [CDS Hooks 2.0](https://cds-hooks.hl7.org/2.0); [STU2 changes](https://cds-hooks.hl7.org/STU2/changes.html); [3.0 ballot build](https://build.fhir.org/ig/HL7/cds-hooks/en/)
- **Clinical Practice Guidelines (CPG) IG:** `PlanDefinition/$apply` (instance `[base]/PlanDefinition/[id]/$apply` or type-level with `url`) maps input parameters to CQL. Its result "effectively represents a proposed set of activities," returned as a Bundle or RequestGroup of proposed diagnoses, data-collection tasks or orders, and it is up to the caller whether to carry them out. CQL is a superset of FHIRPath. IHE Computable Care Guidelines builds on this, with a Guideline Performer submitting `$apply` to a Guideline Engine. — [CPG PlanDefinition $apply (STU2)](https://hl7.org/fhir/uv/cpg/STU2/OperationDefinition-cpg-plandefinition-apply.html); [CPG methodology](https://www.hl7.org/fhir/uv/cpg/methodology.html); [IHE CCG](https://profiles.ihe.net/QRPH/CCG/CCG_v3_launch.html)

### Inferences
- **Architecture options:**
  - (a) *Interactive:* clinician uses an MCP-enabled assistant → MCP server → SMART (user-context token, granular `user/Observation.rs` etc.) → FHIR.
  - (b) *Workflow-embedded:* a CDS Hooks `patient-view` service internally calls the same analysis logic and returns a card with a "Propose referral" suggestion (ServiceRequest, intent = proposal). The Feedback API records accept/override reasons.
  - (c) *Population/LHS:* SMART Backend Services + Bulk `$export` to a research enclave for training and evaluation.
- Deterministic eligibility rules (e.g., PHQ-9 ≥10 with no MH encounter in 12 months, positive ASRS Part A, C-SSRS risk level) are better expressed in CQL/PlanDefinition than in prompts. The LLM is then reserved for unstructured notes (DocumentReference) and explanation generation.
- MCP's own OAuth layer and SMART are separate: the MCP server is a resource server to the MCP client and simultaneously a SMART client to the FHIR server. Token exchange, not passthrough, is required (Q1).

### Gaps
- Exact scope requirements for `Group/[id]/$export` were not retrieved.
- The full patient-view and order-select hook context definitions and the Feedback API payload schema were not retrieved.
- I found no source describing a standard CPG/CQL pattern for emitting RiskAssessment from ML models.

## Q5. VA specifics: Lighthouse APIs, Oracle Health Federal EHR, VistA/CDW/OMOP, 42 CFR Part 2, 38 U.S.C. 7332

### Takeaway
VA exposes FHIR R4 (4.0.1) through Lighthouse: the **Patient Health API** (veteran-authorized, base `https://api.va.gov/services/fhir/v0/r4`) and the **Clinical Health API (CHAPI)** for providers (v2.4.0 CapabilityStatement, Mar 2026). VA's EHR is split. Most sites still run VistA/CPRS. The Oracle Health Federal EHR went live at 4 Michigan sites on 11 Apr 2026 after a 3-year pause, with 13 sites planned for 2026 and 26 more planned for FY2027. Research data sits in the CDW, with an OMOP instance through VINCI. Records about drug or alcohol abuse, HIV and sickle cell anemia are protected by **38 U.S.C. 7332** (special written consent). The **42 CFR Part 2** final rule's compliance date was **16 Feb 2026**.

### Cited Findings
- **Patient Health API (FHIR R4):** lets Veterans and authorized third parties access health data using FHIR R4. Base URL `https://api.va.gov/services/fhir/v0/r4`; FHIR 4.0.1. The PHAPI v2.0.0 CapabilityStatement was drafted Dec 2025 (Organization and Practitioner among listed resources; full list not retrieved). An aggregator states that Lighthouse OAuth supports PKCE and SMART scopes (`patient/*`, `user/*`, `system/*`). This is unverified against developer.va.gov. — [VA FHIR Map Set IG – PHAPI CapabilityStatement](https://department-of-veterans-affairs.github.io/va-fhir-cop-mapset-ig/CapabilityStatement-PHAPI.html); [apis.io VA scopes (aggregator)](https://apis.io/scopes/va-gov/va-gov-scopes/)
- **Clinical Health API (CHAPI):** the v1.6.49 CapabilityStatement (mid-2025) lists FHIR 4.0.1, JSON/XML, and resources including AllergyIntolerance, Patient, Appointment, Specimen, Encounter (outpatient profile), Condition, Location and MedicationDispense. A newer **v2.4.0 (Mar 2026)** CapabilityStatement exists; its full resource list was not confirmed. — [CHAPI CapabilityStatement (VA map-set IG)](https://department-of-veterans-affairs.github.io/va-fhir-cop-mapset-ig/CapabilityStatement-CHAPI.html); [mirror](https://j-p-systems.github.io/va.maps/CapabilityStatement-CHAPI.html)
- A separate VA IG maps My HealtheVet PHR data to FHIR. This is distinct from PHAPI. — [MHV FHIR PHR mapping IG](https://build.fhir.org/ig/department-of-veterans-affairs/mhv-fhir-phr-mapping/background.html)
- **Federal EHR (Oracle Health):** VA paused deployments in April 2023. On **11 April 2026** it deployed at **VA Ann Arbor, Battle Creek, Detroit and Saginaw** (Michigan), the first of **13 planned 2026 deployments**. Four Ohio and Kentucky medical centers were scheduled for **June 2026**. A VA budget document plans **26 additional sites in FY2027**. — [Nextgov (Apr 2026)](https://www.nextgov.com/modernization/2026/04/va-resumes-ehr-rollouts-four-michigan-medical-sites/412807/); [Military Times (2026-04-10)](https://www.militarytimes.com/news/pentagon-congress/2026/04/10/after-three-year-hiatus-va-to-resume-rollout-of-new-electronic-medical-records-system/); [VA Battle Creek news](https://www.va.gov/battle-creek-health-care/stories/history-is-made-as-michigan-sites-go-live-with-ehr/); [VA Chillicothe: 9 sites in 2026](https://www.va.gov/chillicothe-health-care/stories/9-sites-going-live-with-new-electronic-health-record-in-2026/); [Healthcare Dive](https://www.healthcaredive.com/news/veterans-affairs-va-medical-centers-michigan-oracle-ehr/817470/)
- Earlier VA announcements (Mar 2025) named 9 sites for 2026, and later reporting cites 13. Treat the count as evolving. — [VA Philadelphia news release](https://www.va.gov/philadelphia-health-care/news-releases/va-to-complete-federal-ehr-deployment-at-nine-additional-sites-in-2026/); [MeriTalk (13 sites)](https://meritalk.com/articles/va-plans-to-roll-out-ehr-system-to-13-sites-in-2026/)
- **Oracle Health FHIR** supports Bulk Data Group `$export` (v2.0.0). — [Oracle docs](https://docs.oracle.com/en/industries/health/health-ai-application-suite/aibda/bulk_data_access.html)
- **CDW and OMOP:** VINCI began transforming the VA Corporate Data Warehouse into the OMOP CDM in 2015 and released the first version to VA researchers in July 2017, with incremental ETL refreshes. VA OMOP v5.2 covered a large portion of CDW (enrollment data was not yet included as of 2019). VINCI offers a synthetic-data OMOP sandbox. — [Characterization paper (PMC6811349)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6811349); [OHDSI 2021 abstract](https://www.ohdsi.org/wp-content/uploads/2021/09/24-abstract-Viernes.pdf); [IOS Press SHTI190561](https://ebooks.iospress.nl/pdf/doi/10.3233/SHTI190561)
- **38 U.S.C. 7332:** VA records identifying a patient that relate to **drug abuse, alcoholism or alcohol abuse, HIV infection, or sickle cell anemia** are confidential. Disclosure generally requires written consent with specific elements (VA Form 10-5345 may be used; 38 CFR 1.475), and the statute restricts redisclosure by recipients. A proposed rule would allow release to HIE partners based on the partner's attestation of consent; its finalization was not confirmed. — [38 U.S.C. 7332 (Cornell LII)](https://www.law.cornell.edu/uscode/text/38/7332); [38 CFR 1.511](https://www.law.cornell.edu/cfr/text/38/1.511); [Network for Public Health Law snapshot](https://www.networkforphl.org/wp-content/uploads/2019/01/Snapshot-VA-Confidentiality-of-Sensitive-Records.pdf)
- **42 CFR Part 2 final rule (Feb 2024):** compliance date **16 Feb 2026**. OCR enforces it under the HIPAA civil-penalty framework. HIPAA Breach Notification now applies to Part 2 records. Notices of Privacy Practices must be updated. Business associates are added to the Qualified Service Organization definition. — [HHS Part 2 fact sheet](https://www.hhs.gov/hipaa/for-professionals/regulatory-initiatives/fact-sheet-42-cfr-part-2-final-rule/); [HIPAA Journal](https://www.hipaajournal.com/february-16-2026-compliance-deadline-part-2-final-rule/); [Mintz (2026-03-02)](https://www.mintz.com/insights-center/viewpoints/2146/2026-03-02-ensuring-compliance-part-2-final-rule-required-updates)
- **REACH VET** (VA operational precedent for EHR-based MH risk models):
  - Flags the top 0.1% of predicted suicide risk monthly to facility coordinators via a dashboard. GAO describes 61 EHR variables.
  - **REACH VET 2.0** was redeveloped on more than 7 million Veterans and adds risk factors including military sexual trauma and intimate partner violence.
  - By Oct 2020, 98% of identified Veterans (N=6,579) had been contacted.
  - The top tier accounts for only about 2.8% of VHA patient suicides.

  — [Nextgov (Jul 2025)](https://www.nextgov.com/artificial-intelligence/2025/07/inside-vas-yearslong-ai-effort-uncover-veterans-high-risk-suicide/406781/); [Psychiatric Services REACH VET paper](https://ps.psychiatryonline.org/doi/abs/10.1176/appi.ps.202100629); [JAMA Netw Open evaluation (PMC8524305)](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC8524305/); [GAO-22 report](https://www.gao.gov/assets/730/722660.pdf)
- **VA AI governance:**
  - VA adopted a **Trustworthy AI Framework** in July 2023 with six principles: purposeful; effective and safe; secure and private; fair and equitable; transparent and explainable; accountable and monitored.
  - VA's AI use-case inventory listed **367 use cases as of Jan 2026 (253 in VHA; 68% high-impact)**. High-impact deployed use cases are continuously monitored, and non-compliant ones are discontinued.
  - The VA-wide AI Strategy dates from July 2021. VA OIG's AI compliance plan follows OMB M-25-21.

  — [MeriTalk](https://meritalk.com/articles/va-launches-new-trustworthy-ai-framework/); [Military Times (2026-06-23)](https://www.militarytimes.com/veterans/2026/06/23/va-inventory-report-reveals-367-ai-systems-operating-in-healthcare-benefits-and-services/); [GAO-25-108739](https://www.gao.gov/products/GAO-25-108739); [VA OIG AI Compliance Plan 2025](https://www.vaoig.gov/sites/default/files/document/2025-09/VA%20OIG%20AI%20Compliance%20Plan%202025.pdf)

### Inferences
- During the 2026–2028 transition, an MCP server for VA must handle two back ends: Lighthouse CHAPI/VistA-derived FHIR for VistA sites and Oracle Health Millennium FHIR for Federal EHR sites. A FHIR abstraction layer is therefore a practical requirement.
- SUD diagnoses, AUDIT-C-driven alcohol data, HIV and sickle cell data fall under 7332, and possibly Part 2 for SUD program records. The server needs data-segmentation logic: filtering by FHIR `meta.security` labels or by codes. It must also never echo protected content into LLM prompts or logs sent outside the authorized boundary without the required consent or legal basis.
- REACH VET shows VA already runs an EHR-model → coordinator-outreach loop. An MCP referral recommender for ADHD, autism or other MH screening could reuse that governance pattern (dashboards, coordinator review, monthly evaluation) instead of autonomous action.

### Gaps
- developer.va.gov could not be read, so the authoritative PHAPI and CHAPI resource lists, SMART scope names, and whether screening scores (PHQ-9, AUDIT-C, C-SSRS) are exposed as LOINC Observations were not confirmed.
- Whether the June 2026 Ohio and Kentucky go-lives occurred on schedule, and the status of the remaining 2026 sites, were not confirmed.
- How VA tags 7332 data in FHIR (security labels / DS4P) was not found. The status of the 7332 HIE-attestation proposed rule is unknown.
- Current (2025–2026) VA OMOP release details and access procedures were not found.
- No primary VA source for the Trustworthy AI Framework text was retrieved (secondary coverage only).

## Q6. Existing FHIR/healthcare MCP servers and LLM-on-FHIR research

### Takeaway
Several open-source FHIR MCP servers exist. WSO2's is the most mature: Apache-2.0, generic CRUD and search tools, and SMART OAuth. Medplum ships MCP natively, and AWS offers a HealthLake MCP server. As of Oct 2026 neither Epic nor Oracle Health had published an official MCP server for third parties. Benchmarks show frontier LLM agents at roughly 64–70% task success on a FHIR EHR sandbox (MedAgentBench). Agents struggle with FHIR's graph structure (FHIR-AgentBench) and fail in 32–68% of tool-fault-injected episodes (MedToolFault). A 2026 scoping review found no prospective clinical validation of MCP or A2A healthcare systems.

### Cited Findings
**Servers**
- **WSO2 fhir-mcp-server** (Python, Apache 2.0):
  - Tools: `get_capabilities`, `search` (with FHIRPath filtering), `read` (supports operations such as `$everything`), `create`, `update`, `delete`, `get_user`.
  - Auth: SMART-on-FHIR OAuth 2.0 Authorization Code flow, enabled by default; it can be disabled for public servers. A static token option is meant only for local stdio.
  - Transports: stdio, SSE, Streamable HTTP (default).
  - Demonstrated against the Epic sandbox and public HAPI.
  - `get_user` requires the `openid` and `fhirUser` scopes.
  - Local Docker currently requires disabling authorization.

  — [WSO2 README](https://raw.githubusercontent.com/wso2/fhir-mcp-server/HEAD/README.md); [PyPI](https://pypi.org/project/fhir-mcp-server/)
- **fhirHydrant** (Node.js): SMART Backend Services, metadata-aware search and CRUD, and **audit events**. **healsens-fhirmcp**: conformance-aware, R4/R5. **npm fhir-mcp-server**: no-auth or static bearer token. — [mcpservers.org fhirHydrant](https://mcpservers.org/servers/faulkj/fhirhydrant); [healsens](https://mcpservers.org/hi/servers/healsens/healsens-fhirmcp); [socket.dev](https://socket.dev/npm/package/fhir-mcp-server)
- **Medplum:** the standalone MCP proxy is archived, and MCP now ships inside the Medplum server. Community options include `pymedplum[mcp]` and `@ncodeuy/medplum-mcp`. — [Medplum MCP docs](https://www.medplum.com/docs/ai/mcp); [pymedplum MCP](https://pymedplum.readthedocs.io/en/latest/mcp/)
- **AWS HealthLake MCP server** (open source): natural-language CRUD and search over HealthLake FHIR. — [AWS for Industries blog](https://aws.amazon.com/blogs/industries/building-healthcare-ai-agents-with-open-source-aws-healthlake-mcp-server)
- Other listed servers: "the-momentum fhir-mcp-server" ([LobeHub listing](https://lobehub.com/ja/mcp/the-momentum-fhir-mcp-server)); LangCare (open source, Epic and Oracle via FHIR R4); CharmHealth's MCP server (launched Feb 2026). — [fast.io roundup](https://fast.io/resources/best-mcp-servers-for-healthcare/); [HIT Consultant (2026-02-19)](https://hitconsultant.net/2026/02/19/charmhealth-mcp-server-model-context-protocol-ai-ehr-integration/)
- **Epic / Oracle:** a vendor connector page reports no official Epic MCP server for third-party agents as of 20 Oct 2026 (Epic documents Epic on FHIR and open.epic instead). At HIMSS26 Epic previewed "Factory" for building and orchestrating its own AI agents. Oracle Health has published no MCP server of its own and documents Millennium FHIR R4; Oracle emphasized agentic AI at its Sept 2026 summit. These claims rely partly on vendor sources. — [ibl.ai Epic connector](https://ibl.ai/developer/connectors/epic); [ibl.ai Oracle Health connector](https://ibl.ai/developer/connectors/oracle-health-cerner); [Scalekit](https://www.scalekit.com/blog/ehr-integration-ai-agents-epic-cerner-fhir); [Fierce Healthcare HIMSS26](https://www.fiercehealthcare.com/ai-and-machine-learning/himss26-epic-expands-ai-roadmap-previews-factory-build-and-orchestrate-ai); [Healthcare IT Today (2026-09-24)](https://www.healthcareittoday.com/2026/09/24/inside-oracles-playbook-what-the-health-and-life-sciences-summit-means-for-healthcare-leaders/)

**Research**
- **MedAgentBench** (Jiang et al., Stanford; NEJM AI per Stanford HAI): a FHIR-compliant interactive virtual EHR. v2 has **300 physician-written, patient-specific tasks in 10 categories** and evaluated 12 models. The best was **Claude 3.5 Sonnet v2 at 69.67%**, ahead of GPT-4o at 64.00%; performance varied widely by task category. (v1 had 100 tasks, with GPT-4o best at 72%; cite v2.) The authors conclude agents are not yet reliable enough for high-dependability use. — [arXiv 2501.14654v2](https://arxiv.org/abs/2501.14654v2); [Stanford HAI](https://hai.stanford.edu/news/stanford-develops-real-world-benchmarks-for-healthcare-ai-agents)
- **FHIR-AgentBench** (Lee et al., KAIST/Verily/MIT; PMLR v297, 2026): **2,931** clinician-sourced EHRSQL questions grounded in **MIMIC-IV-FHIR**. Agents must retrieve the relevant FHIR resources and answer; an LLM judge (o4-mini) scores answers. Models tested: o4-mini, Gemini-2.5-flash, Qwen-3, LLaMA-3.3. Retrieval over intricate FHIR resources and reasoning over them both critically limit performance, and agents struggle with FHIR's graph-like structure. — [arXiv 2509.19319](https://arxiv.org/abs/2509.19319v2); [PMLR v297 lee26a](https://proceedings.mlr.press/v297/lee26a.html); [Verily blog (2025-12-18)](https://verily.com/perspectives/introducing-fhir-agentbench)
- **LLM on FHIR** (Schmiedmayer et al., Stanford BDHG): an open-source iOS app built on Stanford Spezi (MIT license) in which GPT-4 answers patient questions over SMART-retrieved health records. A SyntheticMass pilot found generally high accuracy and relevance with variability. A peer-reviewed version is PMC12144420 / PMID 40373519. — [arXiv 2402.01711](https://arxiv.org/abs/2402.01711); [PMC12144420](https://pmc.ncbi.nlm.nih.gov/articles/PMC12144420); [GitHub LLMonFHIR](https://github.com/StanfordBDHG/LLMonFHIR)
- **MCP-FHIR framework** (Ehtesham, Singh, Kumar; arXiv 2506.13800, Jun 2025): LLM agents get declarative, JSON-config-driven access to FHIR resources through MCP, tested on SMART Health IT sandbox synthetic data. — [arXiv 2506.13800](https://arxiv.org/abs/2506.13800)
- **EHR-MCP** (Masayoshi et al.; arXiv 2509.15957, Sep 2025): GPT-4.1 in a LangGraph ReAct agent with MCP tools on a **real hospital EHR**. Near-perfect on simple retrieval tasks, with weaker performance on complex ones. Errors came mostly from wrong tool arguments or misread tool output. — [arXiv 2509.15957](https://arxiv.org/abs/2509.15957v1)
- **Scoping review of MCP and A2A in healthcare** (Haider et al., JMIR preprint, Feb 2026): 13 studies were included; **none reported prospective clinical validation with real patients**. Gaps include agent identity verification and health equity. — [JMIR Preprints 93344](https://preprints.jmir.org/preprint/93344/submitted)
- **MedToolFault / MedGuard** (arXiv 2611.09942, Nov 2026): fault injection across 6 tool-failure classes and more than 127,000 episodes on 9 model configurations. Unguarded agents failed in **32.2–67.8%** of fault-injected runs on tasks they otherwise solve. A tool-layer guard that verifies read evidence and attributes ambiguous writes improved safe success by **13.7–46.6 pp**. — [arXiv 2611.09942](https://arxiv.org/pdf/2611.09942)

### Inferences
- A generic CRUD FHIR MCP server (WSO2-style) is the wrong surface for clinical screening. Exposing `create`, `update` and `delete` to an LLM invites the "forbidden mutation" failures MedToolFault measures. A purpose-built, **read-only, task-specific tool set** is safer. Examples: `get_screening_history`, `get_mh_problem_list`, `get_stimulant_med_history`, `search_notes_for_concepts`, `propose_referral`. Pair it with server-side validation of retrieved evidence.
- The benchmark error modes (wrong tool arguments, FHIR graph navigation) argue for the server doing the FHIR joins and flattening itself, e.g., returning a pre-assembled "MH screening summary" resource, rather than making the LLM navigate references.

### Gaps
- Per-model FHIR-AgentBench accuracy numbers could not be retrieved (arxiv.org and verily.com were blocked).
- No information was found on a Flexpa MCP server or a HAPI-specific MCP module. The NEJM AI DOI and date for MedAgentBench were not confirmed.
- No published evaluation of an LLM or MCP system specifically for ADHD or autism referral recommendation from EHR data was found in this search.

## Q7. Regulatory: FDA CDS and AI guidance, PCCP, ONC HTI-1/HTI-5, Section 1557, HIPAA/Part 2

### Takeaway
A referral-recommendation tool aimed at clinicians can potentially be **non-device CDS** if it meets all four §520(o)(1)(E) criteria:
1. It does not analyze images or signals.
2. It displays or analyzes medical information.
3. It supports, rather than replaces, HCP decisions.
4. The HCP can independently review the basis.

FDA revised the CDS guidance in **January 2026**, issued 6 Jan and reissued 29 Jan, with somewhat looser treatment of single recommendations. If the tool becomes a device, FDA's PCCP guidance (final Dec 2024) and the AI lifecycle draft (Jan 2025) govern model updates. ONC's HTI-1 DSI "source attributes" (31 for predictive DSIs) are proposed for removal under HTI-5 (Dec 2025). HHS 45 CFR 92.210 required covered entities to identify and mitigate discrimination risk in patient-care decision support tools from 1 May 2025, though enforcement posture is uncertain.

### Cited Findings
- **FDA CDS guidance (2026):** FDA issued a revised final CDS Software guidance on **6 Jan 2026**. The FDA page lists a version issued **29 Jan 2026** that supersedes it, issued without a comment period. It remains limited to HCP-facing CDS. Changes: certain "singular recommendations" may fall under enforcement discretion, and the time-critical consideration was removed from Criterion 3 but remains relevant to Criterion 4. Commentators note the guidance is silent on AI specifically, as was the 2022 version. — [FDA CDS guidance page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/clinical-decision-support-software); [Covington (Jan 2026)](https://www.cov.com/en/news-and-insights/insights/2026/01/5-key-takeaways-from-fdas-revised-clinical-decision-support-cds-software-guidance); [Cooley (2026-01-20)](https://www.cooley.com/news/insight/2026/2026-01-20-automation-bias-and-clinical-practice-fda-makes-incremental-updates-to-clinical-decision-support-software-guidance); [DLA Piper](https://www.dlapiper.com/en-es/insights/publications/2026/01/fda-updates-its-clinical-decision-support-and-general-wellness-guidances-key-points); [FDA Law Blog](https://www.thefdalawblog.com/2026/01/a-busy-day-in-the-cdrh-neighborhood-updates-to-the-cds-and-general-wellness-guidance-documents/)
- **The four non-device CDS criteria** (all must be met):
  1. Does not acquire, process or analyze a medical image, IVD signal, or pattern or signal from a signal acquisition system.
  2. Displays, analyzes or prints medical information, such as peer-reviewed studies or guidelines.
  3. Supports or provides recommendations to an HCP about prevention, diagnosis or treatment.
  4. Enables the HCP to independently review the basis, so the HCP does not rely primarily on the recommendation.

  Numbering differs between FDA slides and the statute. — [FDA CDS guidance PDF](https://www.fda.gov/media/109618/download); [FDA "Your CDS software: is it a device?"](https://www.fda.gov/medical-devices/software-medical-device-samd/your-clinical-decision-support-software-it-medical-device); [FDA CDS FAQs](https://www.fda.gov/medical-devices/software-medical-device-samd/clinical-decision-support-software-frequently-asked-questions-faqs)
- **PCCP:** the final guidance "Marketing Submission Recommendations for a Predetermined Change Control Plan for AI-Enabled Device Software Functions" was announced 4 Dec 2024 (FR Vol 89 No 233). FDA's page shows an August 2025 date, possibly a revision. The guidance renamed "ML-enabled" to "AI-enabled." — [FDA PCCP guidance page](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/marketing-submission-recommendations-predetermined-change-control-plan-artificial); [Federal Register 2024-28361](https://www.govinfo.gov/content/pkg/FR-2024-12-04/html/2024-28361.htm)
- **AI lifecycle draft:** "Artificial Intelligence-Enabled Device Software Functions: Lifecycle Management and Marketing Submission Recommendations," draft published 7 Jan 2025 (Docket FDA-2024-D-4488). No finalization was found. — [FDA guidance page](https://fda.gov/regulatory-information/search-fda-guidance-documents/artificial-intelligence-enabled-device-software-functions-lifecycle-management-and-marketing); [Federal Register 2024-31543](https://www.govinfo.gov/content/pkg/FR-2025-01-07/html/2024-31543.htm)
- **ONC HTI-1 DSI (45 CFR 170.315(b)(11)):** distinguishes evidence-based DSIs (rules-based) from predictive DSIs (learned from data). Certified modules must support **13 source attributes for evidence-based and 31 for predictive DSIs**, plus intervention risk management. Developers had until 31 Dec 2024. Source-attribute obligations apply to DSIs the developer supplies, but users must be able to record attributes for self-developed or third-party predictive DSIs. — [ONC DSI Criterion Resource Guide (May 2024)](https://www.healthit.gov/sites/default/files/page/2024-05/DSI-Criterion-Resource-Guide_508.pdf); [HIMSS HTI-1 DSI fact sheet](https://www.himss.org/sites/hde/files/2024-01/hti-1-final-rule-fact-sheet-decision-support-interventions.pdf); [Mintz](https://mintz.com/insights-center/viewpoints/2146/2024-01-08-hhs-onc-hti-1-final-rule-introduces-new-transparency)
- **HTI-5 proposed rule** (ASTP/ONC "Deregulatory Actions to Unleash Prosperity"): published in the Federal Register on **29 Dec 2025**, with comments closing **27 Feb 2026**. It proposes removing 34 and revising 7 of 60 certification criteria. The DSI criterion would be **revised** to "fully remove the AI 'model card' requirements," i.e., the source attributes. Final rule status was not found. — [HTI-5 proposed rule page](https://healthit.gov/HTI5); [HTI-5 chart](https://healthit.gov/resources/hti-5-proposed-rule-chart/); [HTI-5 overview PDF](https://healthit.gov/wp-content/uploads/2026/02/HTI-5-Proposed-Rule-Overview.pdf); [Holland & Knight (2026-01-07)](https://www.hklaw.com/en/insights/publications/2026/01/astp-oncs-year-end-moves-mark-a-strategic-pivot)
- **Section 1557, 45 CFR 92.210:** covered entities must not discriminate through "patient care decision support tools," automated or not, including those used for **screening and risk prediction**. They must make **reasonable efforts to identify and mitigate** discrimination risk, with **compliance required by 1 May 2025**. OCR issued a Dear Colleague letter on 10 Jan 2025. Commentators note uncertainty about HHS enforcement after the policy changes and reorganization. — [Final rule, FR 2024-08711](https://www.govinfo.gov/content/pkg/FR-2024-05-06/pdf/2024-08711.pdf); [OCR Dear Colleague letter](https://hhs.gov/sites/default/files/ocr-dcl-section-1557-artificial-intelligence.pdf); [Health Affairs Forefront](https://www.healthaffairs.org/content/forefront/section-1557-rule-mandates-identification-and-mitigation-discriminatory-clinical); [Manatt](https://www.manatt.com/insights/newsletters/health-highlights/hhs-finalizes-antidiscrimination-rules-on-patient)
- **42 CFR Part 2** (compliance 16 Feb 2026) and **38 U.S.C. 7332**: see Q5.

### Inferences
- To stay within non-device CDS, the server should present the **evidence** behind each recommendation: the specific Observations, scores, dates, note excerpts and the guideline rule. This satisfies the "independently review the basis" criterion. The server should target HCPs, not patients, and frame output as "consider referral for screening," not a diagnosis. LLM-generated risk scores from unstructured notes, where the basis is opaque, push toward device status.
- Even if HTI-5 removes certification-side source attributes, documenting the 31 predictive-DSI attributes plus an AI-Transparency-on-FHIR model card is low-cost good practice. It supports VA Trustworthy AI ("transparent and explainable") and 1557 bias mitigation.
- VA is not an HHS-regulated covered entity in the same way for every rule. Whether 45 CFR 92.210 and HTI rules bind VA itself, versus vendors and community-care partners, needs legal review. VA's own Trustworthy AI framework and OMB M-25-21 apply directly.

### Gaps
- The full 2026 CDS guidance text and its examples (e.g., whether a "refer for psychiatric evaluation" recommendation is cited) were not read; the FDA PDF was not fetched.
- The HTI-5 final rule status as of Nov 2026 is unknown.
- Whether HHS has amended, paused or enforced 92.210 since May 2025 is unconfirmed.
- The applicability of 1557 and HTI to VA as a federal provider was not researched.

## Q8 (Objective e). How an MCP server could serve the Learning Health System cycle (data → knowledge → practice → data), including logging, provenance, evaluation and model versioning

### Takeaway
VA frames its LHS as a three-phase cycle adapted from Friedman et al.: data to knowledge, knowledge to performance, performance to data. QUERI operationalizes it. A FHIR MCP server can instrument each phase:
- **Data:** SMART, Bulk FHIR and OMOP.
- **Knowledge:** versioned CQL/PlanDefinition rules plus models with model cards.
- **Practice:** CDS Hooks cards and MCP tools that return evidence-linked RiskAssessments and proposed ServiceRequests.
- **Back to data:** CDS Hooks feedback, accept/override reasons, Provenance and AuditEvent, OpenTelemetry traces, and downstream referral completion.

Model updates would be governed by a PCCP-style change plan.

### Cited Findings
- VA's LHS framework is "a progressive, three-phase approach (data to knowledge, knowledge to performance, performance to data) that aligns people, processes, technologies, and policies," adapted from Friedman et al. QUERI (est. 1998) was created to speed translation of research into VHA practice and later became a vehicle for the National Academy of Medicine LHS model of continuous learning cycles. — [VA LHS / QUERI articles (PMC8332471)](https://pmc.ncbi.nlm.nih.gov/articles/PMC8332471); [PMC5472006](https://pmc.ncbi.nlm.nih.gov/articles/PMC5472006); [PMC9108213](https://pmc.ncbi.nlm.nih.gov/articles/PMC9108213). The exact attribution of each quote to a specific PMC article was not verified because the search tool aggregated them.
- MCP 2026-07-28 provides **OpenTelemetry trace-context propagation in `_meta`** (SEP-414), **`server/discover`** returning server identity, versions and capabilities, **deterministic `tools/list` ordering**, and **cacheable results** with `ttlMs` and `cacheScope`. — [2026-07-28 changelog](https://raw.githubusercontent.com/modelcontextprotocol/modelcontextprotocol/main/docs/specification/2026-07-28/changelog.mdx)
- MCP **Tasks** (extension `io.modelcontextprotocol/tasks`) support long-running, pollable operations through `tasks/get` and `tasks/update`, which suits Bulk `$export` or cohort analyses. — [MCP blog (2026-07-28)](https://blog.modelcontextprotocol.io/posts/2026-07-28/)
- CDS Hooks 2.0 **Feedback** lets services learn the outcomes of their recommendations, including **override reasons**. — [CDS Hooks STU2 changes](https://cds-hooks.hl7.org/STU2/changes.html)
- AI Transparency on FHIR: an AIAST `meta.security` label on every AI-influenced resource; Provenance with the model (Device), inputs (prompt) and human verifier; a Model-Card DocumentReference. — [AI Transparency on FHIR](https://hl7.org/fhir/uv/aitransparency/2026Jan/index.html)
- The HTI-1 predictive DSI source attributes (31) and intervention risk management give a structured model-card and monitoring checklist. — [ONC DSI Resource Guide](https://www.healthit.gov/sites/default/files/page/2024-05/DSI-Criterion-Resource-Guide_508.pdf)
- FDA PCCP guidance provides a framework for pre-specifying permissible AI model modifications and their validation. — [FDA PCCP guidance](https://www.fda.gov/regulatory-information/search-fda-guidance-documents/marketing-submission-recommendations-predetermined-change-control-plan-artificial)
- fhirHydrant shows that an MCP FHIR server can emit **audit events** natively. — [mcpservers.org fhirHydrant](https://mcpservers.org/servers/faulkj/fhirhydrant)
- REACH VET is a VA precedent for an operational EHR model with coordinator workflow and periodic re-development (v2.0 on more than 7M Veterans). — [Nextgov (Jul 2025)](https://www.nextgov.com/artificial-intelligence/2025/07/inside-vas-yearslong-ai-effort-uncover-veterans-high-risk-suicide/406781/)
- VA requires continuous monitoring of deployed high-impact AI use cases, and use cases that cannot comply are discontinued. — [Military Times (2026-06-23)](https://www.militarytimes.com/veterans/2026/06/23/va-inventory-report-reveals-367-ai-systems-operating-in-healthcare-benefits-and-services/)

### Inferences
These are design proposals synthesized from the findings above, not sourced facts.
- **Data → Knowledge:**
  - SMART Backend Services + Bulk `$export` (Oracle sites) and CDW/OMOP (VistA history) build retrospective cohorts: Veterans later diagnosed with ADHD, ASD, PTSD or depression versus controls.
  - Train and validate rules and models in VINCI.
  - Publish logic as versioned FHIR `Library` (CQL) + `PlanDefinition` (`version`, `url`) and models as `Device` + Model-Card `DocumentReference`.
- **Knowledge → Practice:**
  - The MCP server exposes read-only, task-specific tools and returns `structuredContent` that conforms to an `outputSchema`. The output mirrors FHIR `RiskAssessment` (prediction, basis, method = model/rule version) and a proposed `ServiceRequest`.
  - The same engine backs a CDS Hooks `patient-view` service for in-EHR delivery.
  - Clinicians, not the agent, finalize orders.
- **Practice → Data:** log every invocation with:
  - MCP request ID and OTel trace ID
  - `server/discover` server version, tool name, rule/model version
  - input resource IDs and versionIds (FHIR `meta.versionId`)
  - prompt template hash and LLM model ID
  - output RiskAssessment ID
  - clinician action (CDS Hooks feedback: accepted or overridden, with reason)
  - downstream outcomes (ServiceRequest status, screening completed, diagnosis made)

  Store these as FHIR `AuditEvent` + `Provenance` (AI-Transparency profile) in a research store. Use them for monthly performance, calibration and fairness (1557) dashboards. Feed them into PCCP-governed retraining.
- **Evaluation design:** stepped-wedge or cluster-randomized rollout across VA sites, consistent with QUERI implementation-science methods. The staggered Federal EHR deployments (Michigan in Apr 2026, later waves) could serve as natural experiment strata. This is a speculative design idea.
- **Privacy in logs:** logs must themselves honor 7332 and Part 2. Store resource references and hashes rather than raw sensitive content, and keep LLM prompts containing protected content inside the VA boundary.

### Gaps
- No published example was found of an MCP server being used inside a formal LHS or QUERI program, or of CDS Hooks feedback data used for model retraining at VA.
- Friedman et al.'s original LHS definition text was not retrieved directly.
- No VA-specific policy on logging LLM prompts and outputs (retention, PHI handling) was found.
