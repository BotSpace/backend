from typing import Optional
from django.db import models
from core.apps.api.models.file import FileModel
from core.apps.api.models.resource import ResourceModel


def get_project_storage(project) -> Optional[int]:
    return FileModel.objects.filter(project=project).aggregate(total=models.Sum("filesize")).get("total")


def get_user_storage(user) -> Optional[int]:
    return FileModel.objects.filter(project__owner=user).aggregate(total=models.Sum("filesize")).get("total")


def user_used_resources(user) -> dict:
    latest_ids = (
        ResourceModel.objects.filter(project__owner=user)
        .order_by("hostname", "-created_at")
        .distinct("hostname")
        .values_list("id", flat=True)
    )

    totals = ResourceModel.objects.filter(id__in=latest_ids).aggregate(
        ram=models.Sum("ram"),
        cpu=models.Sum("cpu"),
        net_rx=models.Sum("net_rx"),
        net_tx=models.Sum("net_tx"),
    )
    return totals


def project_used_resources(project) -> dict:
    latest_ids = (
        ResourceModel.objects.filter(project=project)
        .order_by("hostname", "-created_at")
        .distinct("hostname")
        .values_list("id", flat=True)
    )

    totals = ResourceModel.objects.filter(id__in=latest_ids).aggregate(
        ram=models.Sum("ram"),
        cpu=models.Sum("cpu"),
        net_rx=models.Sum("net_rx"),
        net_tx=models.Sum("net_tx"),
    )
    return totals
