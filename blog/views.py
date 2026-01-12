from django.shortcuts import get_object_or_404, render

from .models import BlogPost


def home(request):
	qs = BlogPost.objects.published()
	latest = qs.first()
	posts = qs[1:] if latest else qs
	return render(
		request,
		"blog/index.html",
		{
			"latest": latest,
			"posts": posts,
		},
	)


def detail(request, slug: str):
	post = get_object_or_404(BlogPost.objects.published(), slug=slug)
	return render(request, "blog/detail.html", {"post": post})
