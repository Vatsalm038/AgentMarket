---
name: mcp-tool-writer
description: Use when adding tools to the MCP server (mcp_server/ directory). Ensures tool descriptions are clear, schemas are tight, and behavior is idempotent.
---

# Writing MCP Tools for AgentMarket

## What is an MCP tool
A function exposed to Claude/ChatGPT via the Model Context Protocol. Users in those
clients can invoke our tools as if they were native to the chat. We use `fastmcp`
in Python.

## Tool design principles
1. **Descriptions are everything.** Claude/ChatGPT decide whether to use a tool
   based on the description. Be concrete: "Search merchants in a Mumbai area
   selling a specific product type within budget" beats "Find products."
2. **One tool, one job.** No "do_everything(action, ...)" tools.
3. **Tight Pydantic schemas.** Don't accept `dict[str, Any]` — define the shape.
4. **Idempotent reads, explicit writes.** Reads should never have side effects;
   writes should be obvious from the name.
5. **Return structured data.** Models work better with structured JSON than prose.
6. **Bound result sizes.** Default to top 5-10 results, allow override up to 25.

## Standard structure (fastmcp)
```python
from fastmcp import FastMCP
from pydantic import BaseModel, Field
import httpx
from app.config import BACKEND_URL, API_KEY

mcp = FastMCP("agentmarket")

class SearchInput(BaseModel):
    product_query: str = Field(..., description="What to search for, e.g. 'leather wallet'")
    location: str = Field(..., description="Mumbai neighborhood, e.g. 'Andheri West'")
    max_price_inr: float = Field(..., gt=0, description="Maximum price in INR")
    radius_km: float = Field(default=5.0, ge=0.5, le=20, description="Search radius")

class SearchResult(BaseModel):
    product_id: str
    title: str
    listed_price_inr: float
    merchant_name: str
    distance_km: float

@mcp.tool()
async def search_local_merchants(input: SearchInput) -> list[SearchResult]:
    """
    Search Mumbai merchants for a product matching the query, within budget and
    location radius. Returns up to 10 best matches sorted by relevance.

    Use this when a user wants to find a specific product locally before
    initiating a negotiation.
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{BACKEND_URL}/api/match",
            headers={"X-API-Key": API_KEY},
            json=input.model_dump(),
            timeout=10,
        )
        resp.raise_for_status()
        return [SearchResult.model_validate(item) for item in resp.json()["matches"]]
```

## Description writing checklist
- [ ] Says WHAT the tool does (one sentence)
- [ ] Says WHEN to use it (one sentence)
- [ ] Says what it returns (data type + max count)
- [ ] Avoids ambiguity (no "various" / "etc")

## Required for write tools
- Idempotency key parameter (for negotiate, settle)
- Audit log entry on backend side
- Return enough info to verify the action succeeded

## Required for read tools
- No state mutation
- Cache where possible (matcher results can be cached for ~60s)
- Bounded results (default 10, max 25)

## Authentication
- All tools take an API key from env (`MCP_API_KEY`)
- Backend validates the key on every request
- For MVP, single hardcoded key. Post-MVP: per-user keys generated in dashboard.
- API key NEVER goes in tool descriptions or input schemas

## Testing MCP tools locally
```bash
# Run MCP server (from repo root)
python -m mcp_server.server

# In another terminal, install in Claude Code
claude mcp add agentmarket python /path/to/mcp_server/server.py

# Or test directly with the MCP inspector
fastmcp dev mcp_server/server.py
```

## Tools currently planned for AgentMarket (see day-plan.md Day 2)
1. `search_local_merchants` — read, find products
2. `negotiate` — write, runs auction, returns winner + receipt
3. `verify_receipt` — read, verifies signature
4. `get_audit_trail` — read, returns full negotiation log
5. `replay_negotiation` — write-ish (creates a replay session), reproduces past run

## Forbidden
- ❌ Tools that take free-form `instructions: str` and try to interpret them
- ❌ Tools that wrap multiple actions ("do_everything")
- ❌ Tools that don't validate inputs
- ❌ Tools that return unbounded data
- ❌ Tools that auth via the input schema (always use header/env)
- ❌ Tools that print secrets in errors
