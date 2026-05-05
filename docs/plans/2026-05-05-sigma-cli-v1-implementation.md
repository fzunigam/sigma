# Sigma CLI v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build Sigma v1 as a production-quality, local-first CLI finance tracker with auditable rendering workflow and professional repository standards.

**Architecture:** Implement a layered monolith (`domain`, `application`, `infrastructure`, `interface/cli`) with SQLite persistence and Typer/Rich terminal UX. Keep v1 focused on CLP integer amounts, manual render execution, and explicit balance-changing operations (accounts/transfers) while preserving immutable financial history.

**Tech Stack:** Python 3.12, SQLite, Typer, Rich, pytest, ruff

---

Skill references: @superpowers:executing-plans, @superpowers:subagent-driven-development

### Task 1: Bootstrap package, CLI entrypoint, and test tooling

**Files:**
- Create: `pyproject.toml`
- Create: `src/sgm/__init__.py`
- Create: `src/sgm/cli.py`
- Create: `tests/smoke/test_cli_help.py`

**Step 1: Write the failing test**

```python
# tests/smoke/test_cli_help.py
from typer.testing import CliRunner
from sgm.cli import app


def test_cli_help_renders():
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Sigma" in result.stdout
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_help.py -v`  
Expected: FAIL with `ModuleNotFoundError: No module named 'sgm'`

**Step 3: Write minimal implementation**

```toml
# pyproject.toml (minimal)
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "sgm"
version = "0.1.0"
description = "Sigma CLI finance tracker"
requires-python = ">=3.12"
dependencies = ["typer>=0.12.3", "rich>=13.7.1"]

[project.optional-dependencies]
dev = ["pytest>=8.2.0", "ruff>=0.4.0"]

[project.scripts]
sgm = "sgm.cli:app"
```

```python
# src/sgm/cli.py
import typer

app = typer.Typer(help="Sigma CLI finance tracker")
```

```python
# src/sgm/__init__.py
__all__ = ["__version__"]
__version__ = "0.1.0"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_help.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add pyproject.toml src/sgm/__init__.py src/sgm/cli.py tests/smoke/test_cli_help.py
git commit -m "chore: bootstrap Sigma package and CLI entrypoint"
```

### Task 2: Add core domain errors and CLP amount value object

**Files:**
- Create: `src/sgm/domain/errors.py`
- Create: `src/sgm/domain/value_objects.py`
- Create: `tests/unit/domain/test_amount.py`

**Step 1: Write the failing test**

```python
import pytest
from sgm.domain.value_objects import CLPAmount
from sgm.domain.errors import DomainValidationError


def test_clp_amount_accepts_positive_int():
    assert CLPAmount(1500).value == 1500


def test_clp_amount_rejects_negative():
    with pytest.raises(DomainValidationError):
        CLPAmount(-1)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/domain/test_amount.py -v`  
Expected: FAIL with import or validation implementation errors

**Step 3: Write minimal implementation**

```python
# src/sgm/domain/errors.py
class DomainValidationError(ValueError):
    """Raised when a domain invariant is violated."""
```

```python
# src/sgm/domain/value_objects.py
from dataclasses import dataclass
from .errors import DomainValidationError


@dataclass(frozen=True)
class CLPAmount:
    value: int

    def __post_init__(self) -> None:
        if not isinstance(self.value, int) or self.value <= 0:
            raise DomainValidationError("CLP amount must be a positive integer")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/domain/test_amount.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/domain/errors.py src/sgm/domain/value_objects.py tests/unit/domain/test_amount.py
git commit -m "feat: add CLP amount domain value object"
```

### Task 3: Implement account entities and transfer behavior

**Files:**
- Create: `src/sgm/domain/accounts.py`
- Create: `tests/unit/domain/test_accounts.py`

**Step 1: Write the failing test**

```python
import pytest
from sgm.domain.accounts import Account, AccountType, transfer
from sgm.domain.errors import DomainValidationError


def test_transfer_updates_balances():
    src = Account(id="a1", name="Checking", kind=AccountType.DEBIT, balance=10000)
    dst = Account(id="a2", name="Wallet", kind=AccountType.DEBIT, balance=1000)
    transfer(src, dst, 2500)
    assert src.balance == 7500
    assert dst.balance == 3500


def test_transfer_rejects_insufficient_balance():
    src = Account(id="a1", name="Checking", kind=AccountType.DEBIT, balance=100)
    dst = Account(id="a2", name="Wallet", kind=AccountType.DEBIT, balance=0)
    with pytest.raises(DomainValidationError):
        transfer(src, dst, 200)
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/domain/test_accounts.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/sgm/domain/accounts.py
from dataclasses import dataclass
from enum import Enum
from .errors import DomainValidationError


class AccountType(str, Enum):
    DEBIT = "debit"
    CREDIT = "credit"


@dataclass
class Account:
    id: str
    name: str
    kind: AccountType
    balance: int


def transfer(source: Account, target: Account, amount: int) -> None:
    if amount <= 0:
        raise DomainValidationError("Transfer amount must be positive")
    if source.balance < amount:
        raise DomainValidationError("Insufficient balance")
    source.balance -= amount
    target.balance += amount
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/domain/test_accounts.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/domain/accounts.py tests/unit/domain/test_accounts.py
git commit -m "feat: implement account transfer domain logic"
```

