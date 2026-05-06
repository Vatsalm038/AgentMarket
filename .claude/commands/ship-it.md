---
description: Final pre-deploy checklist before going live
---

Walk through this checklist. Stop and report any FAIL.

## Backend
- [ ] All migrations applied to production DB
- [ ] Seed data loaded in production
- [ ] Health check endpoint /health returns 200
- [ ] All env vars set in Render: DATABASE_URL, OPENAI_API_KEY, RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET, PLATFORM_PRIVATE_KEY, MCP_API_KEY
- [ ] No secrets in git history (`git log -S "sk-" --all` should be empty)
- [ ] CORS allows the production frontend domain only
- [ ] Test mode banner visible (Razorpay)

## MCP server
- [ ] Deployed on Render, separate service from backend
- [ ] /health endpoint responds
- [ ] Tool descriptions are concrete, not vague
- [ ] API key auth working (try a request without key → should fail)

## Frontend
- [ ] Deployed on Vercel
- [ ] Custom domain configured, SSL active
- [ ] All 6 pages render: /, /sessions, /session/:id, /replay/:id, /verify, /install-mcp
- [ ] No console errors
- [ ] No 404s on assets
- [ ] Loading + empty + error states tested

## End-to-end smoke test
- [ ] Open Claude.ai
- [ ] Install MCP via /install-mcp instructions
- [ ] Run search_local_merchants tool
- [ ] Run negotiate tool
- [ ] Open /session/:id of the result
- [ ] Click Verify on receipt → green check
- [ ] Click Replay → outcomes match

## Demo materials
- [ ] Demo video recorded, edited, uploaded
- [ ] README has embedded GIF
- [ ] LinkedIn post drafted
- [ ] Resume bullet drafted

If all green, tell me to ship. If anything red, fix it and rerun.
