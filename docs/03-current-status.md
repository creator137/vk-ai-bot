# Current Status

## Project state

Foundation bootstrap, minimal VK transport bootstrap, minimal users bootstrap, VK-to-users handoff, minimal access decision boundary, minimal request outcome slice, minimal outcome consumer slice, minimal denied/accepted branch handling, minimal outward reaction slice, minimal access grant issuance slice, minimal VK outward delivery slice, and minimal AI bootstrap for accepted path implemented.

## Current phase

First real accepted text execution path ready. Repository prepared for the next request persistence/context slice.

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
- Explicit handling for consumed outcome branches added
- VK transport now handles consumed branches explicitly:
  - ignored
  - halted
  - ready_for_next_stage
- Consumed outcome handling tests added
- Minimal VK outward reaction planning added
- Outward reaction planning rules added:
  - ignored -> no reaction
  - halted -> static denied text
  - ready_for_next_stage -> no reaction
- VK transport now plans and logs outward reactions without real VK dispatch
- Outward reaction tests added
- Internal protected access grant endpoint added
- Minimal idempotent access grant issuance added
- Access grants can now be issued through `vk_user_id -> user -> grant`
- Access grant issuance tests added
- Minimal VK outbound delivery adapter added
- Planned denied VK reactions can now be delivered through `messages.send`
- Outward delivery safely skips when `peer_id` is missing
- VK outward delivery tests added
- Minimal OpenAI text provider adapter added
- Accepted `message_new` text requests now dispatch to a worker only for the accepted branch
- Accepted non-text or non-message events now safe no-op without dispatch
- Worker now calls the AI provider and delivers text replies back through the existing VK outward delivery path
- Accepted AI bootstrap tests added

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

Implement the first minimal request persistence/context slice on top of the current accepted text path:

1. keep denied and accepted delivery behavior unchanged
2. persist a minimal request/response record for accepted text flows
3. do not add payment logic yet
4. do not add attachments yet
5. do not add broad conversation memory yet

## Recommended next branch

`feat/request-persistence-bootstrap`

## Recommended next task for AI

Implement only the minimal request persistence/context slice:

- persist accepted text request/response pairs
- no broad conversation system
- no billing logic
- no attachments yet
- no subscription/payment orchestration yet
- no usage accounting yet

Then update current status after the slice is complete.

## Notes

- Foundation is now in place
- Business modules beyond users are not implemented yet
- Current local Docker stack does not include Nginx; this is intentionally deferred
- VK transport currently validates payload shape, optional callback secret, and normalizes events
- VK transport now hands normalized events into a minimal user-aware application slice
- Users module currently covers only minimal identity persistence and lookup/create
- Access module currently uses persisted access grants and deny-by-default decisions
- Access grant issuance is currently manual through a protected internal endpoint
- Application layer currently ends with explicit skipped/denied/accepted request outcomes
- `accepted` at the application outcome level means readiness for the next processing stage
- Outcome consumer currently maps request outcomes to ignored/halted/ready_for_next_stage only
- Current handled branches only log and explicitly finish the flow
- Current outward reaction planning only plans a static denied text
- Current denied outward reaction is now delivered through VK `messages.send` when outbound token is configured
- Current accepted branch now supports a single text-in -> text-out worker path
- Current accepted AI path uses a single OpenAI text provider adapter with the model configured via env
- Current accepted AI path does not include attachments or conversation persistence yet
- VK events without actor id are safely ignored by the application handoff
- Do not mix VK transport with billing or AI logic
- Do not start payment flows yet
- Do not expand into a full AI platform yet
