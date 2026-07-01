# type: ignore
from decimal import Decimal

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from django_core.mixins import BaseViewSetMixin
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from core.apps.administration.permissions import IsAdminUser
from core.apps.administration.serializers.templates import (
    AdminSubmissionReviewSerializer,
    AdminTemplateCreateSerializer,
    AdminTemplateSerializer,
    AdminTemplateSubmissionSerializer,
    AdminTemplateWriteSerializer,
    AdminVerifySerializer,
)
from core.apps.administration.services import log_admin_action
from core.apps.template.enums.template import TemplateSubmissionStatusEnum
from core.apps.template.models import TemplateModel
from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.services.versioning import record_template_version


class AdminTemplatesView(
    BaseViewSetMixin,
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminTemplateSerializer
    # Allow create (POST) + PATCH; block full PUT replacements.
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_serializer_class(self):
        if self.action == "create":
            return AdminTemplateCreateSerializer
        if self.action in ("partial_update", "update"):
            return AdminTemplateWriteSerializer
        return AdminTemplateSerializer

    def create(self, request, *args, **kwargs):
        """Loyihadan yangi template yaratadi: flow+spec snapshot + v1."""
        from core.apps.template.services.template_spec import build_spec_from_project

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.validated_data["project"]
        categories = serializer.validated_data.pop("categories", [])
        features = serializer.validated_data.pop("features", [])
        with transaction.atomic():
            template = TemplateModel.objects.create(
                author=project.owner,
                project=project,
                name=serializer.validated_data["name"],
                short_description=serializer.validated_data.get("short_description", ""),
                description=serializer.validated_data.get("description", ""),
                original_price=serializer.validated_data["original_price"],
                discount=serializer.validated_data.get("discount", Decimal("0.00")),
                discount_type=serializer.validated_data.get("discount_type", "percent"),
                demo_url=serializer.validated_data.get("demo_url"),
                image=serializer.validated_data.get("image") or "",
                is_verify=serializer.validated_data.get("is_verify", False),
            )
            if categories:
                template.categories.set(categories)
            if features:
                template.features.set(features)
            spec = build_spec_from_project(project)
            record_template_version(template, spec, "Loyihadan yaratildi", request.user)
        log_admin_action(
            actor=request.user,
            action="template.create",
            target=template,
            before={},
            after={"id": template.id, "version": template.version},
            note="",
            request=request,
        )
        return Response(AdminTemplateSerializer(template).data, status=201)

    def perform_update(self, serializer):
        """Spec o'zgarsa yangi versiya yoziladi; faqat asosiy info o'zgarsa — yo'q."""
        old_spec = serializer.instance.spec
        new_spec = serializer.validated_data.get("spec", None)
        template = serializer.save()
        if new_spec is not None and new_spec != old_spec:
            record_template_version(template, new_spec, "Spec tahrirlandi", self.request.user)

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
        _allowed_orderings = (
            "id", "-id", "views", "-views", "original_price", "-original_price", "created_at", "-created_at"
        )
        if ordering in _allowed_orderings:
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
            "version": t.version,
            "spec": t.spec,
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

    @action(detail=True, methods=["patch"])
    def resync(self, request, pk=None):
        """Project'dan spec'ni qayta snapshot qiladi (project hali bog'liq bo'lsa)."""
        from core.apps.template.services.template_spec import build_spec_from_project

        target = self.get_object()
        if not target.project_id:
            from rest_framework.exceptions import ValidationError
            raise ValidationError({"project": "Template hozir hech bir project bilan bog'liq emas."})
        before_keys = list((target.spec or {}).keys())
        new_spec = build_spec_from_project(target.project)
        record_template_version(target, new_spec, "Loyihadan yangilandi", request.user)
        log_admin_action(
            actor=request.user,
            action="template.resync",
            target=target,
            before={"spec_keys": before_keys},
            after={"spec_keys": list(new_spec.keys()), "version": target.version},
            note="",
            request=request,
        )
        return Response(self.get_serializer(target).data)

    @action(detail=True, methods=["get"], url_path="versions")
    def versions(self, request, pk=None):
        """Versiya tarixi (spec'siz — yengil ro'yxat)."""
        target = self.get_object()
        data = [
            {
                "version": v.version,
                "note": v.note,
                "created_by_phone": getattr(v.created_by, "phone", None),
                "created_at": v.created_at,
                "is_current": v.version == target.version,
            }
            for v in target.versions.all()
        ]
        return Response(data)

    @action(detail=True, methods=["get"], url_path="versions/(?P<version>[0-9]+)")
    def version_detail(self, request, pk=None, version=None):
        """Bitta versiyaning to'liq spec'i (preview uchun)."""
        from rest_framework.exceptions import NotFound

        target = self.get_object()
        v = target.versions.filter(version=int(version)).first()
        if v is None:
            raise NotFound("Versiya topilmadi")
        return Response(
            {"version": v.version, "note": v.note, "spec": v.spec, "created_at": v.created_at}
        )

    @action(detail=True, methods=["post"], url_path="rollback")
    def rollback(self, request, pk=None):
        """Tanlangan versiyaga qaytaradi (append-only: yangi versiya yoziladi)."""
        from rest_framework.exceptions import NotFound, ValidationError

        target = self.get_object()
        version = request.data.get("version")
        if version is None or not str(version).isdigit():
            raise ValidationError({"version": "version (int) majburiy."})
        v = target.versions.filter(version=int(version)).first()
        if v is None:
            raise NotFound("Versiya topilmadi")
        note = (request.data.get("note") or "").strip() or f"v{v.version} ga qaytarildi"
        before_version = target.version
        record_template_version(target, v.spec, note, request.user)
        log_admin_action(
            actor=request.user,
            action="template.rollback",
            target=target,
            before={"version": before_version},
            after={"version": target.version, "rolled_back_to": v.version},
            note=note[:255],
            request=request,
        )
        return Response(self.get_serializer(target).data)


class AdminTemplateSubmissionsView(
    BaseViewSetMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsAdminUser]
    serializer_class = AdminTemplateSubmissionSerializer
    # Allow PATCH only; block full PUT replacements.
    http_method_names = ["get", "patch", "head", "options"]

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
        with transaction.atomic():
            target.status = new_status
            # Submission models usually have reviewed_by/reviewed_at — write
            # what's available, ignore missing fields.
            if hasattr(target, "reviewed_by"):
                target.reviewed_by = request.user
            if hasattr(target, "reviewed_at"):
                target.reviewed_at = timezone.now()
            # On APPROVE, publish the actual Template from the submission — same
            # as the Django admin `approve_submissions` action. Without this the
            # admin-panel approve only flipped the status and never created the
            # template. Idempotent: skip if a template is already linked.
            if new_status == TemplateSubmissionStatusEnum.APPROVED.value and not target.template:
                from core.apps.template.services.template_spec import build_spec_from_project

                spec = {}
                if target.project:
                    try:
                        spec = build_spec_from_project(target.project)
                    except Exception:
                        pass
                template = TemplateModel.objects.create(
                    author=target.user,
                    name=target.name,
                    image=target.image,
                    video=target.video,
                    project=target.project,
                    short_description=target.short_description,
                    description=target.description,
                    original_price=target.original_price,
                    discount=Decimal("0.00"),
                    discount_type="percent",
                    demo_url=target.demo_url,
                    is_verify=True,
                    required_envs=target.required_envs or [],
                    spec=spec,
                )
                template.categories.set(target.categories.all())
                template.features.set(target.features.all())
                target.template = template
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
