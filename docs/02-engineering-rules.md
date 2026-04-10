# Engineering Rules

## General principle

Код должен быть production-oriented, простым, читаемым и пригодным для продолжения разработки другими людьми и AI-инструментами.

Не допускается demo-style реализация в критичных частях проекта.

## Stack rules

- Use Python 3.12
- Use FastAPI
- Use Pydantic v2
- Use SQLAlchemy 2.x style only
- Use Alembic for migrations
- Use PostgreSQL as primary DB
- Use Redis for queue/support infrastructure
- Use Dramatiq for background tasks

## Architecture rules

- Keep architecture as a modular monolith
- Keep route handlers thin
- Put business logic into service layer
- Put persistence logic into repository layer
- Wrap external integrations in adapters/providers
- Do not place provider-specific logic into routes
- Do not place payment logic into VK transport layer
- Do not place access logic directly into webhook handlers
- Keep domain boundaries explicit and clean

## Code quality rules

- Use type hints for public functions and service methods
- Avoid god classes and god services
- Avoid giant files when logic can be split cleanly
- Avoid circular imports
- Avoid magic constants
- Avoid duplicate schemas and duplicate logic
- Prefer explicit code over clever code
- Prefer simple maintainable implementations over overengineering
- Keep changes scoped to the current task

## Forbidden patterns

- No business logic in routes
- No direct SQL inside handlers
- No direct calls to AI providers from unrelated layers
- No direct payment side effects from transport layer
- No in-memory state for balances, subscriptions, or payments
- No hardcoded secrets
- No hardcoded provider credentials
- No silent exception swallowing
- No fake payment confirmation logic
- No granting access based only on redirect/success page
- No unrelated refactoring in feature tasks unless explicitly requested

## Payments rules

- Payment processing must be idempotent
- Every webhook must be validated
- Repeated webhook delivery must not duplicate side effects
- Access/subscription/credits must be granted only through service layer
- Raw payment events should be persisted when relevant
- Payment status transitions should be explicit and controlled

## AI integration rules

- AI providers must be accessed only through adapters
- Normalize provider errors
- Normalize usage/cost data when possible
- Do not tie product logic too tightly to one provider
- Keep provider-switching feasible
- Do not leak provider-specific behavior into unrelated modules unless necessary

## VK rules

- Treat VK as transport layer
- Validate incoming payloads
- Normalize VK events before passing deeper into the app
- Do not mix VK transport with business decisions

## Attachments and files

- Validate mime type
- Validate file size
- Do not trust external filenames
- Do not pass unvalidated files directly into AI flows
- Clean up temporary files when applicable

## Git workflow rules

- Work in small scoped branches
- Prefer small coherent commits
- One task should change a limited and understandable set of files
- Do not mix feature implementation with unrelated cleanup
- Do not do broad refactors without explicit reason
- After completing a meaningful step, update current project status
- Commit messages must be clear and specific

## Task execution rules for AI-assisted work

For each task:

1. First analyze the task
2. Identify dependencies
3. Identify risks and edge cases
4. Propose a small implementation plan
5. Implement only the scoped slice
6. Suggest a commit message
7. Indicate what should be updated in current-status

## Testing rules

- Write practical tests for critical flows
- Focus on service-layer behavior and important scenarios
- Cover happy paths and key edge cases
- Prioritize tests for:
  - billing
  - access control
  - wallet logic
  - idempotency
  - provider boundaries
- Do not overengineer the test suite
- Do not chase artificial coverage numbers
- Prefer clear maintainable tests over overly abstract tests

## Definition of acceptable completion

A task is considered complete when:

- code fits the current architecture
- code is scoped to the task
- critical scenarios are covered by reasonable tests where needed
- migrations are created when schema changes
- no obvious architectural violations are introduced
- current-status is updated
