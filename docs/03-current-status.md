# Current Status

## Project state

Foundation bootstrap, minimal VK transport bootstrap, minimal users bootstrap, and VK-to-users handoff implemented.

## Current phase

First user-aware application slice ready. Repository prepared for the next business slice.

## Completed

- Repository structure planned
- Core docs created:
  - product vision
  - architecture overview
  - engineering rules
  - current status
- Python project initialized
- FastAPI application skeleton added
- Config management added
- Base logging added
- PostgreSQL bootstrap added
- Redis bootstrap added
- Dramatiq worker bootstrap added
- Dockerfile added
- Docker Compose local stack added for:
  - api
  - worker
  - postgres
  - redis
- `.env.example` added
- Minimal healthcheck endpoint added
- Smoke tests added
- Alembic scaffold added
- Minimal VK callback endpoint added
- VK callback payload validation added
- VK event normalization into internal transport format added
- Thin handoff boundary to future service layer added
- VK transport tests added
- Minimal User model added
- Internal user <-> `vk_user_id` mapping added
- Users table migration added
- Users repository added
- Users find-or-create service added
- Users bootstrap tests added
- Application-level VK event handler added
- VK handoff now resolves or creates internal user by `vk_user_id`
- Safe no-op flow added for VK events without actor id
- VK-to-users handoff tests added

## Accepted technical direction

- Python 3.12
- FastAPI
- PostgreSQL
- Redis
- Dramatiq
- Modular monolith
- VK as transport layer
- AI providers through adapters
- Billing isolated from transport and AI integration layers

## MVP constraints

- Keep first version small and production-oriented
- Avoid overengineering
- Avoid broad architecture complexity
- Prefer small safe steps
- Write practical tests for critical scenarios only

## Next recommended step

Implement the first minimal access decision boundary without entering billing or AI execution:

1. define a small access-check application boundary
2. keep transport and users separate from access rules
3. return explicit allow/deny semantics for the next slice
4. do not add payment logic yet
5. do not add AI execution yet

## Recommended next branch

`feat/access-bootstrap`

## Recommended next task for AI

Implement only the minimal access bootstrap slice:

- access-check service boundary
- explicit allow/deny result model
- no billing logic
- no AI provider calls
- no subscription/payment orchestration yet

Then update current status after the slice is complete.

## Notes

- Foundation is now in place
- Business modules beyond users are not implemented yet
- Current local Docker stack does not include Nginx; this is intentionally deferred
- VK transport currently validates payload shape, optional callback secret, and normalizes events
- VK transport now hands normalized events into a minimal user-aware application slice
- Users module currently covers only minimal identity persistence and lookup/create
- VK events without actor id are safely ignored by the application handoff
- Do not mix VK transport with billing or AI logic
- Do not start payment flows yet
- Do not start full AI integration yet
