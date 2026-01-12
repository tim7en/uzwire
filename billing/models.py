from __future__ import annotations

from datetime import date

from django.conf import settings
from django.db import models

from .features import PLAN_FREE, is_active, plan_has_feature


class Account(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="billing_account",
    )
    plan = models.CharField(max_length=32, default=PLAN_FREE.code)
    paid_until = models.DateField(null=True, blank=True)
    balance_cents = models.BigIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Account(user={self.user_id}, plan={self.plan})"

    @property
    def is_paid_active(self) -> bool:
        return is_active(self.paid_until)

    def has_feature(self, feature: str) -> bool:
        if self.plan == PLAN_FREE.code:
            return False
        if not self.is_paid_active:
            return False
        return plan_has_feature(self.plan, feature)


class Payment(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="payments",
    )
    provider = models.CharField(max_length=64, blank=True, default="")
    reference = models.CharField(max_length=128, blank=True, default="")
    currency = models.CharField(max_length=8, default="UZS")
    amount_cents = models.BigIntegerField()
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.PENDING,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Payment(user={self.user_id}, amount={self.amount_cents}{self.currency}, status={self.status})"


def get_or_create_account(user) -> Account:
    account, _ = Account.objects.get_or_create(user=user)
    return account


def set_plan(user, *, plan: str, paid_until: date | None) -> Account:
    account = get_or_create_account(user)
    account.plan = plan
    account.paid_until = paid_until
    account.save(update_fields=["plan", "paid_until", "updated_at"])
    return account