### Task 4: Implement movement logging and default mark behavior

**Files:**
- Create: `src/sgm/domain/movements.py`
- Create: `tests/unit/domain/test_movements.py`

**Step 1: Write the failing test**

```python
from sgm.domain.movements import Movement, MovementType


def test_new_movement_is_marked_by_default():
    m = Movement.new("Salary", 100000, MovementType.INCOME, "a1")
    assert m.marked is True
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/domain/test_movements.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/sgm/domain/movements.py
from dataclasses import dataclass
from enum import Enum


class MovementType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"


@dataclass
class Movement:
    description: str
    amount: int
    type: MovementType
    account_id: str
    marked: bool

    @classmethod
    def new(cls, description: str, amount: int, type: MovementType, account_id: str) -> "Movement":
        return cls(description=description, amount=amount, type=type, account_id=account_id, marked=True)
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/domain/test_movements.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/domain/movements.py tests/unit/domain/test_movements.py
git commit -m "feat: add movement domain model with default marking"
```

### Task 5: Implement render use case with immutable render history output

**Files:**
- Create: `src/sgm/application/render.py`
- Create: `tests/unit/application/test_render_use_case.py`

**Step 1: Write the failing test**

```python
from sgm.application.render import render_marked_movements


def test_render_computes_net_and_unmarks():
    movements = [
        {"id": "m1", "type": "income", "amount": 1000, "marked": True},
        {"id": "m2", "type": "expense", "amount": 300, "marked": True},
    ]
    snapshot, processed_ids = render_marked_movements(movements)
    assert snapshot["net"] == 700
    assert processed_ids == ["m1", "m2"]
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/application/test_render_use_case.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/sgm/application/render.py
from datetime import UTC, datetime


def render_marked_movements(movements: list[dict]) -> tuple[dict, list[str]]:
    marked = [m for m in movements if m["marked"]]
    income = sum(m["amount"] for m in marked if m["type"] == "income")
    expense = sum(m["amount"] for m in marked if m["type"] == "expense")
    snapshot = {
        "rendered_at": datetime.now(UTC).isoformat(),
        "income_total": income,
        "expense_total": expense,
        "net": income - expense,
        "count": len(marked),
    }
    return snapshot, [m["id"] for m in marked]
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/application/test_render_use_case.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/application/render.py tests/unit/application/test_render_use_case.py
git commit -m "feat: implement render use case net calculation"
```

### Task 6: Add SQLite schema bootstrap and repositories

**Files:**
- Create: `src/sgm/infrastructure/db.py`
- Create: `src/sgm/infrastructure/repositories.py`
- Create: `tests/integration/test_sqlite_repositories.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
from sgm.infrastructure.db import init_db


def test_init_db_creates_tables(tmp_path: Path):
    db_path = tmp_path / "sigma.db"
    conn = init_db(db_path)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='accounts'")
    assert cur.fetchone() is not None
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/integration/test_sqlite_repositories.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/sgm/infrastructure/db.py
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  kind TEXT NOT NULL,
  balance INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS movements (
  id TEXT PRIMARY KEY,
  description TEXT NOT NULL,
  amount INTEGER NOT NULL,
  type TEXT NOT NULL,
  account_id TEXT NOT NULL,
  marked INTEGER NOT NULL
);
CREATE TABLE IF NOT EXISTS transfers (
  id TEXT PRIMARY KEY,
  source_account_id TEXT NOT NULL,
  target_account_id TEXT NOT NULL,
  amount INTEGER NOT NULL,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS render_history (
  id TEXT PRIMARY KEY,
  rendered_at TEXT NOT NULL,
  income_total INTEGER NOT NULL,
  expense_total INTEGER NOT NULL,
  net INTEGER NOT NULL,
  count INTEGER NOT NULL
);
"""


def init_db(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA)
    return conn
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/integration/test_sqlite_repositories.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/infrastructure/db.py src/sgm/infrastructure/repositories.py tests/integration/test_sqlite_repositories.py
git commit -m "feat: add SQLite schema bootstrap and repositories"
```

### Task 7: Wire CLI commands for core workflows

**Files:**
- Modify: `src/sgm/cli.py`
- Create: `src/sgm/interface/formatting.py`
- Test: `tests/smoke/test_cli_workflows.py`

