from django.urls import path

from . import views

app_name = "markets"

urlpatterns = [
    path("api/markets/snapshot/", views.snapshot, name="snapshot"),
    path("api/markets/ticker/", views.ticker, name="ticker"),
    path("api/markets/series/<str:instrument>/", views.series, name="series"),
    path("api/markets/crypto/<str:coin_id>/", views.crypto_chart, name="crypto_chart"),
]
