from django.contrib import admin
from unfold.admin import ModelAdmin

from core.apps.blog.models.blog import BlogPostModel


@admin.register(BlogPostModel)
class BlogPostAdmin(ModelAdmin):
    list_display = ("title", "slug", "is_published", "author", "published_at", "created_at")
    list_filter = ("is_published",)
    search_fields = ("title", "slug", "excerpt")
    readonly_fields = ("slug", "published_at", "created_at", "updated_at")
    autocomplete_fields = ("author",)
