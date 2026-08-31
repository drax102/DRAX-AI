"""
finance_tools.py — Stock, Index, and Crypto finance data tools.
Supports US stocks, Indian NSE/BSE stocks, global indices, and crypto using public Yahoo Finance endpoints.
"""

import requests
from backend.agent.tool_registry import register_tool
from backend.database.db import (
    add_to_watchlist,
    get_watchlist,
    remove_from_watchlist,
    add_price_alert,
    get_active_price_alerts,
)
from backend.core.logger import get_logger

logger = get_logger(__name__)

SYMBOL_MAP = {
    # Common names -> Tickers
    "apple": "AAPL",
    "nvidia": "NVDA",
    "tesla": "TSLA",
    "microsoft": "MSFT",
    "google": "GOOGL",
    "amazon": "AMZN",
    "meta": "META",
    "netflix": "NFLX",
    # Indian stocks (NSE)
    "reliance": "RELIANCE.NS",
    "tcs": "TCS.NS",
    "infosys": "INFY.NS",
    "infy": "INFY.NS",
    "hdfc": "HDFCBANK.NS",
    "hdfc bank": "HDFCBANK.NS",
    "tata motors": "TATAMOTORS.NS",
    "tata steel": "TATASTEEL.NS",
    "tata capital": "TATACAP.NS",
    "sbi": "SBIN.NS",
    "icici": "ICICIBANK.NS",
    "wipro": "WIPRO.NS",
    # Indices & Crypto
    "nifty": "^NSEI",
    "nifty 50": "^NSEI",
    "sensex": "^BSESN",
    "s&p 500": "^GSPC",
    "sp500": "^GSPC",
    "nasdaq": "^IXIC",
    "bitcoin": "BTC-USD",
    "btc": "BTC-USD",
    "ethereum": "ETH-USD",
    "eth": "ETH-USD",
}


def _resolve_ticker(query: str) -> str:
    q = query.lower().strip()
    for w in ["stock", "price", "share", "crypto", "token", "what is", "how is", "track", "what's"]:
        q = q.replace(w, "").strip()

    if q in SYMBOL_MAP:
        return SYMBOL_MAP[q]
    if q.endswith((".ns", ".bo")):
        return q.upper()
    return q.upper()


def fetch_quote(ticker: str) -> dict | None:
    """Fetch live quote from Yahoo Finance public v8 API."""
    try:
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?interval=1d&range=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=6)
        if resp.status_code == 200:
            data = resp.json()
            meta = data["chart"]["result"][0]["meta"]
            price = meta.get("regularMarketPrice", 0.0)
            prev_close = meta.get("chartPreviousClose", meta.get("previousClose", price))
            currency = meta.get("currency", "USD")
            symbol = meta.get("symbol", ticker)

            change = price - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0.0

            return {
                "symbol": symbol,
                "price": round(price, 2),
                "change": round(change, 2),
                "change_pct": round(change_pct, 2),
                "currency": currency,
                "prev_close": round(prev_close, 2),
            }
    except Exception as e:
        logger.warning(f"Failed to fetch quote for {ticker}: {e}")
    return None


@register_tool(
    name="get_stock_price",
    description="Get current market price, daily change, and percentage for any stock, index, or cryptocurrency.",
    parameters={"symbol": {"type": "string", "description": "Company name or ticker symbol (e.g. Nvidia, Apple, Reliance, Nifty 50, Bitcoin)"}},
    risk_level="low",
    category="finance",
)
def get_stock_price(symbol: str) -> str:
    ticker = _resolve_ticker(symbol)
    quote = fetch_quote(ticker)
    if not quote:
        if not ticker.endswith((".NS", "-USD", "^")):
            quote = fetch_quote(f"{ticker}.NS")

    if not quote:
        return f"Sorry, I could not retrieve financial data for '{symbol}'."

    curr_sym = "INR " if quote["currency"] == "INR" else ("USD " if quote["currency"] == "USD" else f"{quote['currency']} ")
    direction = "up" if quote["change"] >= 0 else "down"
    sign = "+" if quote["change"] >= 0 else ""

    return (
        f"{quote['symbol']}: {curr_sym}{quote['price']:,.2f} "
        f"({direction} {sign}{quote['change']:,.2f} / {sign}{quote['change_pct']}%) today."
    )


@register_tool(
    name="track_stock",
    description="Add a stock or cryptocurrency to your background tracking watchlist.",
    parameters={"symbol": {"type": "string", "description": "Ticker symbol or company name"}},
    risk_level="low",
    category="finance",
)
def track_stock(symbol: str) -> str:
    ticker = _resolve_ticker(symbol)
    quote = fetch_quote(ticker)
    name = quote["symbol"] if quote else ticker

    add_to_watchlist(symbol=ticker, name=name)
    return f"Added {name} to your stock watchlist."


@register_tool(
    name="list_watchlist",
    description="List all tracked stocks in your watchlist with current prices.",
    parameters={},
    risk_level="low",
    category="finance",
)
def list_watchlist() -> str:
    items = get_watchlist()
    if not items:
        return "Your stock watchlist is currently empty. Say 'Track Nvidia' to add stocks."

    lines = []
    for item in items:
        sym = item["symbol"]
        quote = fetch_quote(sym)
        if quote:
            curr_sym = "INR " if quote["currency"] == "INR" else "USD "
            sign = "+" if quote["change"] >= 0 else ""
            lines.append(f"- {sym}: {curr_sym}{quote['price']:,.2f} ({sign}{quote['change_pct']}%)")
        else:
            lines.append(f"- {sym}")

    return "Your Tracked Watchlist:\n" + "\n".join(lines)


@register_tool(
    name="create_price_alert",
    description="Set an alert for when a stock crosses above or below a target price.",
    parameters={
        "symbol": {"type": "string", "description": "Stock or crypto symbol"},
        "target_price": {"type": "number", "description": "Target price trigger"},
        "condition": {"type": "string", "description": "'above' or 'below'", "default": "above"},
    },
    risk_level="low",
    category="finance",
)
def create_price_alert(symbol: str, target_price: float, condition: str = "above") -> str:
    ticker = _resolve_ticker(symbol)
    cond = "above" if "above" in condition.lower() or "over" in condition.lower() else "below"
    a_id = add_price_alert(symbol=ticker, target_price=target_price, condition=cond)
    return f"Price alert #{a_id} created: Alert when {ticker} goes {cond} {target_price}."
