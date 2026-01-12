from django.urls import path

from . import views

app_name = "billing"

urlpatterns = [
    path("account/", views.account, name="account"),
]
