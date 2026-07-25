from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from sigma import database
from sigma.api import app
from sigma.db import accounts, movements


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


# --- Database file ---------------------------------------------------------


def test_status_before_anything_is_chosen(client: TestClient):
    body = client.get("/api/database").json()
    assert body["is_open"] is False
    assert body["path"] is None
    assert body["version"]


def test_create_and_report_open(client: TestClient, tmp_path: Path):
    path = tmp_path / "finanzas.db"
    body = client.post("/api/database/create", json={"path": str(path)}).json()

    assert body["is_open"] is True
    assert body["name"] == "finanzas"
    assert database.current() == path


def test_creating_over_existing_data_is_a_400(client: TestClient, tmp_path: Path):
    path = tmp_path / "finanzas.db"
    client.post("/api/database/create", json={"path": str(path)})

    response = client.post("/api/database/create", json={"path": str(path)})
    assert response.status_code == 400
    assert "Ya existe" in response.json()["detail"]


def test_opening_a_stray_file_is_a_400(client: TestClient, tmp_path: Path):
    stray = tmp_path / "notas.db"
    stray.write_text("no soy sqlite")

    response = client.post("/api/database/open", json={"path": str(stray)})
    assert response.status_code == 400


def test_working_without_a_database_is_a_400(client: TestClient):
    response = client.get("/api/summary")
    assert response.status_code == 400
    assert "No hay una base de datos abierta" in response.json()["detail"]


def test_restore_round_trip(api: TestClient, tmp_path: Path):
    from sigma.db import connection

    path = database.current()
    snapshot = connection.create_backup(path)
    api.post(
        "/api/movements",
        json={"kind": "expense", "amount": 40_000, "description": "Error"},
    )

    api.post("/api/database/restore", json={"path": str(snapshot)})

    assert api.get("/api/summary").json()["totals"]["available"] == 100_000


def test_theme_is_persisted(client: TestClient):
    assert client.put("/api/theme", json={"theme": "light"}).json()["theme"] == "light"
    assert client.get("/api/database").json()["theme"] == "light"
    assert client.put("/api/theme", json={"theme": "neon"}).status_code == 422


# --- Accounts --------------------------------------------------------------


def test_account_lifecycle(api: TestClient):
    created = api.post(
        "/api/accounts",
        json={"id": "card", "name": "Tarjeta", "kind": "credit", "credit_limit": 500_000},
    )
    assert created.status_code == 201
    assert created.json()["available"] == 500_000

    renamed = api.patch("/api/accounts/card", json={"name": "Tarjeta Banco"})
    assert renamed.json()["name"] == "Tarjeta Banco"

    reidentified = api.put("/api/accounts/card/id", json={"id": "visa"})
    assert reidentified.json()["id"] == "visa"

    assert api.delete("/api/accounts/visa").status_code == 204
    assert [a["id"] for a in api.get("/api/accounts").json()] == ["wallet"]


def test_duplicate_account_is_a_400(api: TestClient):
    response = api.post(
        "/api/accounts", json={"id": "wallet", "name": "Otra", "kind": "debit"}
    )
    assert response.status_code == 400


def test_unknown_account_is_a_404(api: TestClient):
    assert api.patch("/api/accounts/nope", json={"name": "X"}).status_code == 404
    assert api.delete("/api/accounts/nope").status_code == 404


def test_invalid_account_payload_is_a_422(api: TestClient):
    assert (
        api.post("/api/accounts", json={"id": "x", "name": "X", "kind": "ahorro"}).status_code
        == 422
    )


# --- Movements -------------------------------------------------------------


def test_movement_updates_the_summary(api: TestClient):
    response = api.post(
        "/api/movements",
        json={"kind": "expense", "amount": 30_000, "description": "Supermercado"},
    )
    assert response.status_code == 201

    summary = api.get("/api/summary").json()
    assert summary["totals"]["available"] == 70_000
    assert summary["pending"] == {"net": -30_000, "count": 1}
    assert summary["recent"][0]["description"] == "Supermercado"


def test_movement_falls_back_to_the_only_account(api: TestClient):
    body = api.post(
        "/api/movements", json={"kind": "expense", "amount": 1_000, "description": "Café"}
    ).json()
    assert body["account_id"] == "wallet"


def test_movement_falls_back_to_the_configured_default(api: TestClient):
    api.post(
        "/api/accounts",
        json={"id": "bank", "name": "Banco", "kind": "debit", "balance": 50_000},
    )
    api.put(
        "/api/preferences",
        json={"default_expense_account": "bank", "default_income_account": "wallet"},
    )

    expense = api.post(
        "/api/movements", json={"kind": "expense", "amount": 2_000, "description": "Café"}
    ).json()
    income = api.post(
        "/api/movements", json={"kind": "income", "amount": 5_000, "description": "Sueldo"}
    ).json()

    assert expense["account_id"] == "bank"
    assert income["account_id"] == "wallet"


def test_ambiguous_account_is_rejected(api: TestClient):
    api.post("/api/accounts", json={"id": "bank", "name": "Banco", "kind": "debit"})
    response = api.post(
        "/api/movements", json={"kind": "expense", "amount": 1_000, "description": "Café"}
    )
    assert response.status_code == 400
    assert "Elige una cuenta" in response.json()["detail"]


def test_overspending_is_a_400_with_a_readable_message(api: TestClient):
    response = api.post(
        "/api/movements",
        json={"kind": "expense", "amount": 999_999, "description": "Imposible"},
    )
    assert response.status_code == 400
    assert "Saldo insuficiente" in response.json()["detail"]


