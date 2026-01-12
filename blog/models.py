from django.db import models
from django.urls import reverse


class BlogPostQuerySet(models.QuerySet):
	def published(self):
		return self.filter(status="published", published_at__isnull=False)


class BlogPost(models.Model):
	class Status(models.TextChoices):
		DRAFT = "draft", "Draft"
		PUBLISHED = "published", "Published"

	title = models.CharField(max_length=200)
	slug = models.SlugField(max_length=220, unique=True)
	excerpt = models.TextField(blank=True)
	body = models.TextField()
	status = models.CharField(
		max_length=12,
		choices=Status.choices,
		default=Status.DRAFT,
	)
	published_at = models.DateTimeField(null=True, blank=True)
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	objects = BlogPostQuerySet.as_manager()

	class Meta:
		ordering = ["-published_at", "-created_at"]

	def __str__(self) -> str:
		return self.title

	def get_absolute_url(self):
		return reverse("blog:detail", kwargs={"slug": self.slug})
