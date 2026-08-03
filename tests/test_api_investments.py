from __future__ import annotations

from fastapi.testclient import TestClient

from sigma import database
from sigma.db import investments


def fake_quotes(monkeypatch, answers: dict[str, dict | None]):
    def fetch_quote(symbol: str):
        return answers.get(symbol)

    monkeypatch.setattr(investments.prices, "fetch_quote", fetch_quote)


def make_investment_account(api: TestClient) -> None:
    api.post(
        "/api/accounts",
        json={"id": "fintual", "name": "Fintual", "kind": "investment", "balance": 1_000_000},
    )


def test_investment_account_shows_up_with_its_kind(api: TestClient):
    make_investment_account(api)

    response = api.get("/api/accounts")
    kinds = {a["id"]: a["kind"] for a in response.json()}
    assert kinds["fintual"] == "investment"


def test_buy_sell_and_activity_round_trip(api: TestClient):
    make_investment_account(api)
    api.post(
        "/api/investments/fx-exchange",
        json={"account_id": "fintual", "clp_amount": 800_000, "usd_amount": 1_000},
    )

    buy = api.post(
        "/api/investments/buy",
        json={
            "account_id": "fintual",
            "ticker": "aapl",
            "quantity": 5,
            "price": 50,
            "currency": "USD",
        },
    )
    assert buy.status_code == 201
    assert buy.json()["ticker"] == "AAPL"

    holdings = api.get("/api/investments/accounts/fintual/holdings").json()
    assert holdings[0]["quantity"] == 5

    sell = api.post(
        "/api/investments/sell",
        json={"account_id": "fintual", "ticker": "AAPL", "quantity": 2, "price": 80},
    )
    assert sell.status_code == 201
    assert sell.json()["realized_gain"] == 2 * (80 - 50) * 100

    activity = api.get("/api/investments/accounts/fintual/activity").json()
    assert [row["kind"] for row in activity] == ["sell", "buy", "fx_exchange"]


def test_sell_more_than_held_is_a_400(api: TestClient):
    make_investment_account(api)
    response = api.post(
        "/api/investments/sell",
        json={"account_id": "fintual", "ticker": "AAPL", "quantity": 1, "price": 80},
    )
    assert response.status_code == 400
    assert "No tienes esa cantidad" in response.json()["detail"]


def test_delete_transaction(api: TestClient):
    make_investment_account(api)
    buy = api.post(
        "/api/investments/buy",
        json={
            "account_id": "fintual",
            "ticker": "AAPL",
            "quantity": 5,
            "price": 50,
            "currency": "CLP",
        },
    ).json()

    response = api.delete(f"/api/investments/transactions/{buy['id']}")
    assert response.status_code == 204
    assert api.get("/api/investments/accounts/fintual/holdings").json() == []


def test_refresh_caches_prices_and_snapshots_value(api: TestClient, monkeypatch):
    make_investment_account(api)
    fake_quotes(
        monkeypatch,
        {"USDCLP=X": {"price": 900.0, "currency": "USD", "name": "USD/CLP"}},
    )

    response = api.post("/api/investments/refresh", json={})
    assert response.status_code == 200

    history = api.get("/api/investments/accounts/fintual/history").json()
    assert len(history) == 1
    assert history[0]["value_clp"] == 1_000_000


def test_lookup_returns_the_quote(api: TestClient, monkeypatch):
    fake_quotes(
        monkeypatch, {"AAPL": {"price": 150.0, "currency": "USD", "name": "Apple Inc."}}
    )

    response = api.get("/api/investments/lookup/aapl")
    assert response.status_code == 200
    assert response.json()["name"] == "Apple Inc."


def test_lookup_of_an_unknown_ticker_is_a_404(api: TestClient, monkeypatch):
    fake_quotes(monkeypatch, {})

    response = api.get("/api/investments/lookup/NOTATICKER")
    assert response.status_code == 404


def test_summary_totals_include_investments(api: TestClient, monkeypatch):
    make_investment_account(api)
    fake_quotes(
        monkeypatch, {"USDCLP=X": {"price": 900.0, "currency": "USD", "name": "USD/CLP"}}
    )
    db = database.current()
    investments.refresh_prices(db, [])

    totals = api.get("/api/summary").json()["totals"]
    assert totals["investments"] == 1_000_000
    assert totals["net"] == 100_000 + 1_000_000
