from __future__ import annotations

from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse
from django.shortcuts import redirect
from django.utils.translation import gettext as _

from .models import get_or_create_account


def require_feature(feature: str):
    """Gate a view by a paid feature flag stored on the user's Account."""

    def decorator(view_func):
        @login_required
        @wraps(view_func)
        def wrapped(request: HttpRequest, *args, **kwargs) -> HttpResponse:
            acct = get_or_create_account(request.user)
            if acct.has_feature(feature):
                return view_func(request, *args, **kwargs)
            messages.error(request, _("This feature requires a paid plan."))
            return redirect("billing:account")

        return wrapped

    return decorator
