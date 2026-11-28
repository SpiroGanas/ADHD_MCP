# Hand-off documents

Word documents for the people who will take ADHD_MCP from development to production: developers, clinicians, and security, privacy and regulatory reviewers. Written 2026-11-28 for server 0.9.0, tool contract 0.5.0, ADHD ruleset 1.0.0 (draft).

| Document | For | Contents |
|---|---|---|
| [ADHD_MCP_Human_Review_Checklist.docx](ADHD_MCP_Human_Review_Checklist.docx) | Everyone who must review or sign off | About 130 items that need a person, grouped by reviewer (project owner, physician, suicide prevention lead, psychologist, nurse, pharmacist, coder, informaticist, software engineer, security engineer, privacy officer, counsel, data scientist, operations), each with where to look and when it is needed, plus a sign-off table |
| [ADHD_MCP_User_Guide.docx](ADHD_MCP_User_Guide.docx) | Clinicians, reviewers, informaticists and engineers | Intended use and safeguards, how an assessment works, installation, client set-up, configuration, every tool, how to read every part of a result, worked examples on the synthetic personas, deployment, troubleshooting, limitations and maintaining clinical content |
| [ADHD_MCP_Clinician_Quick_Start.docx](ADHD_MCP_Clinician_Quick_Start.docx) | Clinicians using the tool through an AI assistant | Three pages: what to ask, the order to read a result, what each safety gate status and recommendation means, what to keep in mind, and do's and don'ts. No installation or troubleshooting |

The documents summarize the repository as of the date above; the Markdown sources they draw on stay authoritative: [status.md](../../status.md), [peer_review_01.md](../../peer_review_01.md), the [rule cards](../clinical/rule_card_adhd_1.0.md), the [deployment guide](../guide/deployment.md), the [configuration guide](../guide/configuration.md), the [tool reference](../reference/tools.md) and the [limitations](../limitations.md). When those change in a way a reader of these documents would act on, edit the documents in Word to match.

The worked examples in the User Guide were produced by running version 0.9.0 on the synthetic personas in `tests/personas/bundles/` with `as_of` 2026-06-15. No real patient data appears in any of them.

The Clinician Quick Start Guide ends with a placeholder for the site's support contact, which the deploying organization fills in (checklist item RN-08).
