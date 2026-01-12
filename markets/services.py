from __future__ import annotations

import csv
import json
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from datetime import date as date_type
from typing import Any

from django.core.cache import cache
from django.db import transaction

from .models import MarketLatest, MarketPoint


@dataclass(frozen=True)
class MarketRow:
    category: str
    name: str
    symbol: str
    price: float | None
    change_pct: float | None
    as_of: datetime | None


def _http_get_json(url: str, timeout_seconds: int = 10) -> Any:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "uzwire/1.0 (+https://uzwire.uz)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _http_get_text(url: str, timeout_seconds: int = 10) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "uzwire/1.0 (+https://uzwire.uz)",
            "Accept": "text/plain,*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
        return resp.read().decode("utf-8", errors="replace")


def fetch_coingecko_prices(ids: list[str], vs_currency: str = "usd") -> dict[str, float]:
    # Public endpoint; keep calls low using caching.
    q = urllib.parse.urlencode({"ids": ",".join(ids), "vs_currencies": vs_currency})
    url = f"https://api.coingecko.com/api/v3/simple/price?{q}"
    data = _http_get_json(url)
    out: dict[str, float] = {}
    for coin_id in ids:
        try:
            out[coin_id] = float(data[coin_id][vs_currency])
        except Exception:
            continue
    return out


def fetch_coingecko_chart(coin_id: str, days: int = 30, vs_currency: str = "usd") -> list[tuple[int, float]]:
    q = urllib.parse.urlencode({"vs_currency": vs_currency, "days": str(days)})
    url = f"https://api.coingecko.com/api/v3/coins/{urllib.parse.quote(coin_id)}/market_chart?{q}"
    data = _http_get_json(url)
    prices = data.get("prices") or []
    series: list[tuple[int, float]] = []
    for point in prices:
        try:
            ts_ms = int(point[0])
            price = float(point[1])
            series.append((ts_ms, price))
        except Exception:
            continue
    return series


def fetch_stooq_quotes(symbols: list[str]) -> dict[str, dict[str, float | None]]:
    # Stooq free CSV endpoint. Symbols examples:
    # - Indexes: ^spx, ^ndx, ^dji (availability can vary)
    # - FX/metals may vary by provider; treat as best-effort.
    # Docs: https://stooq.com/q/l/
    out: dict[str, dict[str, float | None]] = {}
    for sym in symbols:
        url = f"https://stooq.com/q/l/?s={urllib.parse.quote(sym)}&f=sd2t2ohlcv&h&e=csv"
        try:
            text = _http_get_text(url)
            rows = list(csv.DictReader(text.splitlines()))
            if not rows:
                continue
            row = rows[0]
            close_str = (row.get("Close") or "").strip()
            open_str = (row.get("Open") or "").strip()
            close = float(close_str) if close_str and close_str != "N/A" else None
            open_ = float(open_str) if open_str and open_str != "N/A" else None
            change_pct = None
            if close is not None and open_ not in (None, 0):
                change_pct = (close - open_) / open_ * 100.0
            out[sym] = {"price": close, "change_pct": change_pct}
        except Exception:
            continue
    return out


def fetch_stooq_history(symbol: str, days: int = 45) -> list[tuple[date_type, float]]:
    """Fetch daily close history from Stooq.

    Returns a list of (date, close) sorted ascending.
    """

    # i=d for daily candles.
    url = f"https://stooq.com/q/d/l/?s={urllib.parse.quote(symbol)}&i=d"
    text = _http_get_text(url)
    rows = list(csv.DictReader(text.splitlines()))
    out: list[tuple[date_type, float]] = []
    for row in rows[-max(2, days):]:
        ds = (row.get("Date") or "").strip()
        close_s = (row.get("Close") or "").strip()
        if not ds or not close_s or close_s == "N/A":
            continue
        try:
            d = datetime.strptime(ds, "%Y-%m-%d").date()
            out.append((d, float(close_s)))
        except Exception:
            continue
    out.sort(key=lambda t: t[0])
    return out


def fetch_fear_greed_altme(days: int = 30) -> list[tuple[date_type, float]]:
    """Crypto Fear & Greed Index via alternative.me (free, no key)."""

    q = urllib.parse.urlencode({"limit": str(max(1, min(days, 365))), "format": "json"})
    url = f"https://api.alternative.me/fng/?{q}"
    data = _http_get_json(url)
    items = data.get("data") or []
    out: list[tuple[date_type, float]] = []
    for it in items:
        try:
            ts = int(it.get("timestamp"))
            v = float(it.get("value"))
            d = datetime.fromtimestamp(ts, tz=timezone.utc).date()
            out.append((d, v))
        except Exception:
            continue
    out.sort(key=lambda t: t[0])
    # Remove dup dates (keep last)
    dedup: dict[date_type, float] = {}
    for d, v in out:
        dedup[d] = v
    return sorted(dedup.items(), key=lambda t: t[0])


def get_market_snapshot(cache_seconds: int = 120) -> list[MarketRow]:
    cache_key = "markets:v1:snapshot"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    now = datetime.now(timezone.utc)

    # Best-effort selection: keep it minimal and robust.
    # Crypto via CoinGecko, traditional/commodities via Stooq.
    crypto_ids = ["bitcoin", "ethereum"]
    try:
        crypto_prices = fetch_coingecko_prices(crypto_ids)
    except Exception:
        crypto_prices = {}

    stooq_symbols = [
        "^spx",  # S&P 500 (may vary)
        "^ndx",  # Nasdaq 100
        "^dji",  # Dow Jones
        "xauusd",  # Gold (spot) - availability can vary
        "wti",  # Crude oil proxy (availability can vary)
    ]
    try:
        stooq = fetch_stooq_quotes(stooq_symbols)
    except Exception:
        stooq = {}

    rows: list[MarketRow] = []

    def add_row(category: str, name: str, symbol: str, price: float | None, change_pct: float | None):
        rows.append(
            MarketRow(
                category=category,
                name=name,
                symbol=symbol,
                price=price,
                change_pct=change_pct,
                as_of=now,
            )
        )

    add_row("Crypto", "Bitcoin", "BTC", crypto_prices.get("bitcoin"), None)
    add_row("Crypto", "Ethereum", "ETH", crypto_prices.get("ethereum"), None)

    add_row("Traditional", "S&P 500", "^SPX", stooq.get("^spx", {}).get("price"), stooq.get("^spx", {}).get("change_pct"))
    add_row("Traditional", "Nasdaq 100", "^NDX", stooq.get("^ndx", {}).get("price"), stooq.get("^ndx", {}).get("change_pct"))
    add_row("Traditional", "Dow Jones", "^DJI", stooq.get("^dji", {}).get("price"), stooq.get("^dji", {}).get("change_pct"))

    add_row("Commodities", "Gold", "XAUUSD", stooq.get("xauusd", {}).get("price"), stooq.get("xauusd", {}).get("change_pct"))
    add_row("Commodities", "WTI (proxy)", "WTI", stooq.get("wti", {}).get("price"), stooq.get("wti", {}).get("change_pct"))

    # Cache even partial/empty results to avoid hammering upstreams.
    cache.set(cache_key, rows, timeout=cache_seconds)
    return rows


def fetch_fx_rates_to_uzs(cache_seconds: int = 3600) -> dict[str, float]:
    """Best-effort FX rates for UZS.

    Returns a mapping like: {"USD": uzs_per_usd, "EUR": uzs_per_eur, "RUB": uzs_per_rub}
    """

    cache_key = "markets:v1:fx:uzs"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached

    out: dict[str, float] = {}
    try:
        # Free endpoint, no API key. Base USD simplifies cross-rates.
        data = _http_get_json("https://open.er-api.com/v6/latest/USD")
        rates = data.get("rates") or {}

        usd_uzs = float(rates.get("UZS")) if rates.get("UZS") else None
        usd_eur = float(rates.get("EUR")) if rates.get("EUR") else None
        usd_rub = float(rates.get("RUB")) if rates.get("RUB") else None

        if usd_uzs and usd_uzs > 0:
            out["USD"] = usd_uzs
        if usd_uzs and usd_eur and usd_eur > 0:
            out["EUR"] = usd_uzs / usd_eur
        if usd_uzs and usd_rub and usd_rub > 0:
            out["RUB"] = usd_uzs / usd_rub
    except Exception:
        out = {}

    cache.set(cache_key, out, timeout=cache_seconds)
    return out


# Backwards-compat alias
get_fx_rates_to_uzs = fetch_fx_rates_to_uzs


def persist_points(instrument: str, points: list[tuple[date_type, float]]) -> None:
    if not points:
        return

    with transaction.atomic():
        for d, v in points:
            MarketPoint.objects.update_or_create(
                instrument=instrument,
                date=d,
                defaults={"value": v},
            )


def persist_latest_from_points(instrument: str, category: str, name: str) -> None:
    qs = MarketPoint.objects.filter(instrument=instrument, value__isnull=False).order_by("-date")
    latest = qs.first()
    if not latest:
        return
    prev = qs[1] if qs.count() > 1 else None
    change_pct = None
    if prev and prev.value not in (None, 0):
        try:
            change_pct = (float(latest.value) - float(prev.value)) / float(prev.value) * 100.0
        except Exception:
            change_pct = None

    MarketLatest.objects.update_or_create(
        instrument=instrument,
        defaults={
            "category": category,
            "name": name,
            "price": latest.value,
            "change_pct": change_pct,
            "as_of": datetime.combine(latest.date, datetime.min.time(), tzinfo=timezone.utc),
        },
    )
