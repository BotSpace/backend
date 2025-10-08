from core.apps.api.models.project import EnviromentModel


def project_enviroment(project_id):
    for env in EnviromentModel.objects.filter(project_id=project_id):
        yield "%(key)s=%(value)s" % {"key": env.key, "value": env.value}
