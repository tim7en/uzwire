from django.shortcuts import get_object_or_404, render

from .models import BlogPost
from news.services import fetch_news
from markets.models import MarketLatest
from markets.services import get_market_snapshot


def home(request):
	qs = BlogPost.objects.published()
	latest = qs.first()
	posts = qs[1:] if latest else qs
	try:
		news_items = fetch_news(limit=12)
	except Exception:
		news_items = []
	try:
		latest_rows = list(MarketLatest.objects.all().order_by("category", "name"))
		market_rows = latest_rows if latest_rows else get_market_snapshot()
	except Exception:
		market_rows = []
	return render(
		request,
		"blog/index.html",
		{
			"news_items": news_items,
			"market_rows": market_rows,
			"latest": latest,
			"posts": posts,
		},
	)


def detail(request, slug: str):
	post = get_object_or_404(BlogPost.objects.published(), slug=slug)
	return render(request, "blog/detail.html", {"post": post})
