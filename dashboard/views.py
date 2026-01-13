from __future__ import annotations

from datetime import datetime, timezone

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_GET, require_POST

from markets.models import MarketLatest

from .forms import CreatePortfolioForm
from .models import Portfolio, PortfolioItem
from .services import (
    PRESET_PORTFOLIOS,
    annualized_volatility,
    backtest_weighted_index,
    best_worst_month,
    cagr,
    correlation,
    max_drawdown,
    max_drawdown_window,
    normalize_allocations,
    total_return,
)


def _parse_custom_lines(text: str) -> list[tuple[str, float]]:
    out: list[tuple[str, float]] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
        sym = parts[0]
        try:
            w = float(parts[1])
        except Exception:
            continue
        out.append((sym, w))
    return out


@login_required
def home(request):
    latest = list(MarketLatest.objects.all().order_by("category", "name")[:12])

    portfolios = list(Portfolio.objects.filter(user=request.user).order_by("-created_at")[:5])

    selected_portfolio = None
    portfolio_items: list[PortfolioItem] = []
    portfolio_backtests = None

    pid = request.GET.get("portfolio")
    if pid:
        try:
            selected_portfolio = Portfolio.objects.get(id=int(pid), user=request.user)
            portfolio_items = list(selected_portfolio.items.all())
        except Exception:
            selected_portfolio = None

    # Default backtest: Semiconductor preset
    selected_preset = request.GET.get("preset") or "semi"
    if selected_preset not in PRESET_PORTFOLIOS:
        selected_preset = "semi"
    allocations = normalize_allocations(PRESET_PORTFOLIOS[selected_preset]["items"])

    if selected_portfolio and portfolio_items:
        allocations = normalize_allocations([(it.symbol, it.weight) for it in portfolio_items])

    days_15y = 4200
    series = backtest_weighted_index(allocations, days=days_15y)

    def pct(x):
        return (x * 100.0) if x is not None else None

    def slice_last(n: int):
        if len(series) < n:
            return None
        return series[-n:]

    horizons = {
        "5y": 1260,
        "10y": 2520,
        "15y": 3780,
    }

    def what_if_row(s, days: int):
        # assumes index series starting at 100
        seg = s[-days:] if s and len(s) >= days else []
        tr = total_return(seg)
        cg = cagr(seg)
        end_value = None
        if tr is not None:
            end_value = 10000.0 * (1.0 + tr)
        return {
            "days": days,
            "total_return": tr,
            "cagr": cg,
            "total_return_pct": pct(tr),
            "cagr_pct": pct(cg),
            "end_value": end_value,
        }

    portfolio_backtests = {k: what_if_row(series, v) for k, v in horizons.items()}

    # Benchmarks (more reliable proxies)
    spx = backtest_weighted_index(normalize_allocations([("spy.us", 1.0)]), days=days_15y)
    ndx = backtest_weighted_index(normalize_allocations([("qqq.us", 1.0)]), days=days_15y)

    bench = {
        "spx": {k: what_if_row(spx, v) for k, v in horizons.items()},
        "ndx": {k: what_if_row(ndx, v) for k, v in horizons.items()},
    }

    dd_info = max_drawdown_window(series)
    bw = best_worst_month(series)
    if bw:
        try:
            bw["best"]["return_pct"] = pct(bw["best"].get("return"))
            bw["worst"]["return_pct"] = pct(bw["worst"].get("return"))
        except Exception:
            pass
    insights = {
        "total_return": total_return(series),
        "cagr": cagr(series),
        "max_drawdown": max_drawdown(series),
        "vol": annualized_volatility(series),
        "total_return_pct": pct(total_return(series)),
        "cagr_pct": pct(cagr(series)),
        "max_drawdown_pct": pct(max_drawdown(series)),
        "vol_pct": pct(annualized_volatility(series)),
        "corr_spx": correlation(series, spx),
        "corr_ndx": correlation(series, ndx),
        "drawdown": dd_info,
        "best_worst_month": bw,
    }

    form = CreatePortfolioForm()

    return render(
        request,
        "dashboard/home.html",
        {
            "now": datetime.now(timezone.utc),
            "latest": latest,
            "portfolios": portfolios,
            "selected_portfolio": selected_portfolio,
            "portfolio_items": portfolio_items,
            "portfolio_backtests": portfolio_backtests,
            "benchmarks": bench,
            "insights": insights,
            "form": form,
            "presets": PRESET_PORTFOLIOS,
            "selected_preset": selected_preset,
            "selected_preset_label": PRESET_PORTFOLIOS[selected_preset]["label"],
        },
    )


@require_POST
@login_required
def create_portfolio(request):
    form = CreatePortfolioForm(request.POST)
    if not form.is_valid():
        for e in form.errors.get("__all__", []):
            messages.error(request, e)
        return redirect("dashboard:home")

    name = form.cleaned_data["name"]
    preset = form.cleaned_data.get("preset") or ""
    custom_lines = form.cleaned_data.get("custom_lines") or ""

    if preset:
        items = PRESET_PORTFOLIOS[preset]["items"]
    else:
        items = _parse_custom_lines(custom_lines)

    allocs = normalize_allocations(items)
    if not allocs:
        messages.error(request, "Could not parse holdings.")
        return redirect("dashboard:home")

    p = Portfolio.objects.create(user=request.user, name=name)
    for a in allocs:
        PortfolioItem.objects.create(portfolio=p, symbol=a.symbol, weight=round(a.weight * 100.0, 4))

    messages.success(request, "Portfolio saved.")
    return redirect(f"/app/?portfolio={p.id}")


@require_GET
@login_required
def portfolio_series(request):
    pid = request.GET.get("portfolio")
    preset = request.GET.get("preset")

    allocs = []
    portfolio_id = None
    if pid and pid.isdigit() and int(pid) > 0:
        try:
            p = Portfolio.objects.get(id=int(pid), user=request.user)
        except Exception:
            return JsonResponse({"error": "not found"}, status=404)
        items = list(p.items.all())
        allocs = normalize_allocations([(it.symbol, it.weight) for it in items])
        portfolio_id = p.id
    else:
        preset = preset or "semi"
        if preset not in PRESET_PORTFOLIOS:
            preset = "semi"
        allocs = normalize_allocations(PRESET_PORTFOLIOS[preset]["items"])
        portfolio_id = 0

    days = int(request.GET.get("days", "1260"))
    days = max(30, min(days, 4200))
    series = backtest_weighted_index(allocs, days=days)
    spx = backtest_weighted_index(normalize_allocations([("spy.us", 1.0)]), days=days)
    ndx = backtest_weighted_index(normalize_allocations([("qqq.us", 1.0)]), days=days)

    # Align by common dates for clean multi-line chart.
    map_p = {d: v for d, v in series}
    map_spx = {d: v for d, v in spx}
    map_ndx = {d: v for d, v in ndx}
    common = sorted(set(map_p.keys()) & set(map_spx.keys()) & set(map_ndx.keys()))

    return JsonResponse(
        {
            "portfolio": portfolio_id,
            "days": days,
            "series": [
                {
                    "t": int(datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000),
                    "p": map_p[d],
                    "spx": map_spx[d],
                    "ndx": map_ndx[d],
                }
                for d in common
            ],
        }
    )
