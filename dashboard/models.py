from __future__ import annotations

from django.conf import settings
from django.db import models


class Portfolio(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=120)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Portfolio(user={self.user_id}, name={self.name})"


class PortfolioItem(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="items")
    symbol = models.CharField(max_length=32)
    weight = models.FloatField(help_text="Weight as percentage (0-100)")

    class Meta:
        unique_together = ("portfolio", "symbol")
        indexes = [models.Index(fields=["portfolio", "symbol"])]

    def __str__(self) -> str:
        return f"{self.portfolio_id}:{self.symbol}={self.weight}%"
