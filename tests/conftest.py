from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sigma.api import app
from sigma.db import accounts
from sigma.db.schema import create_database


@pytest.fixture(autouse=True)
def isolated_settings(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("SIGMA_SETTINGS_DIR", str(tmp_path / "config"))


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def api(client: TestClient, tmp_path: Path) -> TestClient:
    """A client with a database open and one debit account ready."""
    client.post("/api/database/create", json={"path": str(tmp_path / "finanzas.db")})
    client.post(
        "/api/accounts",
        json={"id": "wallet", "name": "Efectivo", "kind": "debit", "balance": 100_000},
    )
    return client


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


@pytest.fixture
def fintual(db: Path) -> dict:
    return accounts.create_account(db, "fintual", "Fintual", "investment", balance=1_000_000)
