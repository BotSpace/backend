from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from unfold.decorators import display

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.models import (
    DebugModel,
    EnviromentModel,
    ProjectModel,
    RelaseModel,
)


class DebugInline(TabularInline):
    model = DebugModel
    tab = True
    fields = ["flow_hash", "service_id", "status"]
    extra = 0


class InlineRelease(TabularInline):
    model = RelaseModel
    tab = True
    extra = 0
    fields = [
        "version",
        "service_id",
        "status",
    ]


class InlineEnviroment(TabularInline):
    model = EnviromentModel
    tab = True


@admin.register(ProjectModel)
class ProjectAdmin(ModelAdmin):
    inlines = [InlineRelease, DebugInline, InlineEnviroment]
    list_display = (
        "id",
        "name",
        "username",
        "owner__phone",
        "owner__first_name",
        "owner__last_name",
        "release_webhook_uuid",
        "debug_webhook_uuid",
        "status",
    )

    @display(
        label={
            ContainerStatusEnum.PENDING.value: "warning",
            ContainerStatusEnum.RUNNING.value: "success",
            ContainerStatusEnum.FAILED.value: "info",
            ContainerStatusEnum.STOPPED.value: "danger",
            ContainerStatusEnum.STOPPING.value: "danger",
        }
    )
    def status(self, obj):
        if obj.release is None:
            return ContainerStatusEnum.PENDING.value
        return obj.release.status


@admin.register(RelaseModel)
class ReleaseAdmin(ModelAdmin):
    list_display = [
        "version",
        "service_id",
        "status",
    ]
