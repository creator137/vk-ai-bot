# Current Status

## Project state

Foundation bootstrap, minimal VK transport bootstrap, minimal users bootstrap, VK-to-users handoff, minimal access decision boundary, minimal request outcome slice, minimal outcome consumer slice, minimal denied/accepted branch handling, minimal outward reaction slice, minimal access grant issuance slice, minimal VK outward delivery slice, minimal AI bootstrap for accepted path, minimal accepted request persistence slice, and minimal subscription/token accounting slice implemented.

## Current phase

First minimal subscription token accounting slice ready. Repository prepared for rollout and verification before any payment or broader context work.

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
- Minimal Gemini text provider adapter added
- Minimal Claude text provider adapter added
- Accepted AI worker now supports env-driven provider selection between OpenAI, Gemini, and Claude
- Accepted `message_new` text requests now dispatch to a worker only for the accepted branch
- Accepted non-text or non-message events now safe no-op without dispatch
- Worker now calls the AI provider and delivers text replies back through the existing VK outward delivery path
- Accepted AI bootstrap tests added
- Minimal accepted request record model added
- Accepted request record migration added
- Minimal accepted request persistence service added
- Accepted worker now persists accepted text request/response pairs before VK delivery
- Accepted request persistence tests added
- Minimal subscription catalog added:
  - Lite — 379₽ — 35000 tokens
  - Pro — 599₽ — 100000 tokens
  - Max — 1190₽ — 200000 tokens
- Minimal user subscription model added
- User subscription migration added
- Internal protected subscription issuance endpoint added
- Access boundary now allows either manual grant or active subscription with remaining tokens
- Denied VK text now shows available subscription plans and token accounting rule
- AI providers now return factual input/output token usage when available from API responses
- Accepted worker now persists input/output/total token usage for each accepted text exchange
- Accepted worker now deducts tokens from active subscriptions by factual input + output usage
- Subscription tests added

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

Roll out and verify the current subscription-aware accepted path before any broader billing or context step:

1. apply the latest migration on the server
2. issue test subscriptions through the internal endpoint
3. verify accepted requests spend factual provider usage
4. verify denied responses show plans when no active access is present
5. keep payment collection, attachments, and broader memory out of scope for now

## Recommended next branch

`feat/subscription-rollout-verification`

## Recommended next task for AI

Complete rollout and verification of the existing subscription slice:

- deploy the latest migration and worker/api code
- issue subscriptions through the protected internal endpoint
- confirm accepted requests deduct factual provider usage
- confirm denied responses show plans when access is absent
- do not add payment collection yet
- do not add broader conversation context yet

Then update current status after the rollout is confirmed.

## Notes

- Foundation is now in place
- Business modules beyond users are still intentionally small
- Current local Docker stack does not include Nginx; this is intentionally deferred
- VK transport currently validates payload shape, optional callback secret, and normalizes events
- VK transport now hands normalized events into a minimal user-aware application slice
- Users module currently covers only minimal identity persistence and lookup/create
- Access module currently supports either persisted manual grants or active subscriptions with remaining balance
- Access grant issuance is currently manual through a protected internal endpoint
- Subscription issuance is currently manual through a protected internal endpoint
- Application layer currently ends with explicit skipped/denied/accepted request outcomes
- `accepted` at the application outcome level means readiness for the next processing stage
- Outcome consumer currently maps request outcomes to ignored/halted/ready_for_next_stage only
- Current handled branches only log and explicitly finish the flow
- Current denied outward reaction is now delivered through VK `messages.send` when outbound token is configured
- Current denied message also serves as the simple subscription interface
- Current accepted branch now supports a single text-in -> text-out worker path
- Current accepted AI path supports OpenAI, Gemini, and Claude text providers selected via env
- Current accepted AI path now persists minimal accepted text request/response pairs plus token usage
- Current accepted AI path now deducts factual input + output tokens from the user's active subscription
- Current accepted AI path still does not include automated payments, attachments, or broader conversation memory yet
- VK events without actor id are safely ignored by the application handoff
- Do not mix VK transport with payment collection logic yet
- Do not expand into a full AI platform yet
