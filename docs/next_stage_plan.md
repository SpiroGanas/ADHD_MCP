# Next-stage proposal

Phase 8, item 8. A short proposal for what follows this plan, based on [Future work](../project_plan.md#future-work) and on what Phase 8 revealed. 2026-11-27, drafted by the Claude Code agent for the project owner. Nothing here is decided; each stage needs the owner's approval and, from stage 3 on, clinical and institutional partners.

## What Phase 8 showed

1. **The abstractions held.** A second back end (Lighthouse), a second condition (the autism stub) and a scorer (the dummy) were added without changing the engine, the ADHD ruleset or any ADHD golden test. The one core change was honest reporting of resource types a server does not offer (`not_supported`), which every real back end will need.
2. **Real VA APIs offer much less than the synthetic server.** Lighthouse's Patient Health API exposes no screening instruments, flags, referrals, care plans, dispenses or statements; its encounters are inpatient and outpatient only. On Lighthouse the safety gate rests on coded conditions and encounters alone, and existing-care checks are mostly "not performed". Oracle Health offers more (9 of the 11 types), with uneven date-search rules ([desk review](integration/oracle_health.md)).
3. **Screening scores will not come from Lighthouse.** The research report's first integration question is answered "not exposed" for that API, so the LOINC verification (F2) and ASRS coding (open question 12) matter only for back ends that carry instruments, such as Oracle Health.
4. **Nothing has touched a real sandbox with credentials.** The Lighthouse adapter is built from documentation; its exit criterion is open.
5. **Sensitive-data labelling is undocumented on Lighthouse** and uses other label codes on Oracle; code-based classification is the only dependable mechanism ([review](security/lighthouse_security_labels.md)).

## Proposed stages

| Stage | Goal | Main work | Needs from the owner | Exit |
|---|---|---|---|---|
| 1. Release 1.0.0 | A reviewed, tagged release | Clinical content review (open questions 1, 14, 16, 17); ruleset `released`; tool contract 1.0.0; merge Phase 8 | Clinical reviewer; decisions on sex balance and ADR 0013 | `v1.0.0` tagged; release check passes |
| 2. Live sandboxes | Prove both VA back ends on real APIs with synthetic patients | Lighthouse CCG registration and a live run; an `oracle` server profile against Oracle's open sandbox (per-type date parameter names, adapter-side filtering for types with unusual date rules); record sandbox responses for tests | Lighthouse registration (open question 5); allow `fhir-open.cerner.com` in the environment | An assessment runs end to end on each sandbox |
| 3. Fit to VA data | Rules that use what VA APIs actually carry | Re-check every signal's availability per back end; decide whether a Lighthouse assessment should report a reduced-evidence mode; Appointment search for missed appointments (Lighthouse and Oracle both offer it); ICD-10-CM codes without the dot (ADR 0007) | Clinical review of any ruleset change (new version) | A per-back-end coverage table in the rule card |
| 4. Live model evaluation | Know how a real assistant uses the tools | The model-in-the-loop run (Phase 7 item 5) and tool description tuning | Budget and SDK approval (open question 4) | Pass bar met per model |
| 5. Governance and silent pilot preparation | Be ready for a partner's review | With a health-system partner: the governance documents in the [deployment guide](guide/deployment.md#6-governance-documents-required-before-any-clinical-use); a FHIR AuditEvent sink (risk P5); a local validation protocol | A clinical and institutional partner; ethics review | Partner approval to run silently |

Stages 1 and 2 can run in parallel; stage 3 depends on stage 2's findings.

## Not proposed yet

- **A real autism ruleset.** The stub proved the plugin; a real ruleset needs its own planning round, verified instruments (AQ-10, RAADS-14 have no verified codes) and a labelled cohort ([stub rule card](clinical/rule_card_autism_stub.md)).
- **A statistical model in the scorer slot.** The slot is proven; a model needs real labelled data, positive-unlabeled methods and prospective validation (research report), which only a partner can provide.
- **Note evidence, CDS Hooks, rules in CQL.** Still future work; each needs a partner and its own plan.

## Decisions requested

1. Approve stage 1 as the immediate next step (it is mostly owner review).
2. Approve applying for Lighthouse CCG sandbox access, and adding `fhir-open.cerner.com` to the development environment for an Oracle profile.
3. Choose whether to seek a clinical and institutional partner now, since stages 3 and 5 depend on one.
