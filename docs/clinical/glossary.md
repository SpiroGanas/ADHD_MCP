# Glossary

Terms used across the project. Clinical figures and sources are in the [research report](../../research/veteran_self_harm_risk_screening.md).

## Project terms

| Term | Meaning |
|---|---|
| Recommendation | The server's output: a suggestion to consider, or not consider, referral for formal screening. Never a diagnosis |
| Referral indicator | A reason to send a patient to a clinician for formal screening |
| Safety gate | The check for recorded self-harm signals that runs before, and takes priority over, any ADHD recommendation |
| Signal | A named, defined finding in the record, such as "stimulant-related disorder code within three years" |
| Weight class | A signal's strength in the rules: high-weight or modifier |
| Evidence item | A signal together with the FHIR resource references and dates that support it |
| Basis | The list of evidence items behind a recommendation |
| Exclusion | A finding that means no recommendation should be made, such as an existing ADHD diagnosis |
| Ruleset | A versioned, immutable set of rules held as data |
| Signal catalog | The versioned list of all signals a condition's rules can use |
| Rule card | The plain-language record of a ruleset |
| Scorer | An optional component, such as a statistical model, that can contribute a score to the rules engine |
| Condition plugin | The package of signal catalog, ruleset, exclusions and next-step text for one condition |
| Persona | A hand-built synthetic patient with a narrative and an expected outcome, used as a test specification |
| Decision trace | The record of which rules fired and which did not for one assessment |
| Data completeness | A statement of which data categories were available, empty, withheld or failed to load |
| Contract snapshot | A stored copy of a tool's name, description and schemas, used to detect unintended changes |

## Technical terms

| Term | Meaning |
|---|---|
| MCP | Model Context Protocol: an open protocol through which servers offer tools, resources and prompts to AI applications |
| FastMCP | The Python framework used to build this server |
| Tool, resource, prompt | MCP's three server primitives: callable functions, readable reference content, and message templates |
| FHIR | HL7 Fast Healthcare Interoperability Resources: the standard for exchanging health data. This project uses release R4 |
| US Core | The US profile set for FHIR that most US health systems implement |
| SMART on FHIR | The OAuth-based authorization standard for applications accessing FHIR servers |
| CDS Hooks | A standard for delivering decision support cards inside an EHR; future work |
| CQL | Clinical Quality Language, a standard for computable clinical rules; future work |
| ICD-10-CM | Diagnosis code system used in the US |
| LOINC | Code system for observations, including screening instruments |
| RxNorm | Code system for medications |
| SNOMED CT | Clinical terminology used for problems and findings |
| Value set | A named list of codes that together define one concept |
| ADR | Architecture decision record |
| TDD | Test-driven development |

## Clinical terms

| Term | Meaning |
|---|---|
| ADHD | Attention-deficit/hyperactivity disorder |
| ASRS | Adult ADHD Self-Report Scale, a screening questionnaire |
| DIVA-5 | A structured diagnostic interview for adult ADHD |
| PHQ-9 | Nine-item depression questionnaire; item 9 asks about thoughts of self-harm |
| C-SSRS | Columbia Suicide Severity Rating Scale; its screener is the VA's primary suicide screen |
| AUDIT-C | Three-item alcohol use screen |
| PC-PTSD-5 | Five-item primary care PTSD screen |
| TBI | Traumatic brain injury; can produce attention problems that resemble ADHD |
| SUD | Substance use disorder |
| MST | Military sexual trauma |

## VA and regulatory terms

| Term | Meaning |
|---|---|
| VA, VHA | Department of Veterans Affairs; Veterans Health Administration |
| Lighthouse | The VA's public API platform, including FHIR APIs and a sandbox |
| VistA, Oracle Health | The VA's legacy and new EHR systems |
| REACH VET, STORM | Existing VA predictive programs for suicide risk and opioid risk |
| Risk ID | The VA's universal suicide risk screening program |
| 38 U.S.C. 7332 | Law giving special protection to VA records on substance use, HIV and sickle cell anemia |
| 42 CFR Part 2 | Federal rule protecting substance use disorder treatment records |
| HIPAA | US health privacy and security law |
| Non-device CDS | Decision support software that meets criteria excluding it from medical device regulation |
