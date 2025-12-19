from typing import Optional
from core.apps.api.models.project import EnviromentModel


def project_enviroment(project_id):
    for env in EnviromentModel.objects.filter(project_id=project_id):
        yield "%(key)s=%(value)s" % {"key": env.key, "value": env.value}


def validate_debug_enviroment(project_id):
    queryset = EnviromentModel.objects.filter(project_id=project_id, key="BOT_TOKEN")
    if not queryset.exists():
        return False
    return True


def debug_bot_token(project_id: int) -> Optional[str]:
    """Get Debug bot token

    Args:
        project_id: [TODO:description]

    Returns:
        [TODO:description]
    """
    try:
        return EnviromentModel.objects.get(project_id=project_id, key="BOT_TOKEN").value
    except EnviromentModel.DoesNotExist:
        return None


def release_bot_token(project_id: int) -> Optional[str]:
    """Get Release bot token

    Args:
        project_id: [TODO:description]

    Returns:
        [TODO:description]
    """
    try:
        return EnviromentModel.objects.get(project_id=project_id, key="RELEASE_BOT_TOKEN").value
    except EnviromentModel.DoesNotExist:
        return None


def validate_release_enviroment(project_id):
    queryset = EnviromentModel.objects.filter(project_id=project_id, key="RELEASE_BOT_TOKEN")
    if not queryset.exists():
        return False
    return True
