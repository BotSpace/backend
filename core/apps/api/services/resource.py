from datetime import timedelta
from typing import Optional
from django.db import models
from django.utils import timezone
from core.apps.api.models.file import FileModel
from core.apps.api.models.resource import ResourceModel


def get_project_storage(project) -> Optional[int]:
    return FileModel.objects.filter(project=project).aggregate(total=models.Sum("filesize")).get("total")


def get_user_storage(user) -> Optional[int]:
    return FileModel.objects.filter(project__owner=user).aggregate(total=models.Sum("filesize")).get("total")


def user_uresources(user) -> dict:
    """Foydalanuvchi loyihalarida oxirigi yangilanishda ishlatilayotgan resourcelar

    Args:
        user ([TODO:type]): [TODO:description]

    Returns:
        [TODO:description]
    """
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


def lproject_uresources(project) -> dict:
    """Loyiha Oxirgi yangilanishdagi ishlatilgan resourcelar o'rtacha qiymati

    Args:
        project ([TODO:type]): [TODO:description]

    Returns:
        [TODO:description]
    """
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


def project_uresources(project, time=None):
    """Loyiha ishlatgan belgilangan vaqt ichidagi resourcelar

    Args:
        project ([TODO:type]): [TODO:description]
    """
    if time is None:
        time = timedelta(hours=1)
    last_time = timezone.now() - time
    host_avg = (
        ResourceModel.objects.filter(project=project, created_at__gte=last_time)
        .values("hostname")
        .annotate(
            avg_ram=models.Avg("ram"),
            avg_cpu=models.Avg("cpu"),
            avg_net_rx=models.Max("net_rx"),
            avg_net_tx=models.Max("net_tx"),
        )
    )
    return host_avg.aggregate(
        total_ram=models.Sum("avg_ram"),
        total_cpu=models.Sum("avg_cpu"),
        total_net_tx=models.Sum("avg_net_tx"),
        total_net_rx=models.Sum("avg_net_rx"),
    )
