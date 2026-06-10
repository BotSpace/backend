from rest_framework import serializers

from core.apps.blog.models.blog import BlogPostModel


class BlogPostListSerializer(serializers.ModelSerializer):
    """Publik ro'yxat — yengil maydonlar (content yo'q)."""

    reading_time = serializers.IntegerField(read_only=True)

    class Meta:
        model = BlogPostModel
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "reading_time",
            "published_at",
        ]
        read_only_fields = fields


class BlogPostDetailSerializer(serializers.ModelSerializer):
    """Publik to'liq post — Markdown content bilan."""

    reading_time = serializers.IntegerField(read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = BlogPostModel
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "reading_time",
            "author_name",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_author_name(self, obj):
        if not obj.author:
            return None
        return obj.author.get_full_name() or getattr(obj.author, "phone", None) or str(obj.author)


class AdminBlogPostSerializer(serializers.ModelSerializer):
    """Admin CRUD — barcha maydonlar (qoralamalar ham)."""

    reading_time = serializers.IntegerField(read_only=True)
    author_name = serializers.SerializerMethodField()

    class Meta:
        model = BlogPostModel
        fields = [
            "id",
            "title",
            "slug",
            "excerpt",
            "content",
            "is_published",
            "author",
            "author_name",
            "reading_time",
            "published_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "author", "author_name", "reading_time", "published_at", "created_at", "updated_at"]

    def get_author_name(self, obj):
        if not obj.author:
            return None
        return obj.author.get_full_name() or getattr(obj.author, "phone", None) or str(obj.author)

    def validate_title(self, value):
        value = (value or "").strip()
        if not value:
            raise serializers.ValidationError("Sarlavha bo'sh bo'lmasligi kerak")
        return value
