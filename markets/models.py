from __future__ import annotations

from django.db import models


class MarketPoint(models.Model):
	instrument = models.CharField(max_length=32, db_index=True)
	date = models.DateField(db_index=True)
	value = models.FloatField(null=True, blank=True)

	class Meta:
		unique_together = ("instrument", "date")
		indexes = [
			models.Index(fields=["instrument", "date"]),
		]


class MarketLatest(models.Model):
	instrument = models.CharField(max_length=32, unique=True)
	category = models.CharField(max_length=32)
	name = models.CharField(max_length=64)

	price = models.FloatField(null=True, blank=True)
	change_pct = models.FloatField(null=True, blank=True)
	as_of = models.DateTimeField(null=True, blank=True)

	class Meta:
		indexes = [
			models.Index(fields=["category", "instrument"]),
		]
