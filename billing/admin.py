from django.contrib import admin

from .models import Account, Payment


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("user", "plan", "paid_until", "balance_cents", "updated_at")
    list_select_related = ("user",)
    search_fields = ("user__username", "user__email")
    list_filter = ("plan",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "amount_cents", "currency", "provider", "reference", "created_at")
    list_select_related = ("user",)
    search_fields = ("user__username", "reference")
    list_filter = ("status", "currency", "provider")
