from __future__ import annotations

import io
import json
import urllib.error

from sigma import prices


def fake_yahoo(monkeypatch, payload: object):
    """Answer the chart endpoint with ``payload`` instead of hitting Yahoo."""

    def urlopen(request, timeout=None, context=None):
        return io.BytesIO(json.dumps(payload).encode("utf-8"))

    monkeypatch.setattr(prices.urllib.request, "urlopen", urlopen)


def fake_offline(monkeypatch):
    def urlopen(request, timeout=None, context=None):
        raise urllib.error.URLError("no internet")

    monkeypatch.setattr(prices.urllib.request, "urlopen", urlopen)


def chart(price: float = 150.25, currency: str = "USD", name: str = "Apple Inc.") -> dict:
    return {
        "chart": {
            "result": [
                {"meta": {"regularMarketPrice": price, "currency": currency, "shortName": name}}
            ]
        }
    }


def test_fetch_quote_reads_price_currency_and_name(monkeypatch):
    fake_yahoo(monkeypatch, chart(150.25, "USD", "Apple Inc."))

    quote = prices.fetch_quote("AAPL")

    assert quote == {"price": 150.25, "currency": "USD", "name": "Apple Inc."}


def test_fetch_quote_falls_back_to_the_symbol_without_a_name(monkeypatch):
    payload = chart()
    del payload["chart"]["result"][0]["meta"]["shortName"]
    fake_yahoo(monkeypatch, payload)

    quote = prices.fetch_quote("AAPL")

    assert quote["name"] == "AAPL"


def test_fetch_quote_returns_none_when_offline(monkeypatch):
    fake_offline(monkeypatch)

    assert prices.fetch_quote("AAPL") is None


def test_fetch_quote_returns_none_for_an_unknown_symbol(monkeypatch):
    fake_yahoo(monkeypatch, {"chart": {"result": None, "error": {"code": "Not Found"}}})

    assert prices.fetch_quote("NOTATICKER") is None


def test_fetch_quote_returns_none_for_malformed_json(monkeypatch):
    fake_yahoo(monkeypatch, {"unexpected": "shape"})

    assert prices.fetch_quote("AAPL") is None
