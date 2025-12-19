# type: ignore
"""
Engine orchestration service.

This module provides functions for managing bot engines using Kubernetes pods.
Engine instances are deployed as Kubernetes pods with appropriate resource limits.
"""
import logging
import os

from config.env import env

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.services.kubernetes_service import (
    deploy_engine,
    get_pod_status,
    pod_logs_async,
    remove_pod,
    stop_project_pods,
    convert_k8s_event_status,
)


logger = logging.getLogger(__name__)


async def service_logs_async(service_id):
    """Stream logs for a pod asynchronously
    
    Args:
        service_id: Kubernetes pod name
        
    Yields:
        Log lines
    """
    async for line in pod_logs_async(service_id):
        yield line


def convert_status(status):
    """Convert status string to container status enum value
    
    Args:
        status: Status string from Kubernetes event
        
    Returns:
        str: Container status enum value
    """
    return convert_k8s_event_status("MODIFIED", status)


def get_service_status(service_id):
    """Get the status of a pod
    
    Args:
        service_id: Kubernetes pod name
        
    Returns:
        str: Container status enum value
    """
    return get_pod_status(service_id)


def remove_service(service_id):
    """Remove a pod
    
    Args:
        service_id: Kubernetes pod name
        
    Returns:
        bool: True if successful, False otherwise
    """
    return remove_pod(service_id)


def get_default_env():
    """Get default environment variables for engine pods
    
    Returns:
        list: List of environment variable strings
    """
    api_url = os.getenv("API_URL")
    if api_url is None:
        logger.error("API_URL not found for .env")
        return []
    return [
        f"API_URL={api_url}",
    ]


def deploy_service(project, prefix, flow, key, _env: list = []):
    """Deploy engine pod for project with MongoDB credentials

    Args:
        project: ProjectModel instance
        prefix: Service prefix (debug/release)
        flow: Bot flow configuration
        key: Unique service key
        _env: Additional environment variables

    Returns:
        Created Kubernetes pod
    """
    # Add default env vars
    _env.extend(get_default_env())
    return deploy_engine(project, prefix, flow, key, _env)


def stop_project_services(project_id: int):
    """Stop all engine pods for a project
    
    Args:
        project_id: Project ID
        
    Returns:
        int: Number of pods stopped
    """
    return stop_project_pods(project_id)
