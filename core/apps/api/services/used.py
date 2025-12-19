# type: ignore
from typing import Literal
from django.db import models
from core.apps.api.models.project import ProjectModel
from core.apps.api.models.resource import ResourceModel, StorageResourceModel
from core.apps.api.services.resource import (
    get_project_storage,
    get_user_storage,
    lproject_uresources,
    user_uresources,
)
from django.db.models.functions import TruncHour
from django.utils import timezone
from datetime import timedelta


MODE = Literal["user", "project"]


class UsedService:

    def __init__(self) -> None:
        self._project = None
        self._user = None
        self._queryset = None
        self._storage_queryset = None
        self._mode: MODE = "project"
        self._user = None

    def set_project(self, project: ProjectModel):
        self._project = project
        self._set_queryset()

    def set_user(self, user):
        self._user = user
        self._set_queryset()

    def _check_project(self):
        assert self._project is not None, "project not set"

    def _check_user(self):
        assert self._user is not None, "user not set"

    def _check_queryset(self):
        assert self._queryset is not None, "queryset not set"

    def set_mode(self, mode: MODE):
        self._mode = mode

    def _set_queryset(self):
        if self._queryset is None:
            last_time = timezone.now() - timedelta(hours=24)
            if self._mode == "project":
                self._check_project()
                self._queryset = ResourceModel.objects.filter(project=self._project, created_at__gte=last_time)
                self._storage_queryset = StorageResourceModel.objects.filter(
                    project=self._project, created_at__gte=last_time
                )
            else:
                self._check_user()
                self._queryset = ResourceModel.objects.filter(project__owner=self._user, created_at__gte=last_time)
                self._storage_queryset = StorageResourceModel.objects.filter(
                    project__owner=self._user, created_at__gte=last_time
                )

    def chart(self) -> dict:
        self._check_queryset()
        data = (
            self._queryset.annotate(hour=TruncHour("created_at"))
            .values("hour")
            .annotate(
                ram=models.Avg("ram"),
                cpu=models.Avg("cpu"),
                net_rx=models.Max("net_rx"),
                net_tx=models.Max("net_tx"),
            )
        )
        storage_data = (
            self._storage_queryset.annotate(hour=TruncHour("created_at"))
            .values("hour")
            .annotate(storage=models.Max("storage"))
        )
        storage_dates = [d["hour"].strftime("%Y-%m-%d %H:%M") for d in storage_data]
        storage = [d["storage"] for d in storage_data]
        dates = [d["hour"].strftime("%Y-%m-%d %H:%M") for d in data]
        ram = [d["ram"] for d in data]
        cpu = [d["cpu"] for d in data]
        net_tx = [d["net_tx"] for d in data]
        net_rx = [d["net_rx"] for d in data]
        return {
            "ram": {"dates": dates, "values": ram},
            "cpu": {"dates": dates, "values": cpu},
            "net_tx": {"dates": dates, "values": net_tx},
            "net_rx": {"dates": dates, "values": net_rx},
            "storage": {"dates": storage_dates, "values": storage},
        }

    def get_used(self) -> dict:
        used_storage = None
        uresource = {}
        if self._mode == "project":
            used_storage = get_project_storage(self._project)
            uresource = lproject_uresources(self._project)
        else:
            used_storage = get_user_storage(self._user)
            uresource = user_uresources(self._user)
        return {
            "used_storage": used_storage,
            "used_ram": uresource.get("ram", 0),
            "used_cpu": uresource.get("cpu", 0),
            "used_net_tx": uresource.get("net_tx", 0),
            "used_net_rx": uresource.get("net_rx", 0),
            "chart": self.chart(),
        }
