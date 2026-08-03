"""Ask Yahoo Finance for a ticker's current price.

Sigma otherwise only touches the network for the update check
(:mod:`sigma.updates`), and this follows the exact same shape: a plain GET of
a public endpoint, nothing about the user or the database sent, and any
failure — no internet, an unknown ticker, Yahoo unreachable — reported as "no
price" rather than raised. The caller always has something to show (the last
cached value in ``security_prices``/``fx_rates``) instead of a broken screen.

Deliberately not the ``yfinance`` package: it pulls in pandas and numpy, which
Sigma's macOS bundle dropped on purpose in 1.0 to keep it small. This hits the
same public chart endpoint ``yfinance`` itself wraps, with the same
``urllib.request`` + certifi approach already used for the update check.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from sigma.updates import ssl_context

CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?range=1d&interval=1d"
TIMEOUT_SECONDS = 4

# The FX pair used to convert USD cash and holdings into CLP for display.
USD_CLP_SYMBOL = "USDCLP=X"


def fetch_quote(symbol: str) -> dict[str, Any] | None:
    """The latest price for ``symbol`` — a ticker, or an FX pair like
    ``'USDCLP=X'``.

    ``{"price": float, "currency": str, "name": str}``, or ``None`` if the
    symbol does not exist or the request failed for any reason.
    """
    request = urllib.request.Request(
        CHART_URL.format(symbol=symbol), headers={"User-Agent": "Sigma"}
    )
    try:
        with urllib.request.urlopen(
            request, timeout=TIMEOUT_SECONDS, context=ssl_context()
        ) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception:
        # Every failure means the same thing: we do not know the price right
        # now, so say nothing and let the last cached value stand.
        return None

    try:
        meta = payload["chart"]["result"][0]["meta"]
        price = meta["regularMarketPrice"]
        currency = meta["currency"]
    except (KeyError, IndexError, TypeError):
        return None
    if not isinstance(price, (int, float)):
        return None

    name = meta.get("shortName") or meta.get("symbol") or symbol
    return {"price": float(price), "currency": str(currency), "name": str(name)}
