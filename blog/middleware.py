from __future__ import annotations

from django.db.models import F

from .models import SiteStat


class SiteStatsMiddleware:
    """Very lightweight visitor counting.

    Counts a "visitor" once per session.
    """

    SESSION_FLAG = "uzwire_counted_visitor"

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = getattr(request, "path", "") or ""

        should_count = True
        if path.startswith("/static/"):
            should_count = False
        elif path.startswith("/admin/"):
            should_count = False
        elif path.startswith("/api/"):
            should_count = False
        elif path.startswith("/i18n/"):
            should_count = False
        elif path.startswith("/robots.txt") or path.startswith("/sitemap.xml"):
            should_count = False

        if should_count:
            try:
                session = request.session
                if not session.get(self.SESSION_FLAG):
                    SiteStat.objects.get_or_create(key="visitors")
                    SiteStat.objects.filter(key="visitors").update(value=F("value") + 1)
                    session[self.SESSION_FLAG] = True
            except Exception:
                # Never block the request for stats.
                pass

        return self.get_response(request)
