# type: ignore
"""
Engine orchestration service.

This module provides functions for managing bot engines using either
Docker Swarm or Kubernetes, based on the ORCHESTRATOR environment variable.

Set ORCHESTRATOR=kubernetes to use Kubernetes pods.
Set ORCHESTRATOR=docker (default) to use Docker Swarm services.
"""
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


# Orchestrator type: 'docker' or 'kubernetes'
ORCHESTRATOR = env.str("ORCHESTRATOR", default="docker")

client = None


def is_kubernetes():
    """Check if Kubernetes orchestration is enabled
    
    Returns:
        bool: True if using Kubernetes, False for Docker
    """
    return ORCHESTRATOR.lower() == "kubernetes"


def get_client():
    """Get Docker client (only used when ORCHESTRATOR=docker)
    
    Returns:
        Docker client instance
    """
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
    """Stream logs for a service/pod asynchronously
    
    Args:
        service_id: Docker service ID or Kubernetes pod name
        
    Yields:
        Log lines
    """
    if is_kubernetes():
        from core.apps.api.services.kubernetes_service import pod_logs_async
        async for line in pod_logs_async(service_id):
            yield line
    else:
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
    """Get the status of a service/pod
    
    Args:
        service_id: Docker service ID or Kubernetes pod name
        
    Returns:
        str: Container status enum value
    """
    if is_kubernetes():
        from core.apps.api.services.kubernetes_service import get_pod_status
        return get_pod_status(service_id)
    
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
        # constraints=["node.labels.name==my"],
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
    """Remove a service/pod
    
    Args:
        service_id: Docker service ID or Kubernetes pod name
        
    Returns:
        bool: True if successful, False otherwise
    """
    if is_kubernetes():
        from core.apps.api.services.kubernetes_service import remove_pod
        return remove_pod(service_id)
    
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
    """Deploy engine service/pod for project with MongoDB credentials
    
    This function creates either a Docker Swarm service or Kubernetes pod
    based on the ORCHESTRATOR environment variable.

    Args:
        project: ProjectModel instance
        prefix: Service prefix (debug/release)
        flow: Bot flow configuration
        key: Unique service key
        _env: Additional environment variables

    Returns:
        Created Docker service or Kubernetes pod
    """
    if is_kubernetes():
        from core.apps.api.services.kubernetes_service import deploy_engine
        return deploy_engine(project, prefix, flow, key, _env)
    
    # Docker Swarm deployment
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


def stop_project_services(project_id: int):
    """Stop all engine services/pods for a project
    
    This function works with both Docker Swarm and Kubernetes.
    
    Args:
        project_id: Project ID
        
    Returns:
        int: Number of services/pods stopped
    """
    if is_kubernetes():
        from core.apps.api.services.kubernetes_service import stop_project_pods
        return stop_project_pods(project_id)
    
    # Docker Swarm - find services by label
    try:
        services = get_client().services.list(filters={
            'label': f'project_id={project_id}'
        })
        
        count = 0
        for service in services:
            try:
                service.remove()
                logging.info(f"Stopped service {service.name} for project {project_id}")
                count += 1
            except Exception as e:
                logging.error(f"Error stopping service {service.name}: {e}")
        
        return count
    except Exception as e:
        logging.error(f"Error stopping services for project {project_id}: {e}")
        return 0
