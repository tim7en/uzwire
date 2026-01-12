from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import get_or_create_account


@login_required
def account(request):
    acct = get_or_create_account(request.user)
    return render(request, "billing/account.html", {"acct": acct})
