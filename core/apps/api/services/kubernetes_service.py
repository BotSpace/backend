# type: ignore
"""
Kubernetes service for managing engine pods.

This service replaces Docker Swarm service management with Kubernetes pods.
Engine instances are deployed as Kubernetes pods with appropriate resource limits.
"""
import logging
import json
import os
import pathlib
from typing import Optional

from django.conf import settings
from config.env import env

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.shared.utils.settings import engine_version


logger = logging.getLogger(__name__)

_k8s_client = None
_k8s_core_api = None


def get_k8s_client():
    """Get or create Kubernetes API client
    
    Returns:
        kubernetes.client.CoreV1Api instance
    """
    global _k8s_client, _k8s_core_api
    
    if _k8s_core_api is not None:
        return _k8s_core_api
    
    try:
        from kubernetes import client, config
        
        # Try in-cluster config first (when running inside Kubernetes)
        try:
            config.load_incluster_config()
            logger.info("Loaded in-cluster Kubernetes config")
        except config.ConfigException:
            # Fall back to kubeconfig file
            kubeconfig_path = env.str("KUBECONFIG", default=None)
            if kubeconfig_path:
                config.load_kube_config(config_file=kubeconfig_path)
            else:
                config.load_kube_config()
            logger.info("Loaded kubeconfig file")
        
        _k8s_client = client
        _k8s_core_api = client.CoreV1Api()
        return _k8s_core_api
    except Exception as e:
        logger.error("Kubernetes client error: %s", e)
        raise Exception("Kubernetes client error")


def get_namespace():
    """Get the Kubernetes namespace for engine pods
    
    Returns:
        str: Namespace name
    """
    return env.str("K8S_NAMESPACE", default="botmother")


def get_pod_status(pod_name: str) -> str:
    """Get the status of a Kubernetes pod
    
    Args:
        pod_name: Name of the pod
        
    Returns:
        str: Container status enum value
    """
    try:
        api = get_k8s_client()
        namespace = get_namespace()
        pod = api.read_namespaced_pod(name=pod_name, namespace=namespace)
        phase = pod.status.phase
        
        match phase:
            case "Pending":
                return ContainerStatusEnum.INIT.value
            case "Running":
                return ContainerStatusEnum.RUNNING.value
            case "Succeeded":
                return ContainerStatusEnum.STOPPED.value
            case "Failed":
                return ContainerStatusEnum.FAILED.value
            case "Unknown":
                return ContainerStatusEnum.FAILED.value
            case _:
                return ContainerStatusEnum.STOPPED.value
    except Exception as e:
        logger.error("Error getting pod status for %s: %s", pod_name, e)
        return ContainerStatusEnum.STOPPED.value


def convert_k8s_event_status(event_type: str, reason: str) -> str:
    """Convert Kubernetes event to container status
    
    Args:
        event_type: Type of event (ADDED, MODIFIED, DELETED)
        reason: Reason from pod status
        
    Returns:
        str: Container status enum value
    """
    # Handle event types
    if event_type == "DELETED":
        return ContainerStatusEnum.STOPPED.value
    
    # Handle pod reasons/phases
    match reason.lower():
        case "pending" | "scheduled" | "pulling" | "pulled" | "created":
            return ContainerStatusEnum.INIT.value
        case "started" | "running":
            return ContainerStatusEnum.RUNNING.value
        case "completed" | "succeeded":
            return ContainerStatusEnum.STOPPED.value
        case "failed" | "backoff" | "unhealthy" | "oomkilled":
            return ContainerStatusEnum.FAILED.value
        case "killing" | "preempting":
            return ContainerStatusEnum.STOPPING.value
        case _:
            return ContainerStatusEnum.STOPPED.value


def get_default_env():
    """Get default environment variables for engine pods
    
    Returns:
        list: List of V1EnvVar objects
    """
    from kubernetes.client import V1EnvVar
    
    api_url = os.getenv("API_URL")
    if api_url is None:
        logger.error("API_URL not found in .env")
        return []
    
    return [
        V1EnvVar(name="API_URL", value=api_url),
    ]


