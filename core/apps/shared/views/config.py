# type: ignore
"""Global Config API views.

Public endpoint  : GET  /api/v1/shared/config/public/              (AllowAny, is_public=True only)
Internal endpoint: GET  /api/v1/shared/config/internal/            (X-Internal-Token, ALL keys)
Admin list       : GET  /api/v1/shared/config/                     (IsAdminUser)
Admin update     : PATCH /api/v1/shared/config/{key}/              (IsAdminUser)

Options (legacy SettingsModel/OptionsModel) — internal only:
  GET  /api/v1/shared/config/internal/options/       — read options rows
  POST /api/v1/shared/config/internal/options/set/   — upsert an option
"""

from django_core.mixins import BaseViewSetMixin
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, extend_schema_view
from rest_framework import mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.settings import AdminSettingsSetSerializer
from core.apps.shared.models import Config
from core.apps.shared.models.settings import OptionsModel, SettingsModel
from core.apps.shared.permissions import IsInternalTokenOnly
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
    http_method_names = ["get", "patch", "post", "head", "options"]

    # Per-action permission overrides via BaseViewSetMixin
    action_permission_classes = {
        "list": [IsAdminUser],
        "partial_update": [IsAdminUser],
        "public": [AllowAny],
        "internal": [IsInternalTokenOnly],
        "internal_options": [IsInternalTokenOnly],
        "internal_options_set": [IsInternalTokenOnly],
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

    @extend_schema(
        summary="Get ALL config values as a flat dict (internal service auth)",
        parameters=[
            OpenApiParameter(
                name="X-Internal-Token",
                location=OpenApiParameter.HEADER,
                required=True,
                description="Internal service token (settings.INTERNAL_API_TOKEN).",
            )
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "example": {
                        "ai_agent.provider": "bedrock",
                        "ai_agent.model": "qwen.qwen3-coder-480b-a35b-v1:0",
                        "ai_agent.region": "us-west-2",
                        "ai_agent.base_url": "",
                        "ai_agent.api_key": "sk-...",
                    },
                },
                description=(
                    "Flat mapping of config key -> value for ALL Config entries, "
                    "including is_public=False secrets such as ai_agent.api_key."
                ),
            ),
            401: OpenApiResponse(description="Missing or invalid X-Internal-Token."),
        },
        auth=[],
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="internal",
        url_name="internal",
        authentication_classes=[],  # No DRF auth needed — permission handles the token check.
    )
    def internal(self, request):
        """Return flat dict {key: value} for ALL Config entries (incl. secrets).

        Auth: X-Internal-Token header must match settings.INTERNAL_API_TOKEN.
        X-User-Id is NOT required — this is a pure service-to-service read.
        """
        qs = Config.objects.all().values("key", "value")
        return Response({item["key"]: item["value"] for item in qs})

    # ------------------------------------------------------------------
    # OptionsModel (legacy SettingsModel/OptionsModel) — internal endpoints
    # ------------------------------------------------------------------

    @extend_schema(
        summary="Read OptionsModel rows by settings_key (and optional option_key)",
        parameters=[
            OpenApiParameter(name="X-Internal-Token", location=OpenApiParameter.HEADER, required=True),
            OpenApiParameter(name="settings_key", location=OpenApiParameter.QUERY, required=True, type=str),
            OpenApiParameter(name="option_key", location=OpenApiParameter.QUERY, required=False, type=str),
        ],
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "example": {"status": True, "data": [{"settings_key": "engine", "option_key": "version", "value": ["3.5.122-prod"]}]},
                }
            ),
            401: OpenApiResponse(description="Missing or invalid X-Internal-Token."),
        },
        auth=[],
    )
    @action(
        methods=["GET"],
        detail=False,
        url_path="internal/options",
        url_name="internal-options",
        authentication_classes=[],
    )
    def internal_options(self, request):
        """Return OptionsModel rows filtered by settings_key (+ optional option_key).

        GET /api/v1/shared/config/internal/options/?settings_key=engine
        GET /api/v1/shared/config/internal/options/?settings_key=engine&option_key=version
        """
        settings_key = request.query_params.get("settings_key", "").strip()
        if not settings_key:
            return Response(
                {"settings_key": ["This field is required."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        qs = OptionsModel.objects.filter(settings__key=settings_key).select_related("settings")
        option_key = request.query_params.get("option_key", "").strip()
        if option_key:
            qs = qs.filter(key=option_key)

        data = [
            {"settings_key": obj.settings.key, "option_key": obj.key, "value": obj.value}
            for obj in qs
        ]
        return Response(data)

    @extend_schema(
        summary="Upsert an OptionsModel row (create or update)",
        parameters=[
            OpenApiParameter(name="X-Internal-Token", location=OpenApiParameter.HEADER, required=True),
        ],
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "settings_key": {"type": "string", "example": "engine"},
                    "option_key": {"type": "string", "example": "version"},
                    "value": {
                        "oneOf": [
                            {"type": "array", "items": {"type": "string"}, "example": ["3.5.122-prod"]},
                            {"type": "string", "example": "3.5.122-prod"},
                        ]
                    },
                },
                "required": ["settings_key", "option_key", "value"],
            }
        },
        responses={
            200: OpenApiResponse(
                response={
                    "type": "object",
                    "example": {
                        "status": True,
                        "data": {
                            "settings_key": "engine",
                            "option_key": "version",
                            "value": ["3.5.122-prod"],
                            "created": False,
                        },
                    },
                }
            ),
            400: OpenApiResponse(description="Validation error."),
            401: OpenApiResponse(description="Missing or invalid X-Internal-Token."),
        },
        auth=[],
    )
    @action(
        methods=["POST"],
        detail=False,
        url_path="internal/options/set",
        url_name="internal-options-set",
        authentication_classes=[],
    )
    def internal_options_set(self, request):
        """Upsert an OptionsModel row.

        POST /api/v1/shared/config/internal/options/set/
        Body: {"settings_key": "engine", "option_key": "version", "value": ["3.5.122-prod"]}

        value may also be a bare string — it will be wrapped into a 1-element list.
        """
        # Coerce bare string value to list before validation
        data = request.data.copy() if hasattr(request.data, "copy") else dict(request.data)
        if isinstance(data.get("value"), str):
            data["value"] = [data["value"]]

        serializer = AdminSettingsSetSerializer(data=data)
        serializer.is_valid(raise_exception=True)

        settings_key = serializer.validated_data["settings_key"]
        option_key = serializer.validated_data["option_key"]
        new_value = serializer.validated_data["value"]

        settings_obj, _ = SettingsModel.objects.get_or_create(
            key=settings_key,
            defaults={"is_public": False, "description": ""},
        )
        option_obj, created = OptionsModel.objects.update_or_create(
            settings=settings_obj,
            key=option_key,
            defaults={"value": new_value},
        )

        return Response(
            {
                "settings_key": settings_key,
                "option_key": option_key,
                "value": option_obj.value,
                "created": created,
            },
            status=status.HTTP_200_OK,
        )
