from __future__ import annotations

from pathlib import Path

import pytest

from sigma.db import investment_transactions as txns
from sigma.db import investments
from sigma.db.errors import ValidationError


def fund_usd(
    db: Path,
    account_id: str = "fintual",
    clp: float = 800_000,
    usd: float = 1_000,
    date: str = "2025-01-01",
) -> None:
    """Convenience: convert CLP into USD cash at an 800 CLP/USD rate."""
    txns.create_fx_exchange(db, account_id, clp, usd, date=date)


# --- Currency exchange -------------------------------------------------------


def test_fx_exchange_moves_cash_between_currencies(db: Path, fintual: dict):
    txns.create_fx_exchange(db, "fintual", 800_000, 1_000)

    from sigma.db import accounts

    assert accounts.get_account(db, "fintual")["balance"] == 200_000
    assert investments.get_cash_usd(db, "fintual") == 100_000  # cents


def test_fx_exchange_rejects_insufficient_clp(db: Path, fintual: dict):
    with pytest.raises(ValidationError, match="Saldo insuficiente"):
        txns.create_fx_exchange(db, "fintual", 5_000_000, 1_000)


# --- Buying -------------------------------------------------------------------


def test_buy_creates_a_holding_and_debits_cash(db: Path, fintual: dict):
    fund_usd(db)
    txns.create_buy(db, "fintual", "aapl", 5, 50, "USD")

    holding = investments.get_holding(db, "fintual", "AAPL")
    assert holding["quantity"] == 5
    assert holding["avg_cost"] == 50
    assert holding["currency"] == "USD"
    assert investments.get_cash_usd(db, "fintual") == 100_000 - 25_000


def test_buy_averages_the_cost_across_purchases(db: Path, fintual: dict):
    fund_usd(db)
    txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")
    txns.create_buy(db, "fintual", "AAPL", 5, 70, "USD")

    holding = investments.get_holding(db, "fintual", "AAPL")
    assert holding["quantity"] == 10
    assert holding["avg_cost"] == 60


def test_buy_rejects_insufficient_usd_cash(db: Path, fintual: dict):
    fund_usd(db, usd=100)
    with pytest.raises(ValidationError, match=r"Saldo insuficiente en 'Fintual' \(USD\)"):
        txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")


def test_buy_rejects_a_non_investment_account(db: Path, wallet: dict):
    with pytest.raises(ValidationError, match="no es una cuenta de inversión"):
        txns.create_buy(db, "wallet", "AAPL", 5, 50, "USD")


def test_buy_rejects_zero_quantity(db: Path, fintual: dict):
    fund_usd(db)
    with pytest.raises(ValidationError, match="cantidad debe ser mayor"):
        txns.create_buy(db, "fintual", "AAPL", 0, 50, "USD")


def test_buy_includes_fees_in_the_cost_basis(db: Path, fintual: dict):
    fund_usd(db)
    txns.create_buy(db, "fintual", "AAPL", 10, 50, "USD", fees=5000)  # $50 in cents

    holding = investments.get_holding(db, "fintual", "AAPL")
    # (10 * 50 + 50) / 10 = 55
    assert holding["avg_cost"] == 55
    assert investments.get_cash_usd(db, "fintual") == 100_000 - 50_000 - 5_000


# --- Selling -------------------------------------------------------------------


def test_sell_credits_cash_and_reduces_the_holding(db: Path, fintual: dict):
    fund_usd(db)
    txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")
    txns.create_buy(db, "fintual", "AAPL", 5, 70, "USD")
    cash_before = investments.get_cash_usd(db, "fintual")

    sale = txns.create_sell(db, "fintual", "AAPL", 4, 80)

    holding = investments.get_holding(db, "fintual", "AAPL")
    assert holding["quantity"] == 6
    assert holding["avg_cost"] == 60  # unchanged by a sell
    assert investments.get_cash_usd(db, "fintual") == cash_before + 4 * 80 * 100
    assert sale["realized_gain"] == 4 * (80 - 60) * 100


def test_selling_the_whole_position_removes_the_holding(db: Path, fintual: dict):
    fund_usd(db)
    txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")
    txns.create_sell(db, "fintual", "AAPL", 5, 80)

    assert investments.get_holding(db, "fintual", "AAPL") is None


def test_sell_rejects_more_than_is_held(db: Path, fintual: dict):
    fund_usd(db)
    txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")

    with pytest.raises(ValidationError, match="No tienes esa cantidad"):
        txns.create_sell(db, "fintual", "AAPL", 6, 80)


def test_sell_rejects_a_ticker_never_bought(db: Path, fintual: dict):
    with pytest.raises(ValidationError, match="No tienes esa cantidad"):
        txns.create_sell(db, "fintual", "AAPL", 1, 80)


# --- Dividends -----------------------------------------------------------------


def test_dividend_credits_usd_cash(db: Path, fintual: dict):
    fund_usd(db)
    txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")
    cash_before = investments.get_cash_usd(db, "fintual")

    txns.create_dividend(db, "fintual", "AAPL", 12.5, "USD")

    assert investments.get_cash_usd(db, "fintual") == cash_before + 1250


def test_dividend_in_clp_credits_the_account_balance(db: Path, fintual: dict):
    from sigma.db import accounts

    txns.create_dividend(db, "fintual", "FALABELLA.SN", 5_000, "CLP")

    assert accounts.get_account(db, "fintual")["balance"] == 1_000_000 + 5_000


# --- Editing and deleting ------------------------------------------------------


