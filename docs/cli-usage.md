# CLI Usage

Sigma (`sgm`) is designed for speed and clarity. Below is the complete reference for all available commands.

## Quickstart
```bash
pip install sigma-finance
sgm start
sgm income cash 100000 "Salary"
sgm expense cash 12000 "Groceries"
sgm pending
sgm render
sgm balances
```

---

## Core Commands

### `sgm start`
First-run setup wizard. Prompts for a display name and initializes the configuration file at `~/.config/sgm/config.toml`.

### `sgm income <account> <amount> "<description>"`
Logs an income movement to a specific account. The movement is "marked" by default, meaning it will be included in the next `render` operation.
- **Example:** `sgm income bank 50000 "Dividend"`

### `sgm expense <account> <amount> "<description>"`
Logs an expense movement from a specific account. Like income, it is "marked" by default.
- **Example:** `sgm expense cash 3500 "Coffee"`

### `sgm pending`
Displays a table of all "marked" movements that are waiting to be processed by a render.

### `sgm render [snapshot_id]`
Processes all marked movements, calculates the net total, and saves an immutable snapshot to the history. Once rendered, movements are "unmarked" and will not appear in `pending` again.
- **snapshot_id:** (Optional) A custom identifier for the snapshot.

### `sgm balances`
Shows a table of all account balances and the total net balance of the system.

---

## Account Management (`sgm account`)

### `sgm account create <id> <name> <kind> <balance>`
Creates a new account in the system.
- **id:** Short unique identifier (e.g., `cash`, `visa`).
- **name:** Descriptive name (e.g., "Main Wallet").
- **kind:** `debit` or `credit`.
- **balance:** Initial balance in integer CLP.

### `sgm account list`
Lists all registered accounts with their ID, name, kind, and current balance.

---

## Movement Management (`sgm movement`)

### `sgm movement add <id> <account_id> "<description>" <amount> <type>`
Manually adds a movement with a specific ID.
- **id:** Unique identifier for the movement.
- **type:** `income` or `expense`.

### `sgm movement list-marked`
Technical view of all marked movements.

---

## Transfer Management (`sgm transfer`)

### `sgm transfer move <id> <source_account_id> <target_account_id> <amount> --created-at <iso-timestamp>`
Records a transfer of funds between two accounts.
- **--created-at:** Required ISO-8601 timestamp (e.g., `2026-05-05T12:00:00Z`).

---

## Reporting (`sgm report`)

### `sgm report balances`
Alias for `sgm balances`.

### `sgm report render-history`
Displays a history of all rendered snapshots, including income total, expense total, and net for each period.
