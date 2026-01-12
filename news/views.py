from django.shortcuts import render

from .services import fetch_news


def feed(request):
	items = fetch_news(limit=60)
	return render(request, "news/feed.html", {"items": items})
