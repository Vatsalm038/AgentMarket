# Project Brief — Agent Market

## One-line pitch
Two-sided marketplace where buyers describe what they want and merchants list what
they have, and AI agents negotiate on both sides — so humans don't haggle, their
agents do. Every spending decision cryptographically bounded; every transaction
verifiable.

## The problem

Indian hyperlocal commerce has price discovery friction. A buyer wanting a wallet
under ₹500 in Andheri today has bad options: walk shop to shop, search Amazon (no
local sellers, fixed prices), or OLX (manual chat, hours of haggling). Merchants
mirror the problem: small sellers can't reach buyers who don't already know their shop.

## The wedge

**MCP-first distribution.** A user already in ChatGPT or Claude says "find me a
wallet under ₹500 in Mumbai." Our platform handles it without them visiting a
website. This is rare in 2026 — most projects build their own UI.

**Cryptographic delegation.** Every spending decision is bounded by an Ed25519-signed
policy. Every transaction produces a verifiable receipt. This is the trust layer
local commerce needs and most platforms skip.

## User flow

1. Buyer (in ChatGPT/Claude via MCP, or web): "wallet under ₹500 in Andheri,
   polite-diplomat negotiation style"
2. Matcher finds eligible merchants (location + product embedding + price band)
3. Platform spawns buyer agent + N merchant agents
4. Auction runs (multi-merchant) or 1-on-1 negotiation
5. Winner presented, buyer approves
6. Razorpay UPI test mode → signed receipt
7. Both parties get audit trail

## What makes this different

- MCP-first (almost no portfolio projects have this in 2026)
- Cryptographic delegation + signed receipts (most agent projects skip auth entirely)
- Configurable agent personas (6 negotiation skills)
- Verifiable replay (every negotiation is reproducible)
- Indian context (Mumbai locations, INR, UPI, regional merchant names)

## Revenue model (post-MVP, for the pitch)

- Transaction fee 2-3% on settled value
- Premium negotiation skills
- Merchant SaaS tier (analytics, bulk listing)
- Audit reports for B2B procurement

## Success criteria for MVP (5 working days, ~3 calendar weeks)

1. User in Claude.ai installs MCP, runs full purchase flow without leaving Claude
2. Web dashboard shows signed policy + negotiation trail + verifiable receipt
3. Razorpay test mode UPI completes
4. WebSocket live negotiation feed works
5. Live URL on custom domain
6. 3-minute demo video
7. README + LinkedIn post + resume bullet

## Out of scope (see CLAUDE.md "What this project is NOT")
