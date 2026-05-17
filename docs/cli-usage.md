# Sigma CLI Usage Guide

Sigma (`sgm`) is a fast, local-first finance tracker. This guide provides a detailed reference for every command, argument, and core concept.

---

## Core Concepts

### 1. The Rendering Cycle
Unlike traditional trackers, Sigma uses a **Marking & Rendering** workflow:
- **Marking**: When you log an expense (`exp`) or income (`inc`), you decide if it's "marked" for review (`yes` or `no`). Marked items are considered "pending" until verified.
- **Rendering**: Running `sgm render` takes all marked items, calculates their net sum, creates a historical snapshot, and "clears" the marks. This is your audit point.

### 2. Smart Argument Resolution
Sigma is designed for speed. Commands like `exp` and `inc` have optional arguments for `[acc_id]` and `[date]`.
- **Automatic Account**: If you only have one account, you can skip `[acc_id]`.
- **Default Accounts**: Use `sgm config` to set a default account for income/expenses.
- **Date Detection**: If you provide a string that looks like a date (`YYYY-MM-DD`) as the 4th argument, Sigma automatically treats it as the date, even if you skipped the account ID.

---

## Quickstart
```bash
sgm start                           # Setup your first account
sgm acc add cc "Visa" credit 0       # Add a credit card
sgm exp 5000 "Lunch" yes wallet     # Log an expense
sgm status                          # See where you stand
sgm render                          # Close the current cycle
```

---

## Workflow Essentials

### `start`
Launches the interactive setup wizard for first-time users.
- **Syntax**: `sgm start`
- **Details**:
    - Initializes the database and configuration.
    - **Import Option**: Prompts if you'd like to import existing data from a ZIP file or folder containing Sigma's CSV tables.
    - If no import is performed, it guides you through creating your first account.
- **Example**:
  ```bash
  sgm start
  # Choose 'y' to import existing data, or 'n' for manual setup.
  ```

### `status`
Displays a rich table of all accounts, their balances, and the total currently marked for the next render.
- **Syntax**: `sgm status`
- **Details**: For credit accounts, it also shows "Available Credit" based on your limit.

### `render`
Processes all marked movements into a historical snapshot.
- **Syntax**: `sgm render`
- **Example**:
  ```bash
  sgm render
  # Output: Rendered 5 movements. Net amount logged: -12500
  ```

---

## Logging Transactions

### `exp` (Expense)
Records a withdrawal or purchase.
- **Syntax**: `sgm exp <amount> <description> <mark: yes|no> [acc_id] [date]`
- **Examples**:
  ```bash
  sgm exp 12000 "Groceries" yes wallet      # Explicit account
  sgm exp 5000 "Coffee" no                  # Uses default/only account
  sgm exp 45000 "Internet" yes 2023-10-01   # Skip acc_id, use specific date
  ```

### `inc` (Income)
Records a deposit or gain.
- **Syntax**: `sgm inc <amount> <description> <mark: yes|no> [acc_id] [date]`
- **Examples**:
  ```bash
  sgm inc 800000 "Salary" yes bank          # Monthly pay
  sgm inc 5000 "Gift" no wallet             # Small gain, don't mark for render
  ```

### `tr` (Transfer)
Moves money between two accounts. Does not affect net "rendering" totals.
- **Syntax**: `sgm tr <from_acc> <to_acc> <amount> [date]`
- **Example**:
  ```bash
  sgm tr bank wallet 50000                  # ATM withdrawal
  sgm tr wallet cc 100000 2023-11-05        # Paying off credit card
  ```

---

## Exploration & Audit

### `log`
Lists the most recent movements and transfers.
- **Syntax**: `sgm log [limit]`
- **Example**:
  ```bash
  sgm log 10        # Show last 10 entries
  sgm log           # Show last 15 (default)
  ```

### `history`
Shows the results of all previous `render` commands.
- **Syntax**: `sgm history`

### `delete`
Permanently removes a record by its unique ID.
- **Syntax**: `sgm delete <unique_id>`
- **Example**:
  ```bash
  sgm log           # Find the ID, e.g., m-15
  sgm delete m-15   # Delete movement #15
  ```

---

## Account Management

### `acc list`
Shows details for one or all accounts.
- **Syntax**: `sgm acc list [acc_id]`
- **Example**:
  ```bash
  sgm acc list      # List all IDs, names, and balances
  sgm acc list cc   # Show full metadata for the 'cc' account
  ```

### `acc add`
Creates a new account.
- **Syntax**: `sgm acc add <id> <name> <type: debit|credit> <initial_balance>`
- **Example**:
  ```bash
  sgm acc add bci "Main Bank" debit 500000
  sgm acc add amex "Travel Card" credit 0
  ```

### `acc rename`
Changes an account's unique identifier.
- **Syntax**: `sgm acc rename <old_id> <new_id>`

### `acc set-limit`
Updates the credit limit for credit-type accounts.
- **Syntax**: `sgm acc set-limit <acc_id> <limit>`

### `acc delete`
Deletes an account. **Safety feature**: History is preserved by moving it to a hidden "ghost" account.
- **Syntax**: `sgm acc delete <acc_id>`

---

## System & Maintenance

### `config`
Interactive prompt to set your default income and expense accounts for faster logging.
- **Syntax**: `sgm config`

### `export`
Exports all database tables into a ZIP file containing CSV files. Useful for backups or external analysis.
- **Syntax**: `sgm export [--output <path>]`
- **Details**: 
    - Defaults to your `Downloads` folder (or home directory if Downloads is missing).
    - The ZIP file is named `sigma_export_YYYYMMDD_HHMMSS.zip`.
    - Includes tables: `accounts`, `movements`, `movement_marks`, `transfers`, and `render_history`.
- **Example**:
    ```bash
    sgm export                      # Saves to Downloads
    sgm export -o ~/backups/my_data.zip  # Saves to a specific path
    ```

### `restore`
**DANGER**: Completely wipes the database. Requires typing 'RESTORE' to confirm.
- **Syntax**: `sgm restore`

### `update`
Checks for and installs the latest version of Sigma from PyPI.
- **Syntax**: `sgm update`

### `version`
Displays current version information.
- **Syntax**: `sgm version`
