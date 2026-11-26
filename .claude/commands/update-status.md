---
description: Bring status.md in line with the actual state of the repository
---

Update `status.md` so that a new session with no other context could resume from it.

1. Read `status.md`.
2. Compare it with the repository: branch, recent commits, uncommitted changes, test state, and open or merged pull requests.
3. Rewrite the sections, keeping the existing layout:
   - **Last updated**, **Current phase**, **Branch**
   - **Done**: add finished work items with pull request links
   - **In progress**: what is partly done, the files involved, and the failing test if there is one
   - **Next steps**: specific, ordered, and actionable; the first item should name the first test to write
   - **Open questions**: add new ones, remove answered ones and record the answer under Decisions
   - **Pull requests**: add or update rows
4. Keep it short. Collapse work from finished phases into one line each.
5. Show a summary of what changed.
