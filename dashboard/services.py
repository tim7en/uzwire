from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

from django.core.cache import cache

from markets.services import fetch_stooq_history


@dataclass(frozen=True)
class Allocation:
    symbol: str
    weight: float  # 0..1


def normalize_allocations(items: Iterable[tuple[str, float]]) -> list[Allocation]:
    cleaned: list[tuple[str, float]] = []
    for sym, w in items:
        sym = (sym or "").strip()
        if not sym:
            continue
        try:
            wv = float(w)
        except Exception:
            continue
        if wv <= 0:
            continue
        cleaned.append((sym, wv))

    total = sum(w for _, w in cleaned)
    if total <= 0:
        return []

    out: list[Allocation] = []
    for sym, w in cleaned:
        out.append(Allocation(symbol=sym, weight=w / total))
    return out


def fetch_history_cached(symbol: str, days: int) -> list[tuple[date, float]]:
    symbol = symbol.strip().lower()
    days = int(days)
    days = max(2, min(days, 9000))
    cache_key = f"stooq:v1:hist:{symbol}:{days}"
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    series = fetch_stooq_history(symbol=symbol, days=days)
    cache.set(cache_key, series, timeout=6 * 60 * 60)
    return series


def _returns_from_prices(series: list[tuple[date, float]]) -> dict[date, float]:
    out: dict[date, float] = {}
    prev = None
    for d, px in series:
        if prev is None:
            prev = px
            continue
        if prev and px and prev > 0:
            out[d] = (px / prev) - 1.0
        prev = px
    return out


def backtest_weighted_index(
    allocations: list[Allocation],
    *,
    days: int,
) -> list[tuple[date, float]]:
    """Build a daily index series starting at 100."""

    if not allocations:
        return []

    returns_by_symbol: dict[str, dict[date, float]] = {}
    common_dates: set[date] | None = None

    for a in allocations:
        hist = fetch_history_cached(a.symbol, days)
        rets = _returns_from_prices(hist)
        returns_by_symbol[a.symbol] = rets
        dates = set(rets.keys())
        common_dates = dates if common_dates is None else (common_dates & dates)

    if not common_dates:
        return []

    dates_sorted = sorted(common_dates)
    value = 100.0
    out: list[tuple[date, float]] = []
    for d in dates_sorted:
        daily = 0.0
        for a in allocations:
            r = returns_by_symbol.get(a.symbol, {}).get(d)
            if r is None:
                daily = None
                break
            daily += a.weight * r
        if daily is None:
            continue
        value *= (1.0 + daily)
        out.append((d, value))

    return out


def total_return(series: list[tuple[date, float]]) -> float | None:
    if len(series) < 2:
        return None
    start = series[0][1]
    end = series[-1][1]
    if start <= 0:
        return None
    return (end / start) - 1.0


PRESET_PORTFOLIOS: dict[str, dict] = {
    # Stooq US symbols are usually like "smh.us" or "aapl.us".
    "semi": {
        "label": "Semiconductors",
        "items": [("smh.us", 1.0)],
    },
    "banking": {
        "label": "Banking",
        "items": [("xlf.us", 1.0)],
    },
    "energy": {
        "label": "Energy",
        "items": [("xle.us", 1.0)],
    },
    "green": {
        "label": "Green energy",
        "items": [("icln.us", 1.0)],
    },
    "staples": {
        "label": "Consumer staples",
        "items": [("xlp.us", 1.0)],
    },
    "healthcare": {
        "label": "Healthcare",
        "items": [("xlv.us", 1.0)],
    },
}
