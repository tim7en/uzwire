from __future__ import annotations

from datetime import datetime, timezone

from django.http import JsonResponse

from .models import MarketLatest, MarketPoint
from .services import fetch_coingecko_chart, get_fx_rates_to_uzs, get_market_snapshot


def snapshot(request):
	latest = list(MarketLatest.objects.all().order_by("category", "name"))
	if latest:
		rows = latest
		as_of = latest[0].as_of.isoformat() if latest and latest[0].as_of else None
		return JsonResponse(
			{
				"as_of": as_of,
				"rows": [
					{
						"category": r.category,
						"name": r.name,
						"symbol": r.instrument,
						"price": r.price,
						"change_pct": r.change_pct,
					}
					for r in rows
				],
			}
		)

	# Fallback for first boot / no persisted data yet
	rows = get_market_snapshot()
	return JsonResponse(
		{
			"as_of": rows[0].as_of.isoformat() if rows else None,
			"rows": [
				{
					"category": r.category,
					"name": r.name,
					"symbol": r.symbol,
					"price": r.price,
					"change_pct": r.change_pct,
				}
				for r in rows
			],
		}
	)


def crypto_chart(request, coin_id: str):
	days = int(request.GET.get("days", "30"))
	days = max(1, min(days, 365))
	series = fetch_coingecko_chart(coin_id=coin_id, days=days)
	return JsonResponse(
		{
			"coin_id": coin_id,
			"days": days,
			"series": [{"t": ts, "p": price} for ts, price in series],
		}
	)


def ticker(request):
	items = []
	latest = list(MarketLatest.objects.all().order_by("category", "name"))
	if latest:
		for r in latest:
			if r.price is None:
				continue
			items.append(
				{
					"category": r.category,
					"name": r.name,
					"symbol": r.instrument,
					"price": r.price,
					"change_pct": r.change_pct,
				}
			)
		return JsonResponse(
			{
				"as_of": latest[0].as_of.isoformat() if latest[0].as_of else None,
				"items": items,
			}
		)

	# Fallback: old on-demand snapshot + FX cache
	rows = get_market_snapshot()
	fx = get_fx_rates_to_uzs()
	for r in rows:
		if r.price is None:
			continue
		items.append({"category": r.category, "name": r.name, "symbol": r.symbol, "price": r.price, "change_pct": r.change_pct})
	if fx.get("USD"):
		items.append({"category": "FX", "name": "USD/UZS", "symbol": "USDUZS", "price": fx["USD"], "change_pct": None})
	if fx.get("EUR"):
		items.append({"category": "FX", "name": "EUR/UZS", "symbol": "EURUZS", "price": fx["EUR"], "change_pct": None})
	if fx.get("RUB"):
		items.append({"category": "FX", "name": "RUB/UZS", "symbol": "RUBUZS", "price": fx["RUB"], "change_pct": None})
	return JsonResponse({"as_of": rows[0].as_of.isoformat() if rows else None, "items": items})


def series(request, instrument: str):
	days = int(request.GET.get("days", "30"))
	days = max(1, min(days, 365))
	qs = MarketPoint.objects.filter(instrument=instrument, value__isnull=False).order_by("-date")[:days]
	points = list(reversed(list(qs)))
	return JsonResponse(
		{
			"instrument": instrument,
			"days": days,
			"series": [
				{"t": int(datetime.combine(p.date, datetime.min.time(), tzinfo=timezone.utc).timestamp() * 1000), "p": p.value}
				for p in points
			],
		}
	)
