import json
import logging
import pathlib

import aiodocker
from docker.types import Mount

import docker
from core.apps.api.enums.container import ContainerStatusEnum

try:
    client = docker.from_env()
except Exception as e:
    print(e)
    client = None


async def service_logs_async(service_id):
    docker = aiodocker.Docker()
    async for line in docker.services.logs(service_id, follow=True, stdout=True, stderr=True):
        yield line


def get_service_status(service_id):
    try:
        state = client.services.get(service_id).tasks()[0]["Status"]["State"]
    except:
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
    return client.services.create(image=image, command=command, **kwargs)


def remove_service(service_id):
    try:
        return client.services.get(service_id).remove()
    except Exception as e:
        logging.error(e)
        print("container must be removed", e)
        return False


def create_volume(name):
    return client.volumes.create(name=name)


def deploy_service(prefix, flow, key, env=[]):
    path = "/var/lib/engine/%s_%s/" % (prefix, key)
    pathlib.Path(path).mkdir(parents=True, exist_ok=True)
    with open(path + "flow.json", "w") as file:
        file.write(json.dumps(flow, indent=4))
    mount = Mount(
        target="/code/assets/",
        source=path,
        type="bind",
    )
    return create_service(
        "jscorptech/engine:latest",
        "%s_%s" % (prefix, key),
        mounts=[mount],
        env=env,
    )
