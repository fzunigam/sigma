# CLI Usage

Sigma (`sgm`) is designed for speed and clarity. Below is the complete reference for all available commands.

## Quickstart
```bash
# 1. Initialize the system
sgm start

# 2. Add your first account
sgm acc add wallet "Cash Wallet" debit 0

# 3. Log an expense and mark it for rendering
sgm exp 5000 "lunch" yes wallet

# 4. View your status
sgm status

# 5. Render your marked movements
sgm render
```

---

## Core Commands

Daily-use commands for logging data and managing the rendering cycle.

| **Command** | **Arguments** | **Example** | **Description** |
|-|-|-|-|
| `start`| *None* | `sgm start` | Launches the first-run setup wizard. |
| `status`| *None* | `sgm status` | Displays a **rich** table of balances, credit limits, and the current *marked* total. |
| `exp` | `<amount> <desc> {yes\|no} [acc_id]` | `sgm exp 7000 "sushi" yes cc` | Records an **expense**. The `{yes\|no}` choice flags the item for the next render. |
| `inc` | `<amount> <desc> {yes\|no} [acc_id]` | `sgm inc 19000 "pay" no bci` | Records an **income**. The `{yes\|no}` choice flags the item for the next render. |
| `tr` | `<from> <to> <amount>` | `sgm tr bci cc 10000` | Executes a transfer between accounts. |
| `render` | *None* | `sgm render` | Sums all marked movements, logs the result to history, and unmarks all items. |

## Data Management & History

Commands to review past performance and individual logs.

| **Command** | **Arguments** | **Example** | **Description** |
|-|-|-|-|
| `log` | `[limit]` | `sgm log 25` | Lists the most recent movements. (Default: 15). | 
| `history` | *None* | `sgm history` | Displays a table of previous render results with dates and total sums. |
| `delete` | `<id>` | `sgm delete m-23` | Permanently removes a movement (`m-`) or transfer (`t-`) by ID. |

## Account Configuration

Management of the underlying financial structure.

| **Command** | **Arguments** | **Example** | **Description** |
|-|-|-|-|
| `acc list` | `[acc_id]` | `sgm acc list cc` | Detailed view of account metadata. Lists all accounts if `[acc_id]` is omitted. |
| `acc add` | `<id> <name> {debit\|credit} <bal>` | `sgm acc add cc "Santander" credit 0` | Adds a new account with an initial balance. |
| `acc rename`| `<old_id> <new_id>`| `sgm acc rename cc bci` | Updates the unique identifier for an account. |
| `acc set-limit`| `<acc_id> <limit>` | `sgm acc set-limit amex 2000000` | Updates the rolling credit limit (Credit accounts only). |

## System & Integration

Meta-commands for maintenance and configuration.

| **Command** | **Arguments** | **Example** | **Description** |
|-|-|-|-|
| `config` | *None* | `sgm config` | Opens the `sgm` global settings (default accounts). |
| `restore` | *None* | `sgm restore` | Deletes all data and leaves the database empty. Requires confirmation. |
| `update`| *None* | `sgm update` | Checks for a newer version on PyPI and performs an upgrade. |
| `version` | *None* | `sgm version` | Displays current version. |