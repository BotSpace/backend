# type: ignore
"""Global Config API views.

Public endpoint  : GET  /api/v1/shared/config/public/  (AllowAny)
Admin list       : GET  /api/v1/shared/config/          (IsAdminUser)
Admin update     : PATCH /api/v1/shared/config/{key}/   (IsAdminUser)
"""

from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.apps.administration.permissions import IsAdminUser
from core.apps.shared.models import Config
from core.apps.shared.serializers import ConfigSerializer, ConfigUpdateSerializer


@extend_schema(tags=["config"])
@extend_schema_view(
    list=extend_schema(
        summary="List all config entries (admin only)",
        responses={200: ConfigSerializer(many=True)},
    ),
    partial_update=extend_schema(
        summary="Update a config value by key (admin only)",
        request=ConfigUpdateSerializer,
        responses={200: ConfigSerializer},
    ),
)
class ConfigViewSet(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.UpdateModelMixin,
    GenericViewSet,
):
    """Config ViewSet.

    - ``list`` and ``partial_update`` require IsAdminUser.
    - ``public`` custom action is AllowAny.

    Lookup is by ``key`` (unique slug) rather than numeric PK.
    """

    serializer_class = ConfigSerializer
    lookup_field = "key"
    # Keys contain dots (e.g. "ai_agent.provider"); the default router lookup
    # regex ([^/.]+) excludes dots, so PATCH /config/ai_agent.provider/ would
    # 404. Allow any non-slash char in the key segment.
    lookup_value_regex = "[^/]+"
    http_method_names = ["get", "patch", "head", "options"]

    # Per-action permission overrides via BaseViewSetMixin
    action_permission_classes = {
        "list": [IsAdminUser],
        "partial_update": [IsAdminUser],
        "public": [AllowAny],
    }
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        return Config.objects.all().order_by("group", "key")

    def get_serializer_class(self):
        if self.action == "partial_update":
            return ConfigUpdateSerializer
        return ConfigSerializer

    def update(self, request, *args, **kwargs):
        # Force partial update; PUT is not exposed.
        kwargs["partial"] = True
        return super().update(request, *args, **kwargs)

    @extend_schema(
        summary="Get all public config values as a flat dict (no auth required)",
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "example": {
                        "ai_agent.provider": "bedrock",
                        "ai_agent.model": "qwen.qwen3-coder-480b-a35b-v1:0",
                        "ai_agent.region": "us-west-2",
                    },
                },
                description="Flat mapping of config key -> value for all is_public=True entries.",
            )
        },
    )
    @action(methods=["GET"], detail=False, url_path="public", url_name="public")
    def public(self, request):
        """Return flat dict {key: value} for every is_public=True Config entry."""
        qs = Config.objects.filter(is_public=True).values("key", "value")
        return Response({item["key"]: item["value"] for item in qs})
