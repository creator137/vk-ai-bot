# Current Status

## Project state

Foundation bootstrap, minimal VK transport bootstrap, minimal users bootstrap, VK-to-users handoff, minimal access decision boundary, minimal request outcome slice, minimal outcome consumer slice, minimal denied/accepted branch handling, minimal outward reaction slice, minimal access grant issuance slice, minimal VK outward delivery slice, minimal AI bootstrap for accepted path, minimal accepted request persistence slice, minimal subscription/token accounting slice, minimal dialogue memory slice, and minimal Robokassa payment bootstrap implemented.

## Current phase

First minimal Robokassa payment bootstrap ready. Repository prepared for rollout and verification of payment initiation plus callback confirmation.

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
- Minimal accepted dialogue memory added:
  - recent accepted request/response pairs are now reused as short dialogue context
  - accepted worker now sends recent dialogue history to the AI provider before the new user message
- Minimal Robokassa payment bootstrap added
- Subscription payment model added
- Subscription payments migration added
- Internal protected Robokassa payment initiation endpoint added
- Robokassa payment link generation added
- Robokassa ResultURL callback verification added
- Robokassa SuccessURL verification added
- Successful Robokassa ResultURL confirmation now activates the selected subscription automatically
- Plan preview in VK can now include a Robokassa payment link when payment settings are configured
- Robokassa tests added

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

Roll out and verify the current Robokassa-aware payment slice:

1. apply the latest migration on the server
2. configure `APP_BASE_URL`, `ROBOKASSA_MERCHANT_LOGIN`, `ROBOKASSA_PASSWORD1`, `ROBOKASSA_PASSWORD2`
3. set `ResultURL`, `SuccessURL`, and `FailURL` in Robokassa technical settings
4. run at least one test payment and one real payment through Robokassa
5. confirm `ResultURL` returns `OK{InvId}` and activates the correct subscription

## Recommended next branch

`feat/robokassa-rollout-verification`

## Recommended next task for AI

Complete rollout and verification of the existing payment slice:

- deploy the latest migration and api/worker code
- configure Robokassa credentials and callback URLs
- confirm internal payment init returns a valid Robokassa payment URL
- confirm `ResultURL` activates the correct subscription after a paid test invoice
- confirm VK tariff preview shows payment links when Robokassa is configured
- keep full billing dashboard, refunds, and recurring payments out of scope for now

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
- Current accepted AI path now includes short dialogue memory from recent accepted exchanges
- Current payment path now supports Robokassa payment link generation and callback confirmation
- Current payment path still does not include a billing cabinet, refunds, or recurring charges yet
- VK events without actor id are safely ignored by the application handoff
- Do not expand into a full AI platform yet
