import json
import logging
import pathlib

import aiodocker
from docker.types import Mount

import docker

client = docker.from_env()


async def service_logs_async(service_id):
    docker = aiodocker.Docker()
    async for line in docker.services.logs(service_id, follow=True, stdout=True, stderr=True):
        yield line


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


def deploy_debug_service(flow, key, env=[]):
    debug_path = "/var/lib/engine/debug_%s/" % key
    pathlib.Path(debug_path).mkdir(parents=True, exist_ok=True)
    with open(debug_path + "flow.json", "w") as file:
        file.write(json.dumps(flow, indent=4))
    mount = Mount(
        target="/code/assets/",
        source=debug_path,
        type="bind",
    )
    return create_service(
        "jscorptech/engine:latest",
        "debug_%s" % key,
        mounts=[mount],
        env=env,
    )
