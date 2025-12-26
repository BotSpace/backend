"""
Engine orchestration service.

This module provides functions for managing bot engines using Kubernetes deployments.
Engine instances are deployed as Kubernetes deployments with appropriate resource limits.
"""
import logging
import os

from config.env import env

from core.apps.api.enums.container import ContainerStatusEnum
from core.apps.api.services.kubernetes_service import (
    deploy_engine,
    get_deployment_status,
    deployment_logs_async,
    remove_deployment,
    stop_project_deployments,
    convert_k8s_event_status,
)


logger = logging.getLogger(__name__)


async def service_logs_async(service_id):
    """Stream logs for a deployment asynchronously
    
    Args:
        service_id: Kubernetes deployment name
        
    Yields:
        Log lines
    """
    async for line in deployment_logs_async(service_id):
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
    """Get the status of a deployment
    
    Args:
        service_id: Kubernetes deployment name
        
    Returns:
        str: Container status enum value
    """
    return get_deployment_status(service_id)


def remove_service(service_id):
    """Remove a deployment
    
    Args:
        service_id: Kubernetes deployment name
        
    Returns:
        bool: True if successful, False otherwise
    """
    return remove_deployment(service_id)


def get_default_env():
    """Get default environment variables for engine deployments
    
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
    """Deploy engine deployment for project with MongoDB credentials

    Args:
        project: ProjectModel instance
        prefix: Service prefix (debug/release)
        flow: Bot flow configuration
        key: Unique service key
        _env: Additional environment variables

    Returns:
        Created Kubernetes deployment
    """
    # Add default env vars
    _env.extend(get_default_env())
    return deploy_engine(project, prefix, flow, key, _env)


def stop_project_services(project_id: int):
    """Stop all engine deployments for a project
    
    Args:
        project_id: Project ID
        
    Returns:
        int: Number of deployments stopped
    """
    return stop_project_deployments(project_id)
