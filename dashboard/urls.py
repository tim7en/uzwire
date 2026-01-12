from django.urls import path

from . import views

app_name = "dashboard"

urlpatterns = [
    path("app/", views.home, name="home"),
    path("app/portfolio/create/", views.create_portfolio, name="create_portfolio"),
    path("api/app/portfolio/series/", views.portfolio_series, name="portfolio_series"),
]
