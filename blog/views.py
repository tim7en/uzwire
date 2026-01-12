from django.shortcuts import get_object_or_404, render

from .models import BlogPost
from news.services import fetch_news


def home(request):
	qs = BlogPost.objects.published()
	latest = qs.first()
	posts = qs[1:] if latest else qs
	news_items = fetch_news(limit=12)
	return render(
		request,
		"blog/index.html",
		{
			"news_items": news_items,
			"latest": latest,
			"posts": posts,
		},
	)


def detail(request, slug: str):
	post = get_object_or_404(BlogPost.objects.published(), slug=slug)
	return render(request, "blog/detail.html", {"post": post})
