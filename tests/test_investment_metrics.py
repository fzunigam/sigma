from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from sigma.db import investment_metrics as metrics
from sigma.db import investment_transactions as txns
from sigma.db import investments, transfers


def fake_quotes(monkeypatch, answers: dict[str, dict | None]):
    def fetch_quote(symbol: str):
        return answers.get(symbol)

    monkeypatch.setattr(investments.prices, "fetch_quote", fetch_quote)


# --- XIRR ----------------------------------------------------------------------


def test_xirr_of_a_single_year_round_trip():
    rate = metrics.xirr([("2025-01-01", -1_000.0), ("2026-01-01", 1_200.0)])
    assert rate == pytest.approx(0.2, abs=1e-4)


def test_xirr_of_multiple_deposits():
    # 1000 in, 1000 more in six months later, worth 2200 a year after the first.
    cashflows = [
        ("2025-01-01", -1_000.0),
        ("2025-07-02", -1_000.0),
        ("2026-01-01", 2_200.0),
    ]
    rate = metrics.xirr(cashflows)
    assert rate is not None
    assert rate > 0

    # Reinvesting the same numbers at the solved rate should net back to ~0.
    t0 = date(2025, 1, 1)
    npv = sum(
        amount / (1 + rate) ** ((date.fromisoformat(when) - t0).days / 365)
        for when, amount in cashflows
    )
    assert npv == pytest.approx(0.0, abs=1.0)


def test_xirr_needs_at_least_two_flows():
    assert metrics.xirr([("2025-01-01", -1_000.0)]) is None


# --- Account metrics -------------------------------------------------------------


def test_metrics_value_holdings_at_the_cached_price(db: Path, fintual: dict, monkeypatch):
    fake_quotes(
        monkeypatch,
        {
            "AAPL": {"price": 180.0, "currency": "USD", "name": "Apple Inc."},
            "USDCLP=X": {"price": 900.0, "currency": "USD", "name": "USD/CLP"},
        },
    )
    investments.refresh_prices(db, ["AAPL"])
    txns.create_fx_exchange(db, "fintual", 800_000, 1_000)
    txns.create_buy(db, "fintual", "AAPL", 5, 150, "USD")

    result = metrics.account_metrics(db, "fintual")

    position = result["positions"][0]
    assert position["ticker"] == "AAPL"
    assert position["current_price"] == 180.0
    assert position["market_value_clp"] == round(5 * 180.0 * 900.0)
    assert position["cost_basis_clp"] == round(5 * 150 * 900.0)
    assert position["gain_clp"] == position["market_value_clp"] - position["cost_basis_clp"]
    assert result["unrealized_gain_clp"] == position["gain_clp"]


def test_metrics_total_value_includes_cash_in_both_currencies(
    db: Path, fintual: dict, monkeypatch
):
    fake_quotes(monkeypatch, {"USDCLP=X": {"price": 900.0, "currency": "USD", "name": "x"}})
    investments.refresh_prices(db, [])
    txns.create_fx_exchange(db, "fintual", 800_000, 1_000)

    result = metrics.account_metrics(db, "fintual")

    # 200_000 CLP left in the account, plus 1_000 USD converted at 900.
    assert result["cash_clp"] == 200_000
    assert result["cash_usd_clp"] == round(1_000 * 900.0)
    assert result["total_value_clp"] == 200_000 + round(1_000 * 900.0)


def test_metrics_sums_realized_gain_and_dividends(db: Path, fintual: dict, monkeypatch):
    fake_quotes(
        monkeypatch,
        {
            "AAPL": {"price": 150.0, "currency": "USD", "name": "Apple Inc."},
            "USDCLP=X": {"price": 900.0, "currency": "USD", "name": "x"},
        },
    )
    investments.refresh_prices(db, ["AAPL"])
    txns.create_fx_exchange(db, "fintual", 800_000, 1_000)
    txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")
    txns.create_sell(db, "fintual", "AAPL", 5, 80)
    txns.create_dividend(db, "fintual", "AAPL", 10, "USD")

    result = metrics.account_metrics(db, "fintual")

    assert result["realized_gain_clp"] == round(5 * (80 - 50) * 900.0)
    assert result["dividends_clp"] == round(10 * 900.0)


def test_metrics_irr_uses_transfers_not_internal_transactions(
    db: Path, wallet: dict, fintual: dict, monkeypatch
):
    fake_quotes(monkeypatch, {"USDCLP=X": {"price": 900.0, "currency": "USD", "name": "x"}})
    investments.refresh_prices(db, [])

    transfers.create_transfer(db, "wallet", "fintual", 50_000, date="2025-01-01")

    result = metrics.account_metrics(db, "fintual")

    assert result["irr"] is not None


def test_metrics_irr_is_none_without_any_transfer(db: Path, fintual: dict, monkeypatch):
    fake_quotes(monkeypatch, {"USDCLP=X": {"price": 900.0, "currency": "USD", "name": "x"}})
    investments.refresh_prices(db, [])

    result = metrics.account_metrics(db, "fintual")

    assert result["irr"] is None


def test_metrics_marks_a_position_stale_without_a_cached_price(db: Path, fintual: dict):
    txns.create_fx_exchange(db, "fintual", 800_000, 1_000)
    txns.create_buy(db, "fintual", "AAPL", 5, 150, "USD")

    result = metrics.account_metrics(db, "fintual")

    assert result["positions"][0]["stale"] is True
    assert result["positions"][0]["current_price"] == 150  # falls back to avg_cost


# --- Value history ---------------------------------------------------------------


def test_value_snapshot_upserts_one_row_per_day(db: Path, fintual: dict):
    metrics.record_value_snapshot(db, "fintual", 1_000_000)
    metrics.record_value_snapshot(db, "fintual", 1_050_000)

    history = metrics.get_value_history(db, "fintual")
    assert len(history) == 1
    assert history[0]["value_clp"] == 1_050_000