def create_pod(image: str, name: str, env_vars: list = None, **kwargs):
    """Create a Kubernetes pod for engine
    
    Args:
        image: Container image
        name: Pod name
        env_vars: List of environment variable strings (KEY=VALUE format)
        **kwargs: Additional pod configuration
        
    Returns:
        Created pod object
    """
    from kubernetes.client import (
        V1Pod,
        V1PodSpec,
        V1Container,
        V1ObjectMeta,
        V1ResourceRequirements,
        V1EnvVar,
        V1VolumeMount,
        V1Volume,
        V1ContainerPort,
    )
    
    api = get_k8s_client()
    namespace = get_namespace()
    
    # Convert env strings to V1EnvVar objects
    container_env = get_default_env()
    if env_vars:
        for env_str in env_vars:
            if "=" in env_str:
                key, value = env_str.split("=", 1)
                container_env.append(V1EnvVar(name=key, value=value))
    
    # Resource limits
    resources = V1ResourceRequirements(
        limits={
            "cpu": "1",
            "memory": "512Mi",
        },
        requests={
            "cpu": "50m",
            "memory": "128Mi",
        }
    )
    
    # Volume mounts for flow file
    volume_mounts = kwargs.get("volume_mounts", [])
    volumes = kwargs.get("volumes", [])
    
    # Container definition
    container = V1Container(
        name="engine",
        image=image,
        env=container_env,
        resources=resources,
        volume_mounts=volume_mounts if volume_mounts else None,
        ports=[V1ContainerPort(container_port=8000, protocol="TCP")],
    )
    
    # Pod metadata with labels
    labels = {
        "app": "botmother-engine",
        "engine-name": name,
    }
    if "project_id" in kwargs:
        labels["project_id"] = str(kwargs["project_id"])
    
    metadata = V1ObjectMeta(
        name=name,
        namespace=namespace,
        labels=labels,
    )
    
    # Pod spec
    spec = V1PodSpec(
        containers=[container],
        restart_policy="OnFailure",
        volumes=volumes if volumes else None,
    )
    
    pod = V1Pod(
        api_version="v1",
        kind="Pod",
        metadata=metadata,
        spec=spec,
    )
    
    try:
        created_pod = api.create_namespaced_pod(namespace=namespace, body=pod)
        logger.info("Created pod: %s in namespace: %s", name, namespace)
        return created_pod
    except Exception as e:
        logger.error("Error creating pod %s: %s", name, e)
        raise


