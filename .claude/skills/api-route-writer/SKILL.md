---
name: api-route-writer
description: Use when adding new FastAPI routes. Ensures consistent structure, validation, error handling, idempotency, and audit logging.
---

# Writing FastAPI Routes for AgentMarket

## Structure of every route
1. Pydantic request model (in `app/api/schemas/<module>.py`)
2. Pydantic response model (same file)
3. Route handler in `app/api/routes/<module>.py` — thin, calls service
4. Service in `app/domain/<module>.py` — business logic
5. Repository in `app/adapters/db/repositories/<module>.py` — persistence

## Required for ALL routes
- Type hints on every parameter
- Pydantic models for request body and response
- Explicit status codes (`status_code=201` on create, etc.)
- Error handling: `HTTPException` with `detail`, never bare `Exception`
- Logging: structured (`logger.info("event_name", extra={...})`), no print
- OpenAPI summary + description on the decorator

## Required for MUTATING routes (POST, PUT, PATCH, DELETE)
- `Idempotency-Key` header support — check before mutating
- Return 200 with the existing result if key has been seen for the same request
- Audit log entry for every state change (event name + payload)
- Authorization check (will be JWT post-MVP; for MVP, stub user_id from header)

## Template
```python
# app/api/schemas/<module>.py
from pydantic import BaseModel, Field

class CreateThingRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., gt=0)

class ThingResponse(BaseModel):
    id: str
    name: str
    amount: float
    created_at: datetime

# app/api/routes/<module>.py
from fastapi import APIRouter, Depends, Header, HTTPException, status
from app.api.schemas.things import CreateThingRequest, ThingResponse
from app.domain.things import ThingService
from app.adapters.db import get_db

router = APIRouter(prefix="/things", tags=["things"])

@router.post(
    "",
    response_model=ThingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a thing",
    description="Creates a thing with idempotency support."
)
async def create_thing(
    body: CreateThingRequest,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    db: AsyncSession = Depends(get_db),
    service: ThingService = Depends(),
) -> ThingResponse:
    try:
        thing = await service.create(body, idempotency_key=idempotency_key, db=db)
        return ThingResponse.model_validate(thing)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
```

## Idempotency pattern
```python
# In service layer
async def create(self, body, idempotency_key, db):
    if idempotency_key:
        existing = await self.repo.find_by_idempotency_key(idempotency_key, db)
        if existing:
            return existing
    # ... do the work ...
    await self.audit.log("thing_created", {"thing_id": thing.id, ...}, db)
    return thing
```

## Forbidden in route handlers
- ❌ DB queries directly (use repositories)
- ❌ Direct LLM calls (use domain services)
- ❌ Returning raw SQLAlchemy models (use Pydantic response models)
- ❌ Synchronous code (`time.sleep`, `requests.get`) — use async equivalents
- ❌ Bare `try/except: pass` — always log and either re-raise or return error
- ❌ Hardcoded secrets / API keys — read from settings

## Error codes (use consistently)
- 400: validation error, bad input from client
- 401: missing auth (post-MVP)
- 403: auth present but insufficient
- 404: resource not found
- 409: conflict (e.g., idempotency key reused with different body)
- 422: pydantic validation auto-handles
- 500: unhandled — should never happen, indicates bug

## For AgentMarket specifically
- Routes that touch money or signatures require audit log entry
- Routes that produce a session require WebSocket pub for live updates
- The `verify_receipt` route is the ONLY one that doesn't need auth (public verification)
