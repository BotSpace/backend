"""Minimal stub for kubernetes.client used in local test runs."""
from kubernetes.client.rest import ApiException  # noqa: F401


class _Stub:
    def __init__(self, *a, **kw): ...
    def __call__(self, *a, **kw): return self


# Populate all names imported across the codebase
ApiClient = _Stub
AppsV1Api = _Stub
Configuration = _Stub
CoreV1Api = _Stub
V1ConfigMap = _Stub
V1ConfigMapVolumeSource = _Stub
V1Container = _Stub
V1ContainerPort = _Stub
V1Deployment = _Stub
V1DeploymentList = _Stub
V1DeploymentSpec = _Stub
V1EnvFromSource = _Stub
V1EnvVar = _Stub
V1LabelSelector = _Stub
V1LocalObjectReference = _Stub
V1ObjectMeta = _Stub
V1Pod = _Stub
V1PodList = _Stub
V1PodSpec = _Stub
V1PodTemplateSpec = _Stub
V1ResourceRequirements = _Stub
V1Secret = _Stub
V1SecretEnvSource = _Stub
V1Service = _Stub
V1ServicePort = _Stub
V1ServiceSpec = _Stub
V1Volume = _Stub
V1VolumeMount = _Stub
