---
name: llm-prompt-writer
description: Use when creating or modifying system prompts for buyer agents, merchant agents, matcher, or any LLM call in the system. Ensures prompts respect math clamps and JSON output contracts.
---

# Writing LLM Prompts for AgentMarket

## Hard rules (non-negotiable)
1. **NEVER ask the LLM to do arithmetic.** Pre-compute in Python, pass as constraint.
2. **ALWAYS demand strict JSON output**, no markdown, no preamble, no trailing prose.
3. **ALWAYS define the JSON schema explicitly** with example values inline.
4. **ALWAYS include round number / max rounds** for negotiation prompts.
5. **ALWAYS clamp numeric LLM output in Python** on return — assume the LLM lies about numbers.
6. **ALWAYS use temperature=0 + seed** for negotiation calls (required for verifiable replay — see ADR-007).

## Standard structure
```
You are <role> doing <task>.

Context (read-only facts):
- <constraint 1, e.g. "listed price: ₹999">
- <constraint 2, e.g. "your last counter: ₹820">
- <constraint 3, e.g. "round 3 of 5">

Pre-computed for you (do not recompute):
- Suggested counter (split-the-difference): ₹<computed_value>
- Hard floor: ₹<floor>

Rules:
- <rule 1, expressed as a logical condition>
- <rule 2>

Respond ONLY with valid JSON, no markdown, no explanation:
{"action": "accept"|"counter"|"reject", "price": <number>, "reason": "<≤15 words>"}
```

## Example: merchant agent prompt
```
You are a merchant agent selling 'Leather Wallet (Genuine)' listed at ₹650.
Buyer's current offer: ₹420.
Your last counter: ₹600.
Pre-computed split price: ₹510.
Round: 2 of 5.

Rules:
- Accept if buyer_offer >= ₹552 (85% of listed)
- Counter using ₹510 (always LOWER than your last counter ₹600)
- Reject if buyer_offer < ₹390 (60% of listed)

Respond ONLY with valid JSON:
{"action": "accept"|"counter"|"reject", "price": <number>, "reason": "<≤15 words>"}
```

## Persona prompts (the 6 skills)
The 6 negotiation personas are stored in `migrations/00X_seed_agent_skills.sql` as
`system_prompt_template` strings. When modifying a persona:
- Keep persona language brief (3-5 sentences)
- Specify target close % as a number, not "low" or "high"
- Specify max rounds as a number
- Persona prompts are PREFIXED to the standard structure above, not replaced

## After receiving LLM output
Always run this clamp in Python:
```python
result = json.loads(response.content)
# Clamp numeric output
if result.get("price"):
    result["price"] = max(floor, min(float(result["price"]), ceiling))
# Clamp action
if result.get("action") not in ("accept", "counter", "reject"):
    result["action"] = "counter"
```

## For verifiable replay (ADR-007)
Every LLM call must store in `negotiation_sessions.replay_data` (jsonb):
```json
{
  "round_1": {
    "model": "gpt-4o-mini",
    "temperature": 0,
    "seed": 42,
    "system_prompt": "...",
    "user_prompt": "...",
    "response": "..."
  }
}
```

## Forbidden patterns
- ❌ "Calculate the average of X and Y" (LLM does arithmetic)
- ❌ "Use your judgment on a fair price" (no constraints)
- ❌ "Respond with a number" (no schema)
- ❌ Markdown code fences in expected output
- ❌ "Be creative" / "be helpful" (vague)
- ❌ Open-ended `reason` fields (always cap word count)
