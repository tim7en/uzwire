from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, render
from django.utils import timezone

from .models import BlogPost
from .models import SiteStat
from billing.models import Account
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

	user_model = get_user_model()
	try:
		site_users_count = user_model.objects.count()
	except Exception:
		site_users_count = None

	try:
		today = timezone.now().date()
		site_members_count = Account.objects.filter(paid_until__gte=today).count()
	except Exception:
		site_members_count = 0

	try:
		stat, _ = SiteStat.objects.get_or_create(key="visitors")
		site_visitors_count = stat.value
	except Exception:
		site_visitors_count = 0

	return render(
		request,
		"blog/index.html",
		{
			"news_items": news_items,
			"market_rows": market_rows,
			"latest": latest,
			"posts": posts,
			"site_users_count": site_users_count,
			"site_members_count": site_members_count,
			"site_visitors_count": site_visitors_count,
		},
	)


def detail(request, slug: str):
	post = get_object_or_404(BlogPost.objects.published(), slug=slug)
	return render(request, "blog/detail.html", {"post": post})
