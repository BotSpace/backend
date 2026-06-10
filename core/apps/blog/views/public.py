from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.viewsets import GenericViewSet, mixins

from core.apps.blog.models.blog import BlogPostModel
from core.apps.blog.serializers.blog import (
    BlogPostDetailSerializer,
    BlogPostListSerializer,
)


@extend_schema(tags=["blog"])
class BlogPostPublicView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    GenericViewSet,
):
    """Publik blog — faqat e'lon qilingan postlar. Slug bo'yicha o'qiladi."""

    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = BlogPostListSerializer
    lookup_field = "slug"

    action_serializer_class = {
        "list": BlogPostListSerializer,
        "retrieve": BlogPostDetailSerializer,
    }

    def get_queryset(self):
        return BlogPostModel.objects.filter(is_published=True).order_by("-published_at", "-created_at")
