---
description: End of session — wrap up, update docs, commit
---

1. Run `git log --oneline --since="6 hours ago"` to see what was committed
2. Run `git diff main --stat` (or `git diff origin/main --stat`) to see changes
3. Update docs/day-plan.md:
   - Mark completed tickets with [x]
   - Note any tickets pushed to next session
4. Append any architectural decisions made today to docs/decisions.md as ADRs
5. Append surprises/learnings to docs/learnings.md (one-liners are fine)
6. Update the "Active context" section of CLAUDE.md (calendar day, current ticket, last decision, blockers)
7. Commit doc updates: `docs: end-of-session update`
8. Tell me:
   - What shipped today (in 2-3 sentences)
   - What's the first ticket next session
   - Any blockers I should think about between now and then
