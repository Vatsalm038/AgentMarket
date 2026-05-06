# Post-MVP Backlog

## Tier 1 — first real users
- [ ] Real WhatsApp Business API
- [ ] Live-mode Razorpay (after legal review)
- [ ] Multi-currency
- [ ] Email/SMS notifications
- [ ] Merchant KYC (Aadhaar/PAN)
- [ ] LLM cost optimization
- [ ] Real merchant onboarding flow with vision
- [ ] Buyer dashboard (currently MCP-only)
- [ ] Merchant dashboard (currently SQL-only)

## Tier 1.5 — schema items deferred from 1.2
- [ ] `negotiation_sessions.approval_status` + `approved_at` + `approved_by` —
  buyer-approval gate before settlement. Deferred because MCP-first flow
  has no separate approval step in the MVP. Add when web-first flow lands.
- [ ] Swap `products.embedding` JSONB → `pgvector` `vector(1536)` once
  embedding count crosses ~10k or matcher latency exceeds 50ms.

## Tier 2 — product polish
- [ ] Sandboxed custom agent skills
- [ ] Skill marketplace
- [ ] Agent memory across sessions
- [ ] Multi-language (Hindi, Marathi, Tamil)
- [ ] Mobile native app
- [ ] Buyer/merchant rating
- [ ] Dispute resolution flow

## Tier 3 — scale + infra
- [ ] Dedicated infra (off Render)
- [ ] Postgres read replicas
- [ ] Redis for sessions + WebSocket pub/sub
- [ ] Background queue (Arq/Celery)
- [ ] OpenTelemetry, Grafana

## Tier 4 — protocol
- [ ] W3C Verifiable Credential format
- [ ] Public protocol spec
- [ ] SDK in Go and TypeScript
- [ ] Federation across platforms

## Ideas to evaluate
- [ ] Group buying
- [ ] Reverse auction
- [ ] Subscription negotiation
