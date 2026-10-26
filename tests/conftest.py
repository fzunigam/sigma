from __future__ import annotations

from pathlib import Path

import pytest

from sigma.db import accounts
from sigma.db.schema import create_database


@pytest.fixture
def db(tmp_path: Path) -> Path:
    """An empty Sigma database in a temporary directory."""
    path = tmp_path / "finanzas.db"
    create_database(path)
    return path


@pytest.fixture
def wallet(db: Path) -> dict:
    return accounts.create_account(db, "wallet", "Efectivo", "debit", balance=100_000)


@pytest.fixture
def card(db: Path) -> dict:
    return accounts.create_account(db, "card", "Tarjeta", "credit", credit_limit=500_000)
