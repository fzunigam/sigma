# Sigma CLI Finance Tracker — Design

## Status
Approved

## Problem
Sigma needs a professional, CLI-first finance tracker that is fast for daily logging, auditable over time, and structured for long-term maintainability.

## Goals
- Build a local-first CLI finance tracker using Python 3.12 and SQLite.
- Optimize for fast movement entry and clear terminal reporting.
- Preserve historical auditability with an explicit render workflow.
- Establish repository standards (versioning, changelog, architecture docs, ADRs, AGENTS guidance).

## Non-Goals (v1)
- Telegram integration implementation (roadmap only).
- Multi-currency support.
- Automatic scheduled rendering.
- Categories, tags, or advanced analytics.

## Architecture
Sigma v1 uses a layered monolith:
- `domain`: entities and business rules.
- `application`: use cases and orchestration.
- `infrastructure`: SQLite repositories, config, runtime dependencies.
- `interface/cli`: Typer commands and Rich presentation.

The executable command is `sgm`. The default database path is `~/.local/share/sgm/sigma.db`.

## Core Components
- **Accounts**: debit and credit tracking, including available credit/debt views.
- **Transfers/Payments**: balance-moving operations between accounts.
- **Movements**: income and expense logs in CLP integer pesos.
- **Rendering**: periodic net calculation over marked movements.
- **Reports**: balances, marked movement pool, and render history views.

## Data Model (v1)
Planned tables:
- `accounts`: account master data and balance state.
- `movements`: immutable income/expense records.
- `movement_marks`: render eligibility marker state.
- `transfers`: immutable transfer/payment records.
- `render_history`: immutable rendered snapshots.

Amounts are stored as integer CLP pesos only.

## Data Flow
1. User logs a movement; it is marked by default.
2. User can list marked movements at any time.
3. `sgm render run` selects marked movements, computes net (`income - expense`), stores a render snapshot, and unmarks processed rows.
4. Historical movement and render records remain available for auditing.

Transfers are independent transactions that immediately update source and destination balances.

## Behavioral Rules
- Debit/Credit balances are managed by explicit account, transfer/payment, and movement commands.
- Income/expense movements immediately alter account balances.
- Transactions (expenses) cannot be completed if there are insufficient funds or credit available.
- Rendering is manual command execution only in v1.
- CLI assumes a single local user (no auth layer in v1).

## Error Handling
- Typed, explicit domain/application errors.
- No silent fallbacks.
- Non-zero exit codes on command failures.
- Validation for account existence, positive amounts, and transfer constraints.

## Testing Strategy
- Unit tests for domain and application use cases.
- CLI smoke tests for critical command paths.
- SQLite-backed tests for repository behaviors.

## Delivery and Governance
- Semantic Versioning starting at `0.1.0`.
- Keep a Changelog format in `CHANGELOG.md`.
- MIT license.
- Project context scaffolding under `docs/` and `AGENTS.md`.

## Roadmap Notes
- Telegram integration is documented as a future optional input gateway.
- Multi-currency and automatic rendering are deferred to post-v1 decisions.
