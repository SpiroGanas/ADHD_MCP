---
description: Final checks, status update, commit, push, then create and watch the pull request
---

The programming for the current task is done. Finish it properly.

1. **Verify.** Run the full check suite (tests, lint, type check; commands are in `CLAUDE.md`). If anything fails, fix it first. Do not skip or weaken tests.
2. **Review.** If the change touches tools, rules, outputs, logging or clinical data files, run the `clinical-safety-reviewer` subagent on the diff and resolve what it finds.
3. **Document.** Update `status.md`. Update the architecture document, rule card or an ADR if the change calls for it.
4. **Commit and push** to the working branch with a clear message.
5. **Create a pull request** using `.github/pull_request_template.md`. Fill in every section and both checklists truthfully.
6. **Watch the pull request.** Subscribe to its activity. Fix failing CI and respond to review comments until it is merged or the user says to stop.
7. **Record the pull request link** in `status.md` and push that update.

Report what was done, the pull request link, and anything left open.