def test_pending_flag_can_be_toggled(api: TestClient):
    movement = api.post(
        "/api/movements", json={"kind": "expense", "amount": 1_000, "description": "Café"}
    ).json()

    api.put(f"/api/movements/{movement['id']}/pending", json={"pending": False})
    assert api.get("/api/summary").json()["pending"]["count"] == 0


def test_delete_movement_restores_the_balance(api: TestClient):
    movement = api.post(
        "/api/movements", json={"kind": "expense", "amount": 30_000, "description": "Error"}
    ).json()

    assert api.delete(f"/api/movements/{movement['id']}").status_code == 204
    assert api.get("/api/summary").json()["totals"]["available"] == 100_000


def test_movements_can_be_filtered_by_month(api: TestClient):
    api.post(
        "/api/movements",
        json={"kind": "expense", "amount": 1_000, "description": "Enero", "date": "2026-01-10"},
    )
    api.post(
        "/api/movements",
        json={"kind": "expense", "amount": 2_000, "description": "Marzo", "date": "2026-03-10"},
    )

    rows = api.get("/api/movements", params={"month": "2026-03"}).json()
    assert [row["description"] for row in rows] == ["Marzo"]


def test_bad_date_format_is_a_422(api: TestClient):
    response = api.post(
        "/api/movements",
        json={"kind": "expense", "amount": 1_000, "description": "X", "date": "10-03-2026"},
    )
    assert response.status_code == 422


# --- Transfers -------------------------------------------------------------


def test_transfer_moves_money_between_accounts(api: TestClient):
    api.post("/api/accounts", json={"id": "bank", "name": "Banco", "kind": "debit"})
    response = api.post(
        "/api/transfers",
        json={"from_account": "wallet", "to_account": "bank", "amount": 40_000},
    )
    assert response.status_code == 201

    balances = {a["id"]: a["balance"] for a in api.get("/api/accounts").json()}
    assert balances == {"wallet": 60_000, "bank": 40_000}


def test_transfer_is_excluded_from_the_month_totals(api: TestClient):
    api.post("/api/accounts", json={"id": "bank", "name": "Banco", "kind": "debit"})
    api.post(
        "/api/transfers",
        json={"from_account": "wallet", "to_account": "bank", "amount": 40_000},
    )

    month = api.get("/api/summary").json()["month"]
    assert month["income"] == 0 and month["expense"] == 0


def test_transfer_from_a_credit_card_is_a_400(api: TestClient):
    api.post(
        "/api/accounts",
        json={"id": "card", "name": "Tarjeta", "kind": "credit", "credit_limit": 100_000},
    )
    response = api.post(
        "/api/transfers",
        json={"from_account": "card", "to_account": "wallet", "amount": 1_000},
    )
    assert response.status_code == 400


def test_delete_transfer_reverses_it(api: TestClient):
    api.post("/api/accounts", json={"id": "bank", "name": "Banco", "kind": "debit"})
    transfer = api.post(
        "/api/transfers",
        json={"from_account": "wallet", "to_account": "bank", "amount": 40_000},
    ).json()

    assert api.delete(f"/api/transfers/{transfer['id']}").status_code == 204
    assert api.get("/api/summary").json()["totals"]["available"] == 100_000


# --- Reconciliations -------------------------------------------------------


def test_reconciliation_flow(api: TestClient):
    api.post(
        "/api/movements", json={"kind": "income", "amount": 500_000, "description": "Sueldo"}
    )
    api.post(
        "/api/movements", json={"kind": "expense", "amount": 120_000, "description": "Arriendo"}
    )

    pending = api.get("/api/reconciliations/pending").json()
    assert pending["summary"] == {"net": 380_000, "count": 2}
    assert len(pending["movements"]) == 2

    result = api.post("/api/reconciliations").json()
    assert result["net_amount"] == 380_000

    closed = api.get(f"/api/reconciliations/{result['id']}/movements").json()
    assert {row["description"] for row in closed} == {"Sueldo", "Arriendo"}
    assert api.get("/api/reconciliations/pending").json()["summary"]["count"] == 0


def test_reconciling_nothing_is_a_400(api: TestClient):
    response = api.post("/api/reconciliations")
    assert response.status_code == 400
    assert "No hay movimientos pendientes" in response.json()["detail"]


def test_unknown_reconciliation_is_a_404(api: TestClient):
    assert api.get("/api/reconciliations/nope/movements").status_code == 404


# --- Preferences -----------------------------------------------------------


def test_preferences_round_trip(api: TestClient):
    body = api.put(
        "/api/preferences",
        json={"default_expense_account": "wallet", "default_income_account": "wallet"},
    ).json()
    assert body["default_expense_account"] == "wallet"
    assert api.get("/api/preferences").json() == body


def test_preferences_reject_an_unknown_account(api: TestClient):
    response = api.put(
        "/api/preferences",
        json={"default_expense_account": "fantasma", "default_income_account": ""},
    )
    assert response.status_code == 404


# --- Totals ----------------------------------------------------------------


def test_totals_separate_cash_from_card_debt(api: TestClient):
    api.post(
        "/api/accounts",
        json={"id": "card", "name": "Tarjeta", "kind": "credit", "credit_limit": 500_000},
    )
    db = database.current()
    movements.create_movement(db, "expense", 80_000, "Notebook", "card")

    totals = api.get("/api/summary").json()["totals"]
    assert totals == {"available": 100_000, "debt": 80_000, "net": 20_000}


def test_summary_hides_deleted_accounts(api: TestClient):
    db = database.current()
    accounts.create_account(db, "old", "Antigua", "debit", balance=5_000)
    accounts.delete_account(db, "old")

    summary = api.get("/api/summary").json()
    assert [a["id"] for a in summary["accounts"]] == ["wallet"]
    assert summary["totals"]["available"] == 100_000
