# Current Status

## Project state

Foundation bootstrap, minimal VK transport bootstrap, minimal users bootstrap, VK-to-users handoff, minimal access decision boundary, minimal request outcome slice, and minimal outcome consumer slice implemented.

## Current phase

First explicit outcome consumer slice ready. Repository prepared for the next outcome-specific handling slice.

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
- Minimal access module added
- Access grant model added
- Access grant migration added
- Access decision service added
- Access deny-by-default behavior added
- VK application slice now returns explicit allow/deny access decisions
- Access boundary tests added
- Typed RequestOutcome model added
- VK application slice now returns explicit request outcomes:
  - skipped
  - denied
  - accepted
- VK transport now logs application request outcomes without changing callback contract
- Request outcome tests added
- Minimal outcome consumer added
- Outcome consumer now maps request outcomes into explicit flow completion states:
  - ignored
  - halted
  - ready_for_next_stage
- VK transport now consumes request outcomes for explicit flow completion and branch-specific logging
- Outcome consumer tests added

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

Implement the first minimal outcome-specific handling slice on top of consumed outcomes:

1. keep consumed outcome states explicit
2. add minimal handling for denied vs accepted branches
3. do not add payment logic yet
4. do not add AI execution yet
5. do not add conversations persistence yet

## Recommended next branch

`feat/denied-outcome-handling`

## Recommended next task for AI

Implement only the minimal denied/accepted outcome handling slice:

- explicit handling for consumed denied vs accepted branches
- no fake AI response generation
- no billing logic
- no AI provider calls
- no subscription/payment orchestration yet
- no conversations persistence yet

Then update current status after the slice is complete.

## Notes

- Foundation is now in place
- Business modules beyond users are not implemented yet
- Current local Docker stack does not include Nginx; this is intentionally deferred
- VK transport currently validates payload shape, optional callback secret, and normalizes events
- VK transport now hands normalized events into a minimal user-aware application slice
- Users module currently covers only minimal identity persistence and lookup/create
- Access module currently uses persisted access grants and deny-by-default decisions
- Access grant issuance flow is not implemented yet
- Application layer currently ends with explicit skipped/denied/accepted request outcomes
- `accepted` currently means readiness for the next processing stage only
- Outcome consumer currently maps request outcomes to ignored/halted/ready_for_next_stage only
- VK events without actor id are safely ignored by the application handoff
- Do not mix VK transport with billing or AI logic
- Do not start payment flows yet
- Do not start full AI integration yet
