# type: ignore
from django.db.models import Q
from django.utils import timezone
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.templates import (
    AdminSubmissionReviewSerializer,
    AdminTemplateSerializer,
    AdminTemplateSubmissionSerializer,
    AdminVerifySerializer,
)
from core.apps.administration.services import log_admin_action
from core.apps.template.enums.template import TemplateSubmissionStatusEnum
from core.apps.template.models import TemplateModel
from core.apps.template.models.submission import TemplateSubmissionRequestModel


class AdminTemplatesView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminTemplateSerializer

    def get_queryset(self):
        qs = TemplateModel.objects.select_related("author").prefetch_related("categories").order_by("-id")
        p = self.request.query_params
        search = p.get("search", "").strip()
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(slug__icontains=search))
        verify = p.get("is_verify", "").strip()
        if verify in ("true", "false"):
            qs = qs.filter(is_verify=(verify == "true"))
        category = p.get("category", "").strip()
        if category.isdigit():
            qs = qs.filter(categories__id=int(category))
        author = p.get("author", "").strip()
        if author.isdigit():
            qs = qs.filter(author_id=int(author))
        price_min = p.get("price_min", "").strip()
        if price_min.replace(".", "", 1).isdigit():
            qs = qs.filter(original_price__gte=price_min)
        price_max = p.get("price_max", "").strip()
        if price_max.replace(".", "", 1).isdigit():
            qs = qs.filter(original_price__lte=price_max)
        created_after = p.get("created_after", "").strip()
        if created_after:
            qs = qs.filter(created_at__date__gte=created_after)
        created_before = p.get("created_before", "").strip()
        if created_before:
            qs = qs.filter(created_at__date__lte=created_before)
        ordering = p.get("ordering", "").strip()
        if ordering in ("id", "-id", "views", "-views", "original_price", "-original_price", "created_at", "-created_at"):
            qs = qs.order_by(ordering)
        return qs

    def retrieve(self, request, *args, **kwargs):
        """Rich detail: template + author + categories + features + order
        stats + flow node count."""
        from core.apps.template.models import TemplateOrderModel  # noqa: WPS433
        from core.apps.template.enums.order import TemplateOrderStatusEnum  # noqa: WPS433

        t = self.get_object()
        orders_qs = TemplateOrderModel.objects.filter(template=t)
        confirmed = orders_qs.filter(
            payment_status=True, status=TemplateOrderStatusEnum.CONFIRM.value
        ).count()
        flow = getattr(getattr(t, "project", None), "flow", None)
        node_count = None
        if flow is not None:
            node_count = len(flow) if isinstance(flow, list) else len((flow or {}).get("nodes", []))
        data = {
            "id": t.id,
            "name": t.name,
            "slug": t.slug,
            "image": t.image.url if t.image else None,
            "demo_url": t.demo_url,
            "short_description": t.short_description,
            "description": t.description,
            "original_price": str(t.original_price),
            "discount": str(t.discount),
            "discount_type": t.discount_type,
            "is_verify": t.is_verify,
            "views": t.views,
            "likes": t.likes.count() if hasattr(t, "likes") else 0,
            "author": {
                "id": t.author_id,
                "phone": getattr(t.author, "phone", None),
            },
            "categories": [{"id": c.id, "name": c.name} for c in t.categories.all()],
            "features": [{"id": f.id, "name": f.name} for f in t.features.all()],
            "orders_total": orders_qs.count(),
            "orders_confirmed": confirmed,
            "node_count": node_count,
            "created_at": t.created_at,
            "updated_at": t.updated_at,
        }
        return Response(data)

    @action(detail=True, methods=["patch"])
    def verify(self, request, pk=None):
        target = self.get_object()
        serializer = AdminVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before = {"is_verify": target.is_verify}
        target.is_verify = serializer.validated_data["is_verify"]
        target.save(update_fields=["is_verify", "updated_at"])
        log_admin_action(
            actor=request.user,
            action="template.verify",
            target=target,
            before=before,
            after={"is_verify": target.is_verify},
            note=serializer.validated_data.get("note", "")[:255],
            request=request,
        )
        return Response(self.get_serializer(target).data)


class AdminTemplateSubmissionsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminTemplateSubmissionSerializer

    def get_queryset(self):
        qs = (
            TemplateSubmissionRequestModel.objects.select_related(
                "user", "project", "template", "reviewed_by"
            )
            .prefetch_related("categories", "features")
            .order_by("-id")
        )
        p = self.request.query_params
        status_filter = p.get("status", "").strip()
        if status_filter:
            qs = qs.filter(status=status_filter)
        search = p.get("search", "").strip()
        if search:
            qs = qs.filter(
                Q(name__icontains=search)
                | Q(user__phone__icontains=search)
                | Q(short_description__icontains=search)
            )
        price_min = p.get("price_min", "").strip()
        if price_min.replace(".", "", 1).isdigit():
            qs = qs.filter(original_price__gte=price_min)
        price_max = p.get("price_max", "").strip()
        if price_max.replace(".", "", 1).isdigit():
            qs = qs.filter(original_price__lte=price_max)
        created_after = p.get("created_after", "").strip()
        if created_after:
            qs = qs.filter(created_at__date__gte=created_after)
        created_before = p.get("created_before", "").strip()
        if created_before:
            qs = qs.filter(created_at__date__lte=created_before)
        ordering = p.get("ordering", "").strip()
        if ordering in (
            "id",
            "-id",
            "original_price",
            "-original_price",
            "created_at",
            "-created_at",
        ):
            qs = qs.order_by(ordering)
        return qs

    def _review(self, request, pk, new_status: str, action_name: str):
        target = self.get_object()
        serializer = AdminSubmissionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        before = {"status": target.status}
        target.status = new_status
        # Submission models usually have reviewed_by/reviewed_at — write
        # what's available, ignore missing fields.
        if hasattr(target, "reviewed_by"):
            target.reviewed_by = request.user
        if hasattr(target, "reviewed_at"):
            target.reviewed_at = timezone.now()
        target.save()
        log_admin_action(
            actor=request.user,
            action=f"template_submission.{action_name}",
            target=target,
            before=before,
            after={"status": target.status},
            note=serializer.validated_data.get("note", "")[:255],
            request=request,
        )
        return Response(self.get_serializer(target).data)

    @action(detail=True, methods=["patch"])
    def approve(self, request, pk=None):
        return self._review(request, pk, TemplateSubmissionStatusEnum.APPROVED.value, "approve")

    @action(detail=True, methods=["patch"])
    def reject(self, request, pk=None):
        return self._review(request, pk, TemplateSubmissionStatusEnum.REJECTED.value, "reject")
