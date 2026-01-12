from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils import translation

from blog.models import BlogPost


LANG_CODES = ("en", "ru", "uz")


class StaticViewSitemap(Sitemap):
    priority = 1.0
    changefreq = "daily"

    def items(self):
        items = []
        for lang in LANG_CODES:
            items.append(("blog:home", lang))
            items.append(("news:feed", lang))
        return items

    def location(self, item):
        viewname, lang = item
        with translation.override(lang):
            return reverse(viewname)


class BlogPostSitemap(Sitemap):
    priority = 0.7
    changefreq = "weekly"

    def items(self):
        items = []
        for post in BlogPost.objects.published():
            for lang in LANG_CODES:
                items.append((post, lang))
        return items

    def location(self, item):
        post, lang = item
        with translation.override(lang):
            return reverse("blog:detail", kwargs={"slug": post.slug})
