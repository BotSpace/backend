# type: ignore
"""
Kubernetes service for managing engine deployments.

This service manages Kubernetes deployments for engine instances.
Engine instances are deployed as Kubernetes deployments with appropriate resource limits.
"""

import logging
import json
import os

from config.env import env
from core.apps.api.services.docker_service import remove_service
from kubernetes.client.rest import ApiException

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.shared.utils.settings import engine_version
from tenacity import retry, stop_after_attempt, wait_exponential
from kubernetes.client import (
    V1EnvVar,
    V1Deployment,
    V1DeploymentSpec,
    V1PodTemplateSpec,
    V1PodSpec,
    V1Container,
    V1ObjectMeta,
    V1ConfigMap,
    V1ResourceRequirements,
    V1EnvFromSource,
    V1SecretEnvSource,
    V1ContainerPort,
    V1LabelSelector,
    V1LocalObjectReference,
)
from kubernetes import client, config, watch


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


def get_deployment_status(deployment_name: str) -> str:
    """Get the status of a Kubernetes deployment

    Args:
        deployment_name: Name of the deployment

    Returns:
        str: Container status enum value
    """
    try:
        apps_api = client.AppsV1Api()
        namespace = get_namespace()
        deployment = apps_api.read_namespaced_deployment(name=deployment_name, namespace=namespace)

        if deployment.status.ready_replicas and deployment.status.ready_replicas > 0:
            return ContainerStatusEnum.RUNNING.value
        elif deployment.status.replicas and deployment.status.replicas > 0:
            return ContainerStatusEnum.INIT.value
        else:
            return ContainerStatusEnum.STOPPED.value
    except Exception as e:
        logger.error("Error getting deployment status for %s: %s", deployment_name, e)
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

    api_url = os.getenv("API_URL")
    if api_url is None:
        logger.error("API_URL not found in .env")
        return []

    return [
        V1EnvVar(name="API_URL", value=api_url),
    ]


def get_pod_ips_by_label(label_selector, namespace=None):
    if namespace is None:
        namespace = get_namespace()
    api = get_k8s_client()

    pods = api.list_namespaced_pod(namespace, label_selector=label_selector)

    ips = [pod.status.pod_ip for pod in pods.items if pod.status.pod_ip]
    return ips


