# Current Status

## Project state

Foundation bootstrap, minimal VK transport bootstrap, and minimal users bootstrap implemented.

## Current phase

User identity boundary ready. Repository prepared for the first user-aware application slice.

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

Integrate VK transport handoff with the users service without entering access control, billing, or AI execution:

1. add a minimal application handler for normalized VK events
2. resolve or create internal user by `vk_user_id`
3. keep VK transport thin and unaware of persistence details
4. do not add access checks yet
5. do not add AI execution yet

## Recommended next branch

`feat/vk-user-handoff`

## Recommended next task for AI

Implement only the minimal handoff between VK transport and the users module:

- normalized event application handler
- user resolution via users service
- no access control
- no billing logic
- no AI provider calls
- no subscription/access logic yet

Then update current status after the slice is complete.

## Notes

- Foundation is now in place
- Business modules beyond users are not implemented yet
- Current local Docker stack does not include Nginx; this is intentionally deferred
- VK transport currently validates payload shape, optional callback secret, and normalizes events
- VK transport does not yet execute business workflows
- Users module currently covers only minimal identity persistence and lookup/create
- Do not mix VK transport with billing or AI logic
- Do not start payment flows yet
- Do not start full AI integration yet
