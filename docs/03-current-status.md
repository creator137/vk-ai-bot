# Current Status

## Project state

Foundation bootstrap implemented.

## Current phase

Foundation ready. Repository prepared for the first functional slice.

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

Implement the first inbound transport slice for VK without entering billing or AI execution:

1. add validated VK webhook entrypoint
2. normalize incoming VK payload
3. isolate VK transport from business logic
4. prepare handoff to future service layer
5. keep response flow minimal and explicit

## Recommended next branch

`feat/vk-transport-bootstrap`

## Recommended next task for AI

Implement only the minimal VK transport boundary:

- request schema validation
- payload normalization
- thin transport handler
- no billing logic
- no AI provider calls
- no user/business workflows yet

Then update current status after the slice is complete.

## Notes

- Foundation is now in place
- Business modules are not implemented yet
- Current local Docker stack does not include Nginx; this is intentionally deferred
- Do not mix VK transport with billing or AI logic
- Do not start payment flows yet
- Do not start full AI integration yet
