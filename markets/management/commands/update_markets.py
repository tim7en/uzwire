from __future__ import annotations

from datetime import datetime, timezone

from django.core.management.base import BaseCommand

from markets.services import (
    fetch_coingecko_chart,
    fetch_fear_greed_altme,
    fetch_fx_rates_to_uzs,
    fetch_stooq_history,
    persist_latest_from_points,
    persist_points,
)


class Command(BaseCommand):
    help = "Fetch and persist market series/latest values (best-effort)."

    def handle(self, *args, **options):
        started = datetime.now(timezone.utc)

        # Crypto (CoinGecko) – store as daily points (UTC dates)
        crypto = {
            "BTC": ("bitcoin", "Crypto", "Bitcoin"),
            "ETH": ("ethereum", "Crypto", "Ethereum"),
        }
        for instrument, (coin_id, category, name) in crypto.items():
            try:
                series = fetch_coingecko_chart(coin_id=coin_id, days=30)
                daily = []
                for ts_ms, price in series:
                    d = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).date()
                    daily.append((d, float(price)))
                # Dedup dates (keep last)
                dedup = {}
                for d, v in daily:
                    dedup[d] = v
                points = sorted(dedup.items(), key=lambda t: t[0])
                persist_points(instrument, points)
                persist_latest_from_points(instrument, category, name)
                self.stdout.write(self.style.SUCCESS(f"Updated {instrument} ({len(points)} points)"))
            except Exception as e:
                self.stderr.write(f"WARN: {instrument} failed: {e}")

        # Stooq historical (daily)
        # Note: symbol availability varies; best-effort.
        stooq = {
            "SPX": ("^spx", "Indexes", "S&P 500"),
            "NDX": ("^ndx", "Indexes", "Nasdaq 100"),
            "VIX": ("^vix", "Volatility", "VIX"),
            "XAU": ("xauusd", "Commodities", "Gold"),
            "XAG": ("xagusd", "Commodities", "Silver"),
        }
        for instrument, (symbol, category, name) in stooq.items():
            try:
                points = fetch_stooq_history(symbol=symbol, days=45)
                if not points:
                    self.stderr.write(f"WARN: {instrument} no data")
                    continue
                # Keep last 30-ish points
                points = points[-35:]
                persist_points(instrument, points)
                persist_latest_from_points(instrument, category, name)
                self.stdout.write(self.style.SUCCESS(f"Updated {instrument} ({len(points)} points)"))
            except Exception as e:
                self.stderr.write(f"WARN: {instrument} failed: {e}")

        # FX rates to UZS (store as latest only)
        try:
            fx = fetch_fx_rates_to_uzs()
            # Persist as 1-point series at today's date so it can be charted if desired.
            today = datetime.now(timezone.utc).date()
            for ccy in ("USD", "EUR", "RUB"):
                if ccy not in fx:
                    continue
                inst = f"{ccy}UZS"
                persist_points(inst, [(today, float(fx[ccy]))])
                persist_latest_from_points(inst, "FX", f"{ccy}/UZS")
            self.stdout.write(self.style.SUCCESS("Updated FX UZS"))
        except Exception as e:
            self.stderr.write(f"WARN: FX failed: {e}")

        # Fear & Greed (crypto) – Alternative.me
        try:
            points = fetch_fear_greed_altme(days=60)
            points = points[-45:]
            persist_points("FNG", points)
            persist_latest_from_points("FNG", "Sentiment", "Fear & Greed (Crypto)")
            self.stdout.write(self.style.SUCCESS(f"Updated FNG ({len(points)} points)"))
        except Exception as e:
            self.stderr.write(f"WARN: FNG failed: {e}")

        elapsed = (datetime.now(timezone.utc) - started).total_seconds()
        self.stdout.write(self.style.SUCCESS(f"Done in {elapsed:.1f}s"))
