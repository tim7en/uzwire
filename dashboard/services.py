from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Iterable

import math

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


def cagr(series: list[tuple[date, float]]) -> float | None:
    if len(series) < 2:
        return None
    d0, v0 = series[0]
    d1, v1 = series[-1]
    if v0 <= 0 or v1 <= 0:
        return None
    years = max(0.0001, (d1 - d0).days / 365.25)
    return (v1 / v0) ** (1.0 / years) - 1.0


def max_drawdown(series: list[tuple[date, float]]) -> float | None:
    if len(series) < 2:
        return None
    peak = series[0][1]
    if peak <= 0:
        return None
    mdd = 0.0
    for _d, v in series:
        if v > peak:
            peak = v
            continue
        if peak > 0:
            dd = (v / peak) - 1.0
            if dd < mdd:
                mdd = dd
    return mdd


def annualized_volatility(series: list[tuple[date, float]]) -> float | None:
    if len(series) < 3:
        return None
    rets: list[float] = []
    prev = series[0][1]
    for _d, v in series[1:]:
        if prev and v and prev > 0:
            rets.append((v / prev) - 1.0)
        prev = v
    if len(rets) < 2:
        return None
    mean = sum(rets) / len(rets)
    var = sum((r - mean) ** 2 for r in rets) / (len(rets) - 1)
    return math.sqrt(var) * math.sqrt(252.0)


def correlation(a: list[tuple[date, float]], b: list[tuple[date, float]]) -> float | None:
    """Pearson correlation of daily returns between two index series."""

    if len(a) < 3 or len(b) < 3:
        return None

    def _ret_map(series: list[tuple[date, float]]) -> dict[date, float]:
        out: dict[date, float] = {}
        prev = None
        for d, v in series:
            if prev is None:
                prev = v
                continue
            if prev and v and prev > 0:
                out[d] = (v / prev) - 1.0
            prev = v
        return out

    ra = _ret_map(a)
    rb = _ret_map(b)
    common = sorted(set(ra.keys()) & set(rb.keys()))
    if len(common) < 5:
        return None

    xs = [ra[d] for d in common]
    ys = [rb[d] for d in common]

    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx <= 0 or vy <= 0:
        return None
    cov = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    return cov / math.sqrt(vx * vy)


def best_worst_month(series: list[tuple[date, float]]) -> dict[str, object] | None:
    """Return best/worst calendar-month total returns based on month endpoints."""

    if len(series) < 25:
        return None

    # Keep the last value per month.
    month_last: dict[tuple[int, int], tuple[date, float]] = {}
    for d, v in series:
        key = (d.year, d.month)
        month_last[key] = (d, v)

    # Need previous month endpoint to compute returns.
    months = sorted(month_last.keys())
    if len(months) < 2:
        return None

    best = None
    worst = None
    prev_key = months[0]
    prev_d, prev_v = month_last[prev_key]

    for key in months[1:]:
        d, v = month_last[key]
        if prev_v and v and prev_v > 0:
            r = (v / prev_v) - 1.0
            item = {"year": key[0], "month": key[1], "date": d, "return": r}
            if best is None or r > best["return"]:
                best = item
            if worst is None or r < worst["return"]:
                worst = item
        prev_d, prev_v = d, v

    if best is None or worst is None:
        return None
    return {"best": best, "worst": worst}


def max_drawdown_window(series: list[tuple[date, float]]) -> dict[str, object] | None:
    """Max drawdown with peak/trough dates (drawdown is negative)."""

    if len(series) < 2:
        return None
    peak_d, peak_v = series[0]
    if peak_v <= 0:
        return None

    best_dd = 0.0
    best_peak = peak_d
    best_trough = peak_d

    for d, v in series:
        if v > peak_v:
            peak_d, peak_v = d, v
            continue
        if peak_v > 0:
            dd = (v / peak_v) - 1.0
            if dd < best_dd:
                best_dd = dd
                best_peak = peak_d
                best_trough = d

    return {
        "drawdown": best_dd,
        "peak_date": best_peak,
        "trough_date": best_trough,
    }


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
