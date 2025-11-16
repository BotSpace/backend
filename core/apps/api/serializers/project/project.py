from rest_framework import serializers

from core.apps.api.models import ProjectModel
from core.apps.api.models.project import DebugModel, EnviromentModel
from core.apps.api.serializers.project.debug import CreateDebugSerializer, RetrieveDebugSerializer
from core.apps.api.serializers.project.relase import ListRelaseSerializer
from core.apps.api.services.dashboard import DashboardService
from core.apps.cms.services.mongo import get_project_collection
from core.apps.template.models import TemplateModel


class BaseProjectSerializer(serializers.ModelSerializer):
    release = ListRelaseSerializer()
    users = serializers.SerializerMethodField()

    def __init__(self, instance=None, *args, **kwargs):
        super().__init__(instance=instance, *args, **kwargs)
        self.dashboardService = DashboardService()

    def to_representation(self, instance):
        self.dashboardService.set_collection(get_project_collection(instance))
        return super().to_representation(instance)

    def get_users(self, obj) -> int:
        return self.dashboardService.users_count()

    class Meta:
        model = ProjectModel
        fields = [
            "id",
            "name",
            "users",
            "username",
            "avatar",
        ]


class ListProjectSerializer(BaseProjectSerializer):
    class Meta(BaseProjectSerializer.Meta):
        fields = [*BaseProjectSerializer.Meta.fields, "release"]


class RetrieveProjectSerializer(BaseProjectSerializer):
    debug = RetrieveDebugSerializer()
    debug_bot = serializers.SerializerMethodField()
    release_bot = serializers.SerializerMethodField()

    def get_debug_bot(self, obj) -> bool:
        return EnviromentModel.objects.filter(project=obj, key="BOT_TOKEN").exists()

    def get_release_bot(self, obj) -> bool:
        return EnviromentModel.objects.filter(project=obj, key="RELEASE_BOT_TOKEN").exists()

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            *BaseProjectSerializer.Meta.fields,
            "debug",
            "release",
            "debug_bot",
            "release_bot",
            "flow",
        ]


class CreateProjectSerializer(BaseProjectSerializer):
    debug = CreateDebugSerializer(required=False)
    release = None

    class Meta(BaseProjectSerializer.Meta):
        fields = [
            "id",
            "name",
            "debug",
            "flow",
        ]


class CreateProjectFromTemplate(serializers.Serializer):
    template = serializers.PrimaryKeyRelatedField(queryset=TemplateModel.objects.all())
    name = serializers.CharField(max_length=255)
    token = serializers.CharField(max_length=255)
