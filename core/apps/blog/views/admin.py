# type: ignore
"""Admin blog CRUD — Next.js admin paneli uchun (faqat staff/superuser)."""

from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets

from core.apps.administration.permissions import IsAdminUser
from core.apps.blog.models.blog import BlogPostModel
from core.apps.blog.serializers.blog import AdminBlogPostSerializer


@extend_schema(tags=["admin-blog"])
class AdminBlogPostView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    """Barcha postlar ustidan to'liq CRUD (qoralamalar bilan birga)."""

    permission_classes = [IsAdminUser]
    serializer_class = AdminBlogPostSerializer

    def get_queryset(self):
        qs = BlogPostModel.objects.select_related("author").order_by("-created_at", "-id")
        published = self.request.query_params.get("is_published", "").strip()
        if published in {"true", "1"}:
            qs = qs.filter(is_published=True)
        elif published in {"false", "0"}:
            qs = qs.filter(is_published=False)
        return qs

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
