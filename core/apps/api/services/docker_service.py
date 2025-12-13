# type: ignore
import logging
import json
import pathlib

import aiodocker
from django.conf import settings
from docker.types import Mount, RestartPolicy
import os
from config.env import env

import docker
from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.shared.utils.settings import engine_version


client = None


def get_client():
    global client
    if client is not None:
        return client
    try:
        _client = docker.from_env()
        _client.login(
            username=env.str("DOCKER_USERNAME"),
            password=env.str("DOCKER_PASSWORD"),
            registry=env.str("DOCKER_REGISTRY"),
        )
        client = _client
        return _client
    except Exception as e:
        logging.error("docker client error error=%s", e)
        raise Exception("docker client error")


async def service_logs_async(service_id):
    docker = aiodocker.Docker()
    async for line in docker.services.logs(service_id, follow=True, stdout=True, stderr=True):
        yield line


def convert_status(status):
    match status:
        case "create":
            return ContainerStatusEnum.INIT.value
        case "start":
            return ContainerStatusEnum.RUNNING.value
        case "die" | "destroy":
            return ContainerStatusEnum.FAILED.value
        case "kill" | "stop":
            return ContainerStatusEnum.STOPPED.value
        case _:
            return ContainerStatusEnum.STOPPED.value


def get_service_status(service_id):
    try:
        state = get_client().services.get(service_id).tasks()[0]["Status"]["State"]
    except Exception as _:
        return ContainerStatusEnum.STOPPED.value
    match state:
        case "new" | "pending" | "assigned" | "accepted" | "preparing" | "starting":
            return ContainerStatusEnum.INIT.value
        case "running":
            return ContainerStatusEnum.RUNNING.value
        case "complete" | "shutdown" | "remove":
            return ContainerStatusEnum.STOPPED.value
        case "failed" | "rejected" | "orphaned":
            return ContainerStatusEnum.FAILED.value
        case _:
            return ContainerStatusEnum.STOPPED.value


def create_service(image, name, command=None, **kwargs):
    """Create Docker service with resource limits

    Args:
        image: Docker image
        name: Service name
        command: Command to run
        **kwargs: Additional service creation parameters

    Returns:
        Created service
    """
    from docker.types import Resources

    kwargs["name"] = name

    resources = Resources(
        cpu_limit=int(1e9),  # 1 CPU core
        cpu_reservation=int(5e7),  # Reserve 0.05 CPU
    )

    return get_client().services.create(
        image=image,
        command=command,
        constraints=["node.labels.name==my"],
        networks=["botmother"],
        restart_policy=RestartPolicy(
            condition="on-failure",
            max_attempts=5,
        ),
        log_driver="json-file",
        log_driver_options={
            "max-size": "5m",
            "max-file": "2",
        },
        resources=resources,
        **kwargs,
    )


def remove_service(service_id):
    try:
        return get_client().services.get(service_id).remove()
    except Exception as e:
        logging.error(e)
        print("container must be removed", e)
        return False


def create_volume(name):
    return get_client().volumes.create(name=name)


def get_default_env():
    api_url = os.getenv("API_URL")
    if api_url is None:
        logging.error("API_URL not found for .env")
        return []
    return [
        f"API_URL={api_url}",
    ]


def deploy_service(project, prefix, flow, key, _env: list = []):
    """Deploy Docker service for project with MongoDB credentials

    Args:
        project: ProjectModel instance
        prefix: Service prefix (debug/release)
        flow: Bot flow configuration
        key: Unique service key
        _env: Additional environment variables

    Returns:
        Created Docker service
    """
    path = "/mnt/engine/%s_%s/" % (prefix, key)
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)

    with open(path + "flow.json", "w") as file:
        file.write(json.dumps(flow, indent=4))

    mount = Mount(target="/app/assets/", source=path, type="bind")
    try:
        mongo_credentials = project.get_mongo_credentials()
        logging.info(f"Using MongoDB credentials for project {project.id}: {mongo_credentials['username']}")
    except Exception as e:
        logging.error(f"Failed to get MongoDB credentials for project {project.id}: {e}")
        mongo_credentials = {"connection_string": env.str("MONGO_URL"), "database": f"project_{project.id}"}

    # Build environment variables
    _env.extend(get_default_env())
    _env.append(
        f"BOT_TOKEN={env.str("TEST_BOT_TOKEN")}"
    )  # WARNING: barcha enginelar ichida birxil bot token bu xafsiz emas
    _env.append("FLOW_FILE_PATH=/app/assets/flow.json")
    _env.append("WEBHOOK_ENABLED=true")
    _env.append("WEBHOOK_PORT=8000")
    _env.append("REDIS_ENABLED=true")
    _env.append("REDIS_ADDR=redis:6379")
    _env.append(f"REDIS_PREFIX={prefix}_{key}")
    _env.append(f"MONGO_ADDR={mongo_credentials.get('connection_string', env.str('MONGO_URL'))}")
    _env.append(f"MONGO_DB_NAME={mongo_credentials.get('database', f'project_{project.id}')}")

    return create_service(
        "registry.jscorp.uz/golang-engine:%s" % engine_version(),
        "%s_%s" % (prefix, key),
        mounts=[mount],
        env=_env,
    )
