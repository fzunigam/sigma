# ADR 0001: Layered Monolith for Sigma v1

## Status
Accepted

## Context
Sigma needs a maintainable CLI-first architecture that can ship quickly for personal finance tracking while leaving room for future integrations (such as Telegram input) without overengineering v1.

Alternatives considered:
- Event-oriented core from day one.
- SQL-first minimal script architecture.

## Decision
Adopt a layered monolith in Python 3.12 with SQLite, Typer, and Rich:
- Domain/application layers for business logic separation.
- Infrastructure layer for persistence and external concerns.
- CLI interface layer for commands and presentation.

Amounts are stored as integer CLP pesos, rendering is manual in v1, and movements directly update account balances, ensuring transactions cannot proceed without sufficient funds.

## Consequences
- Faster delivery with clear boundaries and low operational complexity.
- Straightforward unit testing of domain and application services.
- Future integrations can be added via adapters without rewriting core logic.
- Some future extensibility patterns (events/plugins) are deferred until justified.
