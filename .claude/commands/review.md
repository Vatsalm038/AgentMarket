---
description: Review uncommitted changes before commit
---

1. Run `git diff --stat` to see what changed
2. Determine which agents to invoke:
   - If files in `backend/` or `mcp-server/` changed → invoke code-reviewer agent
   - If files in `frontend/` changed → invoke design-reviewer agent
   - If both → run code-reviewer first, then design-reviewer
   - If only docs/ changed → skip review, just summarize the doc changes
3. Show me the verdict (APPROVE / REQUEST CHANGES / BLOCK) from each
4. Wait for my confirmation before committing
