import math
import re

from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from django_core.models import AbstractBaseModel

User = get_user_model()


class BlogPostModel(AbstractBaseModel):
    """Blog posti — Markdown ko'rinishida yoziladi, publik saytda ko'rsatiladi."""

    title = models.CharField(verbose_name=_("title"), max_length=255)
    slug = models.SlugField(
        verbose_name=_("slug"),
        max_length=280,
        unique=True,
        blank=True,
        help_text=_("Sarlavhadan avtomatik hosil bo'ladi"),
    )
    excerpt = models.CharField(
        verbose_name=_("excerpt"),
        max_length=500,
        blank=True,
        help_text=_("Qisqa tavsif (ro'yxat kartochkalarida ko'rsatiladi)"),
    )
    content = models.TextField(verbose_name=_("content"), help_text=_("Markdown matni"))
    cover_image = models.URLField(
        verbose_name=_("cover image"),
        max_length=1000,
        blank=True,
        null=True,
        help_text=_("Muqova rasmi havolasi (ixtiyoriy)"),
    )
    is_published = models.BooleanField(verbose_name=_("is published"), default=False, db_index=True)
    author = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="blog_posts",
        verbose_name=_("author"),
    )
    published_at = models.DateTimeField(verbose_name=_("published at"), null=True, blank=True)

    class Meta:
        db_table = "blog_post"
        verbose_name = _("Blog Post")
        verbose_name_plural = _("Blog Posts")
        ordering = ["-published_at", "-created_at"]

    def __str__(self):
        return self.title

    def _unique_slug(self):
        """Sarlavhadan noyob slug hosil qiladi (band bo'lsa -2, -3 ... qo'shadi)."""
        base = slugify(self.title) or "post"
        slug = base
        counter = 2
        qs = BlogPostModel.objects.exclude(pk=self.pk)
        while qs.filter(slug=slug).exists():
            slug = f"{base}-{counter}"
            counter += 1
        return slug

    @property
    def reading_time(self):
        """Taxminiy o'qish vaqti (daqiqa) — ~200 so'z/daqiqa."""
        words = len(re.findall(r"\w+", self.content or ""))
        return max(1, math.ceil(words / 200))

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        # Birinchi marta publish qilinganda published_at ni o'rnatamiz.
        if self.is_published and self.published_at is None:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
