"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.http import HttpResponse
from django.urls import include, path

from .sitemaps import BlogPostSitemap, StaticViewSitemap


sitemaps = {
    "static": StaticViewSitemap,
    "posts": BlogPostSitemap,
}


def robots_txt(_request):
    content = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            f"Sitemap: {_request.build_absolute_uri('/sitemap.xml')}",
        ]
    )
    content += "\n"
    return HttpResponse(content, content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("robots.txt", robots_txt, name="robots_txt"),
    path(
        "sitemap.xml",
        sitemap,
        {"sitemaps": sitemaps},
        name="django.contrib.sitemaps.views.sitemap",
    ),
    path("", include("markets.urls")),
]


urlpatterns += i18n_patterns(
    path("", include("dashboard.urls")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("accounts/", include("accounts.urls")),
    path("", include("billing.urls")),
    path("", include("news.urls")),
    path("", include("blog.urls")),
    prefix_default_language=False,
)
