# ADR 0009: Hand-curated RxNorm drug classes, expanded and verified with RxNav

- **Status:** Accepted
- **Date:** 2026-11-27
- **Decided by:** project owner (option chosen 2026-11-27); implemented by the Claude Code agent

## Context

`get_medication_timeline` must group a patient's medications into the classes the ADHD rules use: stimulant and non-stimulant ADHD medications, antidepressants (with a count of distinct agents) and sedative-hypnotics. FHIR medication codes are usually RxNorm product concepts (SCD, SBD, packs), not ingredients, so a class needs both its ingredients and the products that contain them. The tool must not call an external service at run time (ADR 0002, read-only and self-contained), and every code used by a rule must be verified (standing invariant 6).

## Decision

Each class is a hand-curated list of ingredient names in `scripts/drug_class_spec.toml`. `scripts/build_drug_classes.py` looks each name up in NLM RxNav, refuses anything that is not an active ingredient (TTY `IN`, not suppressed, name equal to the curated name), expands it to the active product concepts that contain it (PIN, MIN, SCDC, SCDF, SCDG, SCD, SBDC, SBDF, SBDG, SBD, GPCK, BPCK) and writes `src/adhd_mcp/data/drug_classes/<id>.toml` with per-ingredient provenance (RxNorm release, date, checker). The generated files are committed. A medication maps to every class ingredient its code contains, so a combination product counts once per class ingredient and the distinct-agent count is by ingredient (dose, form, brand and generic collapse).

Curation choices, recorded as inference for owner review: guanfacine and clonidine are not in the non-stimulant ADHD class (mostly hypertension at ingredient level); trazodone, doxepin, amitriptyline, selegiline and milnacipran are not counted as antidepressants (frequent insomnia, pain, Parkinson or fibromyalgia use); modafinil and armodafinil are not ADHD medications.

## Alternatives considered

| Option | Why not |
|---|---|
| Query RxNav or another terminology server at run time | Adds an external runtime dependency and a privacy question (medication codes leave the server); results could change between identical calls |
| Ingredient codes only, no product expansion | Real records code products; nearly every medication would go unclassified |
| A drug-class source such as RxClass (ATC, VA class, MED-RT) | Class membership is broader than the rules need (for example ATC N06A includes trazodone) and harder to review; a curated list is short and explicit |

## Consequences

- Classes are reviewable in one short spec file; rebuilding refreshes product codes for a new RxNorm release.
- Retired (obsolete) product codes are not returned by RxNav and are not matched. Older records that use them are reported as unclassified medication. Revisit with RxNorm history files if this matters on real data (Phase 8).
- Some products carry a class ingredient for another use (for example bupropion with naltrexone for weight loss). They count as that ingredient. Recorded in the rule card.
- rxnav.nlm.nih.gov was added to the development environment's allowed hosts for the build.
