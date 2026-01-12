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
from .services import PRESET_PORTFOLIOS, backtest_weighted_index, normalize_allocations, total_return


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
    allocations = normalize_allocations(PRESET_PORTFOLIOS["semi"]["items"])

    if selected_portfolio and portfolio_items:
        allocations = normalize_allocations([(it.symbol, it.weight) for it in portfolio_items])

    days_15y = 4200
    series = backtest_weighted_index(allocations, days=days_15y)

    def slice_last(n: int):
        if len(series) < n:
            return None
        return series[-n:]

    horizons = {
        "5y": 1260,
        "10y": 2520,
        "15y": 3780,
    }

    portfolio_backtests = {
        k: {
            "days": v,
            "total_return": total_return(slice_last(v) or []),
        }
        for k, v in horizons.items()
    }

    # Benchmarks (best-effort)
    spx = backtest_weighted_index(normalize_allocations([("^spx", 1.0)]), days=days_15y)
    ndx = backtest_weighted_index(normalize_allocations([("^ndx", 1.0)]), days=days_15y)

    bench = {
        "spx": {k: {"total_return": total_return((spx[-v:] if len(spx) >= v else []) )} for k, v in horizons.items()},
        "ndx": {k: {"total_return": total_return((ndx[-v:] if len(ndx) >= v else []) )} for k, v in horizons.items()},
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
            "form": form,
            "presets": PRESET_PORTFOLIOS,
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
    if not pid:
        return JsonResponse({"error": "missing portfolio"}, status=400)

    try:
        p = Portfolio.objects.get(id=int(pid), user=request.user)
    except Exception:
        return JsonResponse({"error": "not found"}, status=404)

    items = list(p.items.all())
    allocs = normalize_allocations([(it.symbol, it.weight) for it in items])

    days = int(request.GET.get("days", "1260"))
    days = max(30, min(days, 4200))
    series = backtest_weighted_index(allocs, days=days)

    return JsonResponse(
        {
            "portfolio": p.id,
            "days": days,
            "series": [{"t": int(datetime.combine(d, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000), "p": v} for d, v in series],
        }
    )
