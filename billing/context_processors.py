from __future__ import annotations

from .models import get_or_create_account


def billing_account(request):
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    return {"billing_account": get_or_create_account(user)}
