# Sigma (`sgm`)

**Sigma** is a fast, CLI-first personal finance tracker designed for local use. It focuses on rapid transaction logging, simple account management, and auditable snapshots through a unique "rendering" cycle.

[![PyPI version](https://img.shields.io/pypi/v/sigma-finance.svg)](https://pypi.org/project/sigma-finance/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Build Status](https://github.com/fzunigam/sigma/actions/workflows/ci.yml/badge.svg)](https://github.com/fzunigam/sigma/actions)

## Why Sigma?

Most finance trackers are either too complex or require too many clicks. Sigma is built for users who live in the terminal and want to:

*   **Log quickly**: Record expenses, income, and transfers with minimal keystrokes.
*   **Audit with ease**: Use the `render` command to verify and clear your pending movements into historical snapshots.
*   **Stay local**: Your data stays on your machine in a lightweight SQLite database.
*   **See the big picture**: Rich terminal tables provide instant clarity on your balances and credit availability.

---

## Features

- ⚡ **Fast Logging**: Simple commands for `exp` (expense), `inc` (income), and `tr` (transfer).
- 🏦 **Account Management**: Support for both **Debit** and **Credit** accounts with rolling credit limit tracking.
- 🔄 **Rendering Cycle**: Mark movements for review and "render" them into your history once verified.
- 📊 **Rich Interface**: Beautifully formatted tables powered by [Rich](https://github.com/Textualize/rich).
- 📜 **Audit Log**: Full history of movements and render snapshots.
- 🛠️ **Built-in Setup**: Interactive first-run wizard to get you started in seconds.

---

## Installation

Sigma requires **Python 3.10** or higher.

```bash
pip install sigma-finance
```

### First-run Setup

Once installed, initialize your database and create your first account:

```bash
sgm start
```

---

## Usage

### Core Workflow

1.  **Check your status**:
    ```bash
    sgm status
    ```
2.  **Log an expense**:
    ```bash
    # Usage: sgm exp <amount> <description> <mark_for_render: yes|no> [account_id]
    sgm exp 5000 "Lunch" yes wallet
    ```
3.  **Log income**:
    ```bash
    sgm inc 2500000 "Salary" no bci
    ```
4.  **Transfer between accounts**:
    ```bash
    sgm tr bci wallet 50000
    ```
5.  **Render marked movements**:
    ```bash
    # Sums marked items, logs to history, and clears marks.
    sgm render
    ```

### Command Reference

| Command | Description |
| :--- | :--- |
| `sgm status` | Show balances, credit limits, and marked totals. |
| `sgm log [limit]` | List recent movements (default: 15). |
| `sgm history` | View previous render results. |
| `sgm acc list` | List all accounts and their details. |
| `sgm config` | Configure default accounts for faster logging. |
| `sgm export` | Export all data to a ZIP file with CSV tables. |
| `sgm delete <id>` | Remove a record by its unique ID (e.g., `m-1`). |

For a complete reference of all available commands and their arguments, please refer to the [Detailed CLI Usage Guide](docs/cli-usage.md).

---

## Development

We use `Makefile` for common development tasks.

```bash
# Clone the repository
git clone https://github.com/fzunigam/sigma
cd sigma

# Install in editable mode with dev dependencies
make install

# Run tests
make test

# Run linter
make lint
```

---

## Project Structure

- `src/sgm/`: Core package logic.
  - `cli.py`: Typer-based CLI definition.
  - `infrastructure/`: Database (SQLite) and config management.
  - `interface/`: Terminal banners and UI elements.
- `docs/`: Detailed documentation and architecture plans.
- `tests/`: Smoke tests for CLI flows.

---

## License

Sigma is licensed under the [MIT License](LICENSE).

---

## Acknowledgments

- [Typer](https://typer.tiangolo.com/) for the CLI framework.
- [Rich](https://github.com/Textualize/rich) for the beautiful terminal output.