def test_updating_an_old_buy_recomputes_later_realized_gain(db: Path, fintual: dict):
    fund_usd(db)
    first = txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")
    txns.create_buy(db, "fintual", "AAPL", 5, 70, "USD")
    sale = txns.create_sell(db, "fintual", "AAPL", 4, 80)
    assert sale["realized_gain"] == 4 * (80 - 60) * 100

    # Correcting the first buy's price changes the average cost the sale used.
    txns.update_investment_transaction(db, first["id"], price=30)

    holding = investments.get_holding(db, "fintual", "AAPL")
    # (5 * 30 + 5 * 70) / 10 = 50
    assert holding["avg_cost"] == 50
    updated_sale = investments.get_investment_transaction(db, sale["id"])
    assert updated_sale["realized_gain"] == 4 * (80 - 50) * 100


def test_deleting_a_buy_reverses_its_cash_effect(db: Path, fintual: dict):
    fund_usd(db)
    cash_before = investments.get_cash_usd(db, "fintual")
    buy = txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")

    txns.delete_investment_transaction(db, buy["id"])

    assert investments.get_cash_usd(db, "fintual") == cash_before
    assert investments.get_holding(db, "fintual", "AAPL") is None


def test_deleting_a_dividend_reverses_the_credit(db: Path, fintual: dict):
    from sigma.db import accounts

    dividend = txns.create_dividend(db, "fintual", "FALABELLA.SN", 5_000, "CLP")
    txns.delete_investment_transaction(db, dividend["id"])

    assert accounts.get_account(db, "fintual")["balance"] == 1_000_000


def test_update_rejects_dividends(db: Path, fintual: dict):
    dividend = txns.create_dividend(db, "fintual", "FALABELLA.SN", 5_000, "CLP")
    with pytest.raises(ValidationError, match="Elimina y vuelve a registrar"):
        txns.update_investment_transaction(db, dividend["id"], quantity=1)


# --- Activity listing -----------------------------------------------------------


def test_list_investment_activity_orders_newest_first(db: Path, fintual: dict):
    fund_usd(db)
    txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD", date="2026-01-01")
    txns.create_buy(db, "fintual", "AAPL", 5, 70, "USD", date="2026-02-01")

    dates = [row["date"] for row in investments.list_investment_activity(db, "fintual")]
    assert dates == ["2026-02-01", "2026-01-01", "2025-01-01"]


def test_list_investment_activity_excludes_deleted(db: Path, fintual: dict):
    fund_usd(db)
    buy = txns.create_buy(db, "fintual", "AAPL", 5, 50, "USD")
    txns.delete_investment_transaction(db, buy["id"])

    kinds = [row["kind"] for row in investments.list_investment_activity(db, "fintual")]
    assert "buy" not in kinds


# --- Prices and FX cache --------------------------------------------------------


def fake_quotes(monkeypatch, answers: dict[str, dict | None]):
    def fetch_quote(symbol: str):
        return answers.get(symbol)

    monkeypatch.setattr(investments.prices, "fetch_quote", fetch_quote)


def test_refresh_prices_caches_successful_answers(db: Path, monkeypatch):
    fake_quotes(
        monkeypatch,
        {
            "AAPL": {"price": 150.25, "currency": "USD", "name": "Apple Inc."},
            "USDCLP=X": {"price": 950.0, "currency": "USD", "name": "USD/CLP"},
        },
    )

    result = investments.refresh_prices(db, ["AAPL"])

    assert result == {"AAPL": True}
    assert investments.get_price(db, "AAPL") == {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "currency": "USD",
        "price": 150.25,
        "fetched_at": investments.get_price(db, "AAPL")["fetched_at"],
    }
    assert investments.get_fx_rate(db) == 950.0


def test_refresh_prices_keeps_the_last_cache_for_a_failed_ticker(db: Path, monkeypatch):
    fake_quotes(
        monkeypatch,
        {
            "AAPL": {"price": 150.0, "currency": "USD", "name": "Apple Inc."},
            "USDCLP=X": {"price": 950.0, "currency": "USD", "name": "USD/CLP"},
        },
    )
    investments.refresh_prices(db, ["AAPL"])

    fake_quotes(monkeypatch, {"AAPL": None, "USDCLP=X": None})
    result = investments.refresh_prices(db, ["AAPL"])

    assert result == {"AAPL": False}
    assert investments.get_price(db, "AAPL")["price"] == 150.0


def test_get_price_is_none_before_any_refresh(db: Path):
    assert investments.get_price(db, "AAPL") is None
    assert investments.get_fx_rate(db) is None


def test_lookup_ticker_validates_against_yahoo(db: Path, monkeypatch):
    fake_quotes(
        monkeypatch, {"AAPL": {"price": 150.0, "currency": "USD", "name": "Apple Inc."}}
    )

    assert investments.lookup_ticker(db, "aapl")["name"] == "Apple Inc."
    assert investments.lookup_ticker(db, "NOTATICKER") is None


def test_lookup_ticker_caches_a_successful_answer(db: Path, monkeypatch):
    """A ticker just validated for a purchase should not show as stale before
    the next refresh — the lookup already paid for a fresh quote."""
    fake_quotes(
        monkeypatch, {"AAPL": {"price": 150.0, "currency": "USD", "name": "Apple Inc."}}
    )

    investments.lookup_ticker(db, "aapl")

    assert investments.get_price(db, "AAPL") == {
        "ticker": "AAPL",
        "name": "Apple Inc.",
        "currency": "USD",
        "price": 150.0,
        "fetched_at": investments.get_price(db, "AAPL")["fetched_at"],
    }
