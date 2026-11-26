---
description: Run one red-green-refactor cycle for a named behavior
argument-hint: <behavior to implement>
---

Implement this behavior using one strict test-driven cycle: $ARGUMENTS

If the behavior is ambiguous, or it changes clinical content or a tool contract, ask before starting.

1. **Red.** Write the smallest test that states the behavior. Choose the right layer from the table in `project_plan.md` (unit first; add a persona or golden expectation if it is a rule). Run it and confirm it fails for the expected reason. Show the failure.
2. **Green.** Write the least production code that makes it pass. Run the whole suite, not only the new test.
3. **Refactor.** Remove duplication and improve names with the suite green. Run lint and type checks.
4. **Check the invariants.** Confirm the change cannot produce diagnostic wording, skip the safety gate, drop evidence references, write to FHIR, or log clinical content.
5. **Record.** Commit at green with a clear message and update `status.md`.

Never weaken or skip an existing test to get to green. If an existing test looks wrong, stop and explain.
