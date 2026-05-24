# Credit Card Transfer Validation Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Disallow transfers from credit cards, and prevent transfers to credit cards that would result in a negative balance (overpayment), in both the CLI and web interface.

**Architecture:** Implement core validations in `create_transfer` inside `src/sgm/infrastructure/database.py`, return appropriate HTTP 400 errors from FastAPI, filter select options, and add validation checks in the Next.js React frontend.

**Tech Stack:** Python 3.12, SQLite, Next.js, React, TypeScript.

---

### Task 1: Add validation rules in backend database layer

**Files:**
- Modify: `src/sgm/infrastructure/database.py:479-541`

**Step 1: Code modification**
In `src/sgm/infrastructure/database.py`, modify the `create_transfer` function:
1. Reject transfers from credit card accounts by checking if `from_type == "credit"`.
2. Reject transfers to credit card accounts if `to_balance - amount < 0`.

Code snippet:
```python
        # Get from_account
        cursor.execute("SELECT type, balance, credit_limit FROM accounts WHERE id = ? AND deleted_at IS NULL", (from_account,))
        from_row = cursor.fetchone()
        if not from_row:
            raise ValueError(f"Account with ID '{from_account}' does not exist.")
        from_type, from_balance, from_limit = from_row
        
        if from_type == "credit":
            raise ValueError("Transfers from credit cards are not allowed.")
```

And update deposit check:
```python
        # Deposit into to_account
        if to_type == "debit":
            new_to_balance = to_balance + amount
        elif to_type == "credit":
            new_to_balance = to_balance - amount
            if new_to_balance < 0:
                raise ValueError(f"Transfer would leave credit card '{to_account}' with a negative balance. Current balance: {to_balance}, Transfer amount: {amount}")
        else:
            raise ValueError(f"Unknown account type '{to_type}'")
```

---

### Task 2: Add CLI Smoke Tests

**Files:**
- Modify: `tests/smoke/test_cli_tr.py`

**Step 1: Write tests**
Add the following tests to `tests/smoke/test_cli_tr.py`:

```python
def test_tr_from_credit_card_disallowed(clean_db):
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    runner.invoke(app, ["acc", "add", "cc", "Visa", "credit", "500000"])
    
    result = runner.invoke(app, ["tr", "cc", "wallet", "3000"])
    assert result.exit_code == 1
    assert "Error: Transfers from credit cards are not allowed." in result.output

def test_tr_to_credit_card_negative_balance_disallowed(clean_db):
    runner.invoke(app, ["acc", "add", "wallet", "Cash", "debit", "10000"])
    # Credit card starts with 0 balance (0 spent)
    runner.invoke(app, ["acc", "add", "cc", "Visa", "credit", "500000"])
    
    # Try to pay 3000 to credit card, which has 0 debt -> would leave negative balance (-3000)
    result = runner.invoke(app, ["tr", "wallet", "cc", "3000"])
    assert result.exit_code == 1
    assert "Error: Transfer would leave credit card 'cc' with a negative balance." in result.output
```

**Step 2: Run test to verify it passes**
Run: `python3 -m pytest tests/smoke/test_cli_tr.py -v`
Expected: All tests pass.

---

### Task 3: Add Web Server Integration Tests

**Files:**
- Modify: `tests/integration/test_web_server.py`

**Step 1: Write tests**
Add a test in `tests/integration/test_web_server.py` to assert FastAPI returns HTTP 400 for these invalid transfers:

```python
def test_web_transfer_credit_card_restrictions(monkeypatch, tmp_path):
    from sgm.infrastructure.database import init_db
    db_file = tmp_path / "test_sigma.db"
    monkeypatch.setattr("sgm.infrastructure.database.get_db_path", lambda: db_file)
    init_db(db_file)
    
    from sgm.interface.web.server import app
    client = TestClient(app)
    
    # Create accounts
    client.post("/api/v1/accounts", json={"id": "wallet", "name": "Cash", "type": "debit", "initial_balance": 10000})
    client.post("/api/v1/accounts", json={"id": "cc", "name": "Visa", "type": "credit", "initial_balance": 0, "credit_limit": 500000})
    
    # 1. Try transferring from credit card
    response = client.post("/api/v1/transactions/transfer", json={
        "from_account": "cc",
        "to_account": "wallet",
        "amount": 1000
    })
    assert response.status_code == 400
    assert "Transfers from credit cards are not allowed." in response.json()["detail"]
    
    # 2. Try transferring to credit card leaving negative balance
    response = client.post("/api/v1/transactions/transfer", json={
        "from_account": "wallet",
        "to_account": "cc",
        "amount": 1000
    })
    assert response.status_code == 400
    assert "Transfer would leave credit card 'cc' with a negative balance." in response.json()["detail"]
```

**Step 2: Run test to verify it passes**
Run: `python3 -m pytest tests/integration/test_web_server.py -v`
Expected: All tests pass.

---

### Task 4: Implement Web Frontend Validations and UI Filters

**Files:**
- Modify: `web/src/app/page.tsx`

**Step 1: Modify Account dropdown filtering**
In `web/src/app/page.tsx`, filter the source ("From Account") dropdown so credit cards are not option choices when the transaction type is a transfer:

```tsx
                    <select
                      id="tx-account"
                      value={txAccount}
                      onChange={(e) => setTxAccount(e.target.value)}
                      className="bg-background border border-border text-foreground rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-ring w-full"
                    >
                      {accounts
                        .filter((acc) => txType !== 'transfer' || acc.type !== 'credit')
                        .map((acc) => (
                          <option key={acc.id} value={acc.id}>{acc.name} ({acc.id})</option>
                        ))
                      }
                    </select>
```

**Step 2: Modify frontend submission validations**
In `handleLogTransaction` submit handler:
1. Fix the typo/bug `Source and destination accounts must be identical.` to `Source and destination accounts must be different.`.
2. Add validations for credit card source and negative balance destination.

```typescript
      } else {
        if (!txAccount || !txTransferTo) {
          setTxError('Both source and destination accounts are required.');
          setIsSubmitting(false);
          return;
        }
        if (txAccount === txTransferTo) {
          setTxError('Source and destination accounts must be different.');
          setIsSubmitting(false);
          return;
        }
        
        const fromAcc = accounts.find(a => a.id === txAccount);
        if (fromAcc && fromAcc.type === 'credit') {
          setTxError('Transfers from credit cards are not allowed.');
          setIsSubmitting(false);
          return;
        }
        
        const toAcc = accounts.find(a => a.id === txTransferTo);
        if (toAcc && toAcc.type === 'credit') {
          if (toAcc.balance - amountNum < 0) {
            setTxError(`Transfer would leave credit card '${txTransferTo}' with a negative balance. Current balance: ${toAcc.balance}, Transfer amount: ${amountNum}`);
            setIsSubmitting(false);
            return;
          }
        }
```

---
