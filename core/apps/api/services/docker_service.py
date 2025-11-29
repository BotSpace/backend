# type: ignore
from datetime import timedelta
import json
import logging
import pathlib

import aiodocker
from django.conf import settings
from docker.types import Mount, RestartPolicy
from rest_framework_simplejwt import tokens
import os
from config.env import env

import docker
from core.apps.api.enums.container import ContainerStatusEnum


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
    kwargs["name"] = name
    return get_client().services.create(
        image=image,
        command=command,
        constraints=["node.labels.name==my"],
        networks=["botmother"],
        restart_policy=RestartPolicy(
            condition="on-failure",
            max_attempts=5,
        ),
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
    path = "/var/lib/engine/%s_%s/" % (prefix, key)
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    access = tokens.AccessToken.for_user(project.owner)
    access.set_exp(lifetime=timedelta(days=365 * 100))  # supper katta risk lekin bizga baribir 😂
    with open(path + "flow.json", "w") as file:
        file.write(json.dumps(flow, indent=4))
    mount = Mount(
        target="/app/assets/",
        source=path,
        type="bind",
    )
    _env.extend(get_default_env())
    _env.append("FLOW_FILE_PATH=/app/assets/flow.json")
    _env.append(f"API_TOKEN={str(access)}")
    _env.append(f"PROJECT_ID={project.id}")
    _env.append("WEBHOOK_ENABLED=true")
    _env.append("WEBHOOK_PORT=8000")
    _env.append("REDIS_ENABLED=true")
    _env.append("REDIS_ADDR=redis:6379")
    _env.append(f"REDIS_PREFIX={prefix}_{key}")
    return create_service(
        "registry.jscorp.uz/golang-engine:%s" % settings.ENGINE_VERSION,
        "%s_%s" % (prefix, key),
        mounts=[mount],
        env=_env,
    )
