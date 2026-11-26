## Summary

What this changes and why.

## Plan reference

Phase and work item from `project_plan.md`, and any linked issue.

## How it was tested

Which tests were written first, and what they cover.

## Checklist

- [ ] Tests were written before the code and now pass
- [ ] Lint and type checks pass
- [ ] `status.md` is updated
- [ ] Documentation is updated where needed (architecture, rule card, ADR)
- [ ] No real patient data, identifiers or credentials are included

## Safety checklist

Complete if this touches tools, rules, outputs, logging or clinical data files. Otherwise write "Not applicable".

- [ ] No output states or implies a diagnosis
- [ ] The safety gate still runs before any recommendation
- [ ] Every signal in an output cites a FHIR resource
- [ ] No tool writes to a FHIR server
- [ ] No clinical values or text are logged
- [ ] No unverified code or cutoff is used in an active ruleset
- [ ] Contract snapshot changes are intentional and explained below

## Notes for the reviewer

Decisions made, open questions, anything left for a follow-up.
