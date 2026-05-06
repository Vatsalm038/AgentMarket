# Demo Video Script (3 minutes)

## Pre-recording checklist
- [ ] Production URL working
- [ ] MCP installed in Claude.ai
- [ ] Test session pre-run so /session/:id shows good data
- [ ] Browser zoomed to 110% for readability
- [ ] Other tabs closed
- [ ] Notifications silenced
- [ ] OBS or Loom set up at 1080p

## Script

### 0:00 — 0:20 — The hook
"Imagine asking AI to find you a wallet under ₹500 near you in Mumbai. Today,
ChatGPT and Claude can't actually do this — they don't know local merchants,
they can't negotiate, they can't pay. Watch what happens when they can."

(Show: blank Claude.ai screen)

### 0:20 — 0:50 — The MCP install + query
"I built an MCP server that gives Claude exactly that. One config, and it can
search local merchants, run an auction between AI agents, and produce a
cryptographically signed receipt."

(Show: MCP install one-liner being copy-pasted, then in Claude.ai:)
"Find me a leather wallet under ₹500 in Andheri Mumbai. Negotiate politely."

### 0:50 — 1:40 — The auction in real-time
(Show: Claude calls search_local_merchants, returns 3 matches. Then negotiate.
Switch to web dashboard /session/:id, watch rounds populate via WebSocket.)

"Three AI merchant agents — each representing a real merchant — compete in
real-time. Each one knows their floor price, their persona, their location.
The buyer agent splits-the-difference each round. Round one: ₹420 vs ₹600.
Round two: ₹510. Settled at ₹490. Total time: 12 seconds."

### 1:40 — 2:20 — The verification moment
(Show: Click on the receipt JSON. Click "Verify Receipt".)

"Every transaction produces an Ed25519-signed receipt that anyone can verify
against our published public key. The signature covers the buyer agent ID,
the policy that authorized this purchase, the amount, the timestamp.
This receipt is non-repudiable — the buyer can't deny it, the platform can't
fake it."

(Click Verify → green check)

(Show: /replay/:id)

"Even better — every negotiation is reproducible. We store the LLM prompts,
the model, the temperature, the seed. Click replay and you get the same
outcome. AI decisions you can audit."

### 2:20 — 2:50 — The architecture slide
(Static slide, 30 seconds)

Tech: MCP, Ed25519, OpenAI embeddings, Verifiable Replay, FastAPI, React, Razorpay UPI
Architecture diagram (simple)
Why it matters: trust layer for agentic commerce

### 2:50 — 3:00 — The close
"Built solo in 5 working days. Code on GitHub. Live demo at agentmarket.app.
Hire me to build more of this. Vatsal."

(Show: GitHub URL + LinkedIn URL on screen)

## Editing notes
- Cut any pause longer than 1 second
- Add subtle background music (LoFi-style, low volume)
- Captions in Inter font, white-on-black at bottom
- End card with all links + email
- Export 1080p, MP4, < 30MB if possible (LinkedIn limit)
