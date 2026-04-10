# Current Status

## Project state

Foundation bootstrap and minimal VK transport bootstrap implemented.

## Current phase

Transport boundary ready. Repository prepared for the first application slice.

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

Implement the minimal users bootstrap without entering billing, access control, or AI execution:

1. add internal user model linked to VK user id
2. add migration for user storage
3. add repository for user lookup/create
4. add thin service for find-or-create user
5. keep transport unaware of user persistence details

## Recommended next branch

`feat/users-bootstrap`

## Recommended next task for AI

Implement only the minimal users slice:

- user entity and migration
- repository and service layer
- find-or-create by VK user id
- no billing logic
- no AI provider calls
- no subscription/access logic yet

Then update current status after the slice is complete.

## Notes

- Foundation is now in place
- Business modules are not implemented yet
- Current local Docker stack does not include Nginx; this is intentionally deferred
- VK transport currently validates payload shape, optional callback secret, and normalizes events
- VK transport does not yet execute business workflows
- Do not mix VK transport with billing or AI logic
- Do not start payment flows yet
- Do not start full AI integration yet