def remove_pod(pod_name: str):
    """Remove a Kubernetes pod
    
    Args:
        pod_name: Name of the pod to remove
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        api = get_k8s_client()
        namespace = get_namespace()
        api.delete_namespaced_pod(name=pod_name, namespace=namespace)
        logger.info("Removed pod: %s", pod_name)
        return True
    except Exception as e:
        logger.error("Error removing pod %s: %s", pod_name, e)
        return False


def create_configmap(name: str, data: dict):
    """Create a ConfigMap for storing flow configuration
    
    Args:
        name: ConfigMap name
        data: Dictionary of data to store
        
    Returns:
        Created ConfigMap object
    """
    from kubernetes.client import V1ConfigMap, V1ObjectMeta
    
    api = get_k8s_client()
    namespace = get_namespace()
    
    configmap = V1ConfigMap(
        api_version="v1",
        kind="ConfigMap",
        metadata=V1ObjectMeta(
            name=name,
            namespace=namespace,
        ),
        data=data,
    )
    
    try:
        # Try to create, if exists update
        try:
            created = api.create_namespaced_config_map(namespace=namespace, body=configmap)
            logger.info("Created ConfigMap: %s", name)
            return created
        except Exception:
            # Update existing
            updated = api.replace_namespaced_config_map(name=name, namespace=namespace, body=configmap)
            logger.info("Updated ConfigMap: %s", name)
            return updated
    except Exception as e:
        logger.error("Error managing ConfigMap %s: %s", name, e)
        raise


def delete_configmap(name: str):
    """Delete a ConfigMap
    
    Args:
        name: ConfigMap name
        
    Returns:
        bool: True if successful
    """
    try:
        api = get_k8s_client()
        namespace = get_namespace()
        api.delete_namespaced_config_map(name=name, namespace=namespace)
        logger.info("Deleted ConfigMap: %s", name)
        return True
    except Exception as e:
        logger.error("Error deleting ConfigMap %s: %s", name, e)
        return False


def deploy_engine(project, prefix: str, flow: dict, key: str, _env: list = None):
    """Deploy an engine pod for a project
    
    Args:
        project: ProjectModel instance
        prefix: Engine prefix (debug/release)
        flow: Bot flow configuration
        key: Unique engine key
        _env: Additional environment variables
        
    Returns:
        Created pod object
    """
    from kubernetes.client import V1VolumeMount, V1Volume, V1ConfigMapVolumeSource
    
    if _env is None:
        _env = []
    
    pod_name = f"{prefix}-{key}".lower().replace("_", "-")
    configmap_name = f"{pod_name}-flow"
    
    # Create ConfigMap with flow
    flow_json = json.dumps(flow, indent=4)
    create_configmap(configmap_name, {"flow.json": flow_json})
    
    # Get MongoDB credentials
    try:
        mongo_credentials = project.get_mongo_credentials()
        logger.info(
            "Using MongoDB credentials for project %s: %s",
            project.id,
            mongo_credentials["username"]
        )
    except Exception as e:
        logger.error("Failed to get MongoDB credentials for project %s: %s", project.id, e)
        mongo_credentials = {
            "connection_string": env.str("MONGO_URL"),
            "database": f"project_{project.id}"
        }
    
    # Build environment variables
    _env.append(f"BOT_TOKEN={env.str('TEST_BOT_TOKEN')}")
    _env.append("FLOW_FILE_PATH=/app/assets/flow.json")
    _env.append("WEBHOOK_ENABLED=true")
    _env.append("WEBHOOK_PORT=8000")
    _env.append("REDIS_ENABLED=true")
    _env.append(f"REDIS_ADDR={env.str('REDIS_HOST', default='redis')}:{env.str('REDIS_PORT', default='6379')}")
    _env.append(f"REDIS_PREFIX={prefix}_{key}")
    _env.append(f"MONGO_ADDR={mongo_credentials.get('connection_string', env.str('MONGO_URL'))}")
    _env.append(f"MONGO_DB_NAME={mongo_credentials.get('database', f'project_{project.id}')}")
    
    # Volume mount for flow file from ConfigMap
    volume_mounts = [
        V1VolumeMount(
            name="flow-volume",
            mount_path="/app/assets",
            read_only=True,
        )
    ]
    
    volumes = [
        V1Volume(
            name="flow-volume",
            config_map=V1ConfigMapVolumeSource(
                name=configmap_name,
            )
        )
    ]
    
    image = f"registry.jscorp.uz/golang-engine:{engine_version()}"
    
    return create_pod(
        image=image,
        name=pod_name,
        env_vars=_env,
        volume_mounts=volume_mounts,
        volumes=volumes,
        project_id=project.id,
    )


def stop_project_pods(project_id: int):
    """Stop all engine pods for a project
    
    Args:
        project_id: Project ID
        
    Returns:
        int: Number of pods stopped
    """
    try:
        api = get_k8s_client()
        namespace = get_namespace()
        
        # List pods with project_id label
        pods = api.list_namespaced_pod(
            namespace=namespace,
            label_selector=f"project_id={project_id}"
        )
        
        count = 0
        for pod in pods.items:
            try:
                api.delete_namespaced_pod(name=pod.metadata.name, namespace=namespace)
                logger.info("Stopped pod %s for project %s", pod.metadata.name, project_id)
                count += 1
            except Exception as e:
                logger.error("Error stopping pod %s: %s", pod.metadata.name, e)
        
        return count
    except Exception as e:
        logger.error("Error stopping project pods for %s: %s", project_id, e)
        return 0


async def pod_logs_async(pod_name: str):
    """Stream pod logs asynchronously
    
    Args:
        pod_name: Name of the pod
        
    Yields:
        Log lines
    """
    from kubernetes import client, config, watch
    
    try:
        # Load config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()
        
        api = client.CoreV1Api()
        namespace = get_namespace()
        
        w = watch.Watch()
        for line in w.stream(
            api.read_namespaced_pod_log,
            name=pod_name,
            namespace=namespace,
            follow=True,
        ):
            yield line
    except Exception as e:
        logger.error("Error streaming logs for pod %s: %s", pod_name, e)
        yield f"Error: {str(e)}"
