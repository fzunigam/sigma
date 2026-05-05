# Architecture Overview

## Purpose
Sigma is a local-first CLI finance tracker for personal use. It optimizes fast movement logging and periodic render snapshots for auditability.

## System Design
Sigma v1 uses a layered monolith:
- **Domain layer**: entities and business invariants (accounts, movements, transfers, render snapshot).
- **Application layer**: use cases that orchestrate domain rules.
- **Infrastructure layer**: SQLite persistence, filesystem/config access, and runtime adapters.
- **CLI interface layer**: Typer commands and Rich terminal rendering.

## Data Storage
- SQLite database at `~/.local/share/sgm/sigma.db` by default.
- CLP amounts stored as integer pesos.
- Core records are immutable where possible (movements, transfers, render history).

## Core Flow
1. User logs movements, which are marked by default.
2. User runs `sgm render run` manually.
3. The app computes net (`income - expense`) for marked movements.
4. The app persists a render snapshot in `render_history` and unmarks processed movements.
5. Historical data remains queryable for audit purposes.

## Boundaries and Constraints (v1)
- Single local user CLI.
- Manual rendering only (no scheduler in v1).
- No Telegram implementation yet (roadmap item).
- No multi-currency, categories, or tags in v1.