@retry(stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, min=1, max=10))
def create_deployment(image: str, name: str, env_vars: list = None, **kwargs):
    """Create a Kubernetes Deployment for engine

    Args:
        image: Container image
        name: Deployment name
        env_vars: List of environment variable strings (KEY=VALUE format) - will be stored in Secret
        **kwargs: Additional deployment configuration

    Returns:
        Created deployment object
    """

    apps_api = client.AppsV1Api()
    namespace = get_namespace()

    # Create Secret for environment variables
    secret_name = f"{name}-env"
    env_data = {}

    # Add default env vars
    default_env = get_default_env()
    for env_var in default_env:
        env_data[env_var.name] = env_var.value

    # Add custom env vars from list
    if env_vars:
        for env_str in env_vars:
            if "=" in env_str:
                key, value = env_str.split("=", 1)
                env_data[key] = value

    # Create or update Secret
    create_secret(secret_name, env_data)

    # Resource limits
    resources = V1ResourceRequirements(
        limits={
            "cpu": "1",
            "memory": "512Mi",
        },
        requests={
            "cpu": "50m",
            "memory": "128Mi",
        },
    )

    # Volume mounts for flow file
    volume_mounts = kwargs.get("volume_mounts", [])
    volumes = kwargs.get("volumes", [])

    # Container definition with envFrom to load all env vars from Secret
    container = V1Container(
        name="engine",
        image=image,
        env_from=[V1EnvFromSource(secret_ref=V1SecretEnvSource(name=secret_name))],
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

    # Pod template
    pod_template = V1PodTemplateSpec(
        metadata=V1ObjectMeta(labels=labels),
        spec=V1PodSpec(
            containers=[container],
            restart_policy="Always",
            volumes=volumes if volumes else None,
            image_pull_secrets=[V1LocalObjectReference(name="registry-secret")],
            hostname=name,
            subdomain="bot-provider",
        ),
    )

    # Deployment spec
    deployment_spec = V1DeploymentSpec(
        replicas=1,
        selector=V1LabelSelector(match_labels=labels),
        template=pod_template,
    )

    # Deployment metadata
    deployment = V1Deployment(
        api_version="apps/v1",
        kind="Deployment",
        metadata=V1ObjectMeta(
            name=name,
            namespace=namespace,
            labels=labels,
        ),
        spec=deployment_spec,
    )

    try:
        remove_service(name)
        created_deployment = apps_api.create_namespaced_deployment(namespace=namespace, body=deployment)
        logger.info("Created deployment: %s in namespace: %s", name, namespace)
        return created_deployment
    except Exception as e:
        logger.error("Error creating deployment %s: %s", name, e)
        raise


def remove_deployment(deployment_name: str):
    """Remove a Kubernetes deployment and its associated Secret

    Args:
        deployment_name: Name of the deployment to remove

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        apps_api = client.AppsV1Api()
        namespace = get_namespace()

        # Delete deployment
        apps_api.delete_namespaced_deployment(name=deployment_name, namespace=namespace)
        logger.info("Removed deployment: %s", deployment_name)

        # Delete associated Secret
        secret_name = f"{deployment_name}-env"
        delete_secret(secret_name)

        return True
    except Exception as e:
        logger.error("Error removing deployment %s: %s", deployment_name, e)
        return False


def create_configmap(name: str, data: dict):
    """Create a ConfigMap for storing flow configuration

    Args:
        name: ConfigMap name
        data: Dictionary of data to store

    Returns:
        Created ConfigMap object
    """

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
        except ApiException as e:
            if e.status == 409:  # Conflict - ConfigMap already exists
                # Update existing
                updated = api.replace_namespaced_config_map(name=name, namespace=namespace, body=configmap)
                logger.info("Updated ConfigMap: %s", name)
                return updated
            raise
    except ApiException as e:
        logger.error("Error managing ConfigMap %s: %s", name, e)
        raise


def create_secret(name: str, data: dict):
    """Create a Secret for storing sensitive environment variables

    Args:
        name: Secret name
        data: Dictionary of key-value pairs (will be base64 encoded automatically)

    Returns:
        Created Secret object
    """
    from kubernetes.client import V1Secret, V1ObjectMeta
    import base64

    api = get_k8s_client()
    namespace = get_namespace()

    # Encode data to base64
    encoded_data = {}
    for key, value in data.items():
        if isinstance(value, str):
            encoded_data[key] = base64.b64encode(value.encode()).decode()
        else:
            encoded_data[key] = base64.b64encode(str(value).encode()).decode()

    secret = V1Secret(
        api_version="v1",
        kind="Secret",
        metadata=V1ObjectMeta(
            name=name,
            namespace=namespace,
        ),
        type="Opaque",
        data=encoded_data,
    )

    try:
        # Try to create, if exists update
        try:
            created = api.create_namespaced_secret(namespace=namespace, body=secret)
            logger.info("Created Secret: %s", name)
            return created
        except ApiException as e:
            if e.status == 409:  # Conflict - Secret already exists
                # Update existing
                updated = api.replace_namespaced_secret(name=name, namespace=namespace, body=secret)
                logger.info("Updated Secret: %s", name)
                return updated
            raise
    except ApiException as e:
        logger.error("Error managing Secret %s: %s", name, e)
        raise


def delete_secret(name: str):
    """Delete a Secret

    Args:
        name: Secret name

    Returns:
        bool: True if successful
    """
    try:
        api = get_k8s_client()
        namespace = get_namespace()
        api.delete_namespaced_secret(name=name, namespace=namespace)
        logger.info("Deleted Secret: %s", name)
        return True
    except Exception as e:
        logger.error("Error deleting Secret %s: %s", name, e)
        return False


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
    """Deploy an engine deployment for a project

    Args:
        project: ProjectModel instance
        prefix: Engine prefix (debug/release)
        flow: Bot flow configuration
        key: Unique engine key
        _env: Additional environment variables

    Returns:
        Created deployment object
    """
    from kubernetes.client import V1VolumeMount, V1Volume, V1ConfigMapVolumeSource

    if _env is None:
        _env = []

    deployment_name = f"{prefix}-{key}".lower().replace("_", "-")
    configmap_name = f"{deployment_name}-flow"

    # Create ConfigMap with flow
    flow_json = json.dumps(flow, indent=4)
    create_configmap(configmap_name, {"flow.json": flow_json})

    # Get MongoDB credentials
    try:
        mongo_credentials = project.get_mongo_credentials()
        logger.info("Using MongoDB credentials for project %s: %s", project.id, mongo_credentials["username"])
    except Exception as e:
        logger.error("Failed to get MongoDB credentials for project %s: %s", project.id, e)
        mongo_credentials = {"connection_string": env.str("MONGO_URL"), "database": f"project_{project.id}"}

    # Build environment variables
    _env.append(f"BOT_TOKEN={env.str('TEST_BOT_TOKEN')}")
    _env.append("FLOW_FILE_PATH=/app/assets/flow.json")
    _env.append("WEBHOOK_ENABLED=true")
    _env.append("WEBHOOK_PORT=8000")
    _env.append("REDIS_ENABLED=true")
    _env.append(f"REDIS_ADDR={env.str('REDIS_HOST', default='redis')}:{env.str('REDIS_PORT', default='6379')}")
    _env.append(f"REDIS_PASSWORD={env.str("REDIS_PASSWORD")}")
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
            ),
        )
    ]

    image = f"registry.jscorp.uz/golang-engine:{engine_version()}"

    return create_deployment(
        image=image,
        name=deployment_name,
        env_vars=_env,
        volume_mounts=volume_mounts,
        volumes=volumes,
        project_id=project.id,
    )


def stop_project_deployments(project_id: int):
    """Stop all engine deployments for a project

    Args:
        project_id: Project ID

    Returns:
        int: Number of deployments stopped
    """
    try:
        apps_api = client.AppsV1Api()
        namespace = get_namespace()

        # List deployments with project_id label
        deployments = apps_api.list_namespaced_deployment(
            namespace=namespace, label_selector=f"project_id={project_id}"
        )

        count = 0
        for deployment in deployments.items:
            try:
                apps_api.delete_namespaced_deployment(name=deployment.metadata.name, namespace=namespace)
                logger.info("Stopped deployment %s for project %s", deployment.metadata.name, project_id)
                count += 1
            except Exception as e:
                logger.error("Error stopping deployment %s: %s", deployment.metadata.name, e)

        return count
    except Exception as e:
        logger.error("Error stopping project deployments for %s: %s", project_id, e)
        return 0


async def deployment_logs_async(deployment_name: str):
    """Stream deployment logs asynchronously

    Args:
        deployment_name: Name of the deployment

    Yields:
        Log lines
    """
    try:
        # Load config
        try:
            config.load_incluster_config()
        except config.ConfigException:
            config.load_kube_config()

        api = client.CoreV1Api()
        namespace = get_namespace()

        # Get pods for this deployment
        label_selector = f"engine-name={deployment_name}"
        pods = api.list_namespaced_pod(namespace=namespace, label_selector=label_selector)

        if not pods.items:
            yield "No pods found for deployment"
            return

        pod_name = pods.items[0].metadata.name

        w = watch.Watch()
        for line in w.stream(
            api.read_namespaced_pod_log,
            name=pod_name,
            namespace=namespace,
            follow=True,
        ):
            yield line
    except Exception as e:
        logger.error("Error streaming logs for deployment %s: %s", deployment_name, e)
        yield f"Error: {str(e)}"