**Step 1: Write the failing test**

```python
from typer.testing import CliRunner
from sgm.cli import app


def test_render_command_exists():
    result = CliRunner().invoke(app, ["render", "--help"])
    assert result.exit_code == 0
    assert "run" in result.stdout
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/smoke/test_cli_workflows.py -v`  
Expected: FAIL (missing subcommands)

**Step 3: Write minimal implementation**

```python
# src/sgm/cli.py (shape)
import typer

app = typer.Typer(help="Sigma CLI finance tracker")
account_app = typer.Typer()
movement_app = typer.Typer()
transfer_app = typer.Typer()
render_app = typer.Typer()
report_app = typer.Typer()

@render_app.command("run")
def render_run() -> None:
    typer.echo("Render completed")

app.add_typer(account_app, name="account")
app.add_typer(movement_app, name="movement")
app.add_typer(transfer_app, name="transfer")
app.add_typer(render_app, name="render")
app.add_typer(report_app, name="report")
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/smoke/test_cli_workflows.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/cli.py src/sgm/interface/formatting.py tests/smoke/test_cli_workflows.py
git commit -m "feat: add core CLI command groups"
```

### Task 8: Add config defaults for database location and app wiring

**Files:**
- Create: `src/sgm/infrastructure/config.py`
- Modify: `src/sgm/cli.py`
- Test: `tests/unit/infrastructure/test_config.py`

**Step 1: Write the failing test**

```python
from pathlib import Path
from sgm.infrastructure.config import default_db_path


def test_default_db_path_points_to_local_share():
    path = default_db_path()
    assert str(path).endswith(".local/share/sgm/sigma.db")
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest tests/unit/infrastructure/test_config.py -v`  
Expected: FAIL

**Step 3: Write minimal implementation**

```python
# src/sgm/infrastructure/config.py
from pathlib import Path


def default_db_path() -> Path:
    return Path.home() / ".local" / "share" / "sgm" / "sigma.db"
```

**Step 4: Run test to verify it passes**

Run: `python -m pytest tests/unit/infrastructure/test_config.py -v`  
Expected: PASS

**Step 5: Commit**

```bash
git add src/sgm/infrastructure/config.py src/sgm/cli.py tests/unit/infrastructure/test_config.py
git commit -m "feat: add default database configuration"
```

### Task 9: Professionalize docs and release workflow guardrails

**Files:**
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- Modify: `AGENTS.md`
- Create: `docs/conventions/python.md`
- Create: `docs/conventions/testing.md`

**Step 1: Write the failing documentation check**

```bash
rg -n "Versioning|Testing|Development" README.md
```

Expected: Missing one or more required sections.

**Step 2: Run check to verify the gap**

Run: `rg -n "Versioning|Testing|Development" README.md`  
Expected: Incomplete matches

**Step 3: Write minimal implementation**

```markdown
<!-- README additions -->
## Development
- Install: `python -m pip install -e ".[dev]"`
- Test: `python -m pytest`
- Lint: `python -m ruff check .`

## Testing
- Unit tests for domain/application
- Smoke tests for CLI commands
```

```markdown
<!-- docs/conventions/testing.md -->
# Testing Conventions
- Prefer unit tests for business logic.
- Keep CLI tests focused on behavior/output contracts.
```

**Step 4: Run checks to verify they pass**

Run: `rg -n "Versioning|Testing|Development" README.md && python -m pytest -q`  
Expected: Required sections found; tests pass

**Step 5: Commit**

```bash
git add README.md CHANGELOG.md AGENTS.md docs/conventions/python.md docs/conventions/testing.md
git commit -m "docs: establish development and testing conventions"
```

### Task 10: Final quality gate and v0.1.0 baseline tag preparation

**Files:**
- Modify: `CHANGELOG.md`
- Modify: `src/sgm/__init__.py`

**Step 1: Write failing version consistency check**

```bash
python - <<'PY'
from pathlib import Path
import re
init = Path("src/sgm/__init__.py").read_text()
assert re.search(r'__version__\\s*=\\s*"0.1.0"', init)
print("ok")
PY
```

**Step 2: Run checks to verify current failures (if any)**

Run: `python -m pytest -q && python -m ruff check .`  
Expected: Fix any failing output before release baseline

**Step 3: Write minimal implementation**

```markdown
<!-- CHANGELOG.md -->
## [0.1.0] - YYYY-MM-DD
### Added
- Initial Sigma CLI v1 baseline.
```

**Step 4: Run full verification**

Run: `python -m pytest -q && python -m ruff check . && sgm --help`  
Expected: All checks pass and CLI help renders

**Step 5: Commit**

```bash
git add CHANGELOG.md src/sgm/__init__.py
git commit -m "chore: prepare v0.1.0 baseline release metadata"
```
