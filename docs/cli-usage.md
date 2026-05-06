# CLI Usage

Sigma (`sgm`) is designed for speed and clarity. Below is the complete reference for all available commands.

## Quickstart
```bash
EMPTY
```

---

## Core Commands

Daily-use commands for logging data and managing the rendering cycle.

| **Command** | **Arguments** | **Example** | **Description** |
|-|-|-|-|
| `start`| *None* | `sgm start` | First-run setup wizard. |
| `status`| *None* | `sgm status` | Displays a **rich** table of all account balances, credit limits, and the current *marked* total pending render. |
| `exp` | `<amount> <description> {yes\|no} [account_id]` | `sgm exp 7000 "sushi" yes cc` | Records an expense. The {yes|no} choice flags the item for the next render. `[account_id]` is optional, you can select the default account in `sgm config`|
| `inc` | `<amount> <description> [marked]` | `sgm inc 19000 "car wash" no` | Records an income. The {yes|no} choice flags the item for the next render. `[account_id]` is optional, you can select the default account in `sgm config`|
| `tr` | `<from> <to> <amount>` | `sgm cc cr 10000`| Executes a transfer. |
| `render` | *None* | `sgm render` | Sums marked movements, saves the result to history, and unmarks all items. |

## Data Management & History

Commands to review past performance and individual logs.

| **Command** | **Arguments** | **Example** | **Description** |
|-|-|-|-|
| `log` | `[limit]` | `sgm log 25` | Lists the most recent movements. (Default: 15). | 
| `history` | *None* | `sgm history`| Displays a table of previous render results. Shows dates and total sums.|
| `delete` | `<id>` | `sgm delete m23` | Removes a specific movement or transfer by ID. |
| `edit`| `<id>` | `sgm edit 7` | Interactive command to modify the amount, description, or account of an existing entry. |

## Account Configuration

Management of the underlying financial structure.

| **Command** | **Arguments** | **Example** | **Description** |
|-|-|-|-|
| `acc list` | `<account_id>` | `sgm acc list cc` | A detailed view of account metadata. |
| `acc add` | `<account_id> <name> <type> <initial_balance>` | `sgm acc add cc "Cuenta Corriente Santander" 120000` | Add an account. |
| `acc rename`| `<old> <new>`| `sgm acc cc cc2`| Change account identifier |
| `acc set-limit`| `<account_id> <limit>` | `sgm acc set-limit worldmember 2000000`| Updates the rolling limit for credit cards. |

## System & Integration

Meta-commands for maintenance and the Telegram bridge.

| **Command** | **Arguments** | **Example** | **Description** |
|-|-|-|-|
| `bot start` | *None* | `sgm bot start` | Launches the Telegram bot setup |
| `config` | *None* | `sgm config` | Open `sgm` settings |
| `update`| *None* | `sgm update`| Checks GitHub for a newer version and updates if necessary.|
| `version` | *None* | `sgm version`| Displays current version, database path, and last update check. | 