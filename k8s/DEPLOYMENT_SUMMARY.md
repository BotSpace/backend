# Kubernetes Deployment Summary

## Overview

This deployment replaces the previous supervisord-based multi-process container setup with Kubernetes-native deployments following best practices.

## What Changed

### Before (Docker Swarm with supervisord)
- Single container running multiple processes via supervisord
  - Django web application (Gunicorn)
  - Celery worker
  - Celery beat
- PostgreSQL and Redis deployed in Docker Swarm
- Scaling required scaling the entire stack

### After (Kubernetes)
- Separate deployments for each component:
  - **botmother-web**: Django web application (2 replicas)
  - **botmother-celery-worker**: Background task processor (2 replicas)
  - **botmother-celery-beat**: Periodic task scheduler (1 replica)
  - **botmother-nginx**: Reverse proxy and static files (2 replicas)
- PostgreSQL and Redis are external services (not deployed in k8s)
- Each component can be scaled independently

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Kubernetes Cluster                        │
│                                                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  botmother namespace                                  │  │
│  │                                                        │  │
│  │  ┌──────────────┐     ┌──────────────┐               │  │
│  │  │   Nginx      │────▶│  Web (x2)    │               │  │
│  │  │ LoadBalancer │     │  Django      │               │  │
│  │  └──────────────┘     └──────────────┘               │  │
│  │                             │                          │  │
│  │                             ▼                          │  │
│  │                    ┌─────────────────┐                │  │
│  │                    │  Shared Storage │                │  │
│  │                    │  (PVCs)         │                │  │
│  │                    └─────────────────┘                │  │
│  │                                                        │  │
│  │  ┌──────────────┐     ┌──────────────┐               │  │
│  │  │ Celery Beat  │     │ Celery Worker│               │  │
│  │  │    (x1)      │     │     (x2)     │               │  │
│  │  └──────────────┘     └──────────────┘               │  │
│  │                                                        │  │
│  └────────────────────┬──────────────┬──────────────────┘  │
└─────────────────────┬─┴──────────────┴─┬───────────────────┘
                      │                  │
                      ▼                  ▼
              ┌──────────────┐   ┌──────────────┐
              │  PostgreSQL  │   │    Redis     │
              │  (External)  │   │  (External)  │
              └──────────────┘   └──────────────┘
```

## Deployment Components

### 1. Namespace
- **File**: `namespace.yaml`
- **Purpose**: Isolates resources in the `botmother` namespace

### 2. Configuration
- **ConfigMap** (`configmap.yaml`): Non-sensitive environment variables
- **Secret** (`secret.yaml`): Sensitive credentials (template with placeholders)

### 3. Storage
- **PVCs** (`pvc.yaml`):
  - `botmother-media`: User uploaded files (10Gi)
  - `botmother-static`: Static files (5Gi)
  - `botmother-logs`: Application logs (5Gi)

### 4. Deployments

#### Web Application
- **File**: `deployment-web.yaml`
- **Image**: `registry.jscorp.uz/botmother:latest`
- **Replicas**: 2 (scalable)
- **Resources**: 500m-2 CPU, 512Mi-2Gi RAM
- **Command**: `sh ./resources/scripts/entrypoint-server.sh`
- **Features**:
  - Health checks (liveness & readiness)
  - Runs migrations on startup
  - Serves on port 8000

#### Celery Worker
- **File**: `deployment-celery-worker.yaml`
- **Image**: `registry.jscorp.uz/botmother:latest`
- **Replicas**: 2 (scalable)
- **Resources**: 250m-1 CPU, 256Mi-1Gi RAM
- **Command**: `sh ./resources/scripts/celery-worker.sh`
- **Features**:
  - Processes background tasks
  - Horizontally scalable

#### Celery Beat
- **File**: `deployment-celery-beat.yaml`
- **Image**: `registry.jscorp.uz/botmother:latest`
- **Replicas**: 1 (must be exactly 1)
- **Resources**: 100m-500m CPU, 128Mi-512Mi RAM
- **Command**: `sh ./resources/scripts/celery-beat.sh`
- **Features**:
  - Schedules periodic tasks
  - Should not be scaled (duplicate tasks)

#### Nginx
- **File**: `deployment-nginx.yaml`
- **Image**: `jscorptech/nginx:latest`
- **Replicas**: 2 (scalable)
- **Resources**: 100m-500m CPU, 64Mi-256Mi RAM
- **Features**:
  - Reverse proxy to web service
  - Serves static files and media
  - LoadBalancer service (external access)

### 5. Services
- **botmother-web** (`service-web.yaml`): ClusterIP service on port 8000
- **botmother-nginx** (in `deployment-nginx.yaml`): LoadBalancer on port 80

## Deployment Instructions

### Quick Start
```bash
# 1. Update secrets
vim k8s/secret.yaml

# 2. Apply all manifests
kubectl apply -k k8s/

# 3. Check status
kubectl get pods -n botmother
kubectl get svc -n botmother
```

### Using Kustomize
```bash
kubectl apply -k k8s/
```

### Manual Application
```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/pvc.yaml
kubectl apply -f k8s/deployment-web.yaml
kubectl apply -f k8s/deployment-celery-worker.yaml
kubectl apply -f k8s/deployment-celery-beat.yaml
kubectl apply -f k8s/deployment-nginx.yaml
kubectl apply -f k8s/service-web.yaml
```

## External Dependencies

### PostgreSQL (Required)
- Must be accessible from the Kubernetes cluster
- Update `DB_HOST` and `DB_PASSWORD` in `secret.yaml`
- Default port: 5432

### Redis (Required)
- Must be accessible from the Kubernetes cluster
- Update `REDIS_HOST` and `REDIS_URL` in `secret.yaml`
- Default port: 6379

## Resource Requirements

### Minimum Cluster Resources
- **CPU**: ~3 cores (web: 1, worker: 0.5, beat: 0.2, nginx: 0.2, overhead: 1.1)
- **Memory**: ~4GB (web: 1Gi, worker: 512Mi, beat: 256Mi, nginx: 128Mi, overhead: 2Gi)
- **Storage**: 20Gi with ReadWriteMany support

### Recommended for Production
- **CPU**: 6+ cores
- **Memory**: 8+ GB
- **Storage**: NFS/EFS/Azure Files/GCP Filestore for shared volumes

## Security Considerations

### 1. Secrets Management
- Never commit actual secrets to git
- Use Kubernetes Secrets or external secret managers (Vault, AWS Secrets Manager)
- Rotate secrets regularly

### 2. Network Security
- Use NetworkPolicies to restrict pod-to-pod communication
- Keep PostgreSQL and Redis on a private network
- Use TLS for all external connections

### 3. Host Path Volumes
- `/mnt/engine` is mounted for Docker engine access
- This is required for container management
- Ensure pods with hostPath run on trusted nodes only

### 4. Image Security
- Use specific image tags instead of `latest` in production
- Scan images for vulnerabilities
- Use a private registry

## Scaling

### Scale Web Application
```bash
kubectl scale deployment botmother-web -n botmother --replicas=5
```

### Scale Celery Workers
```bash
kubectl scale deployment botmother-celery-worker -n botmother --replicas=4
```

### DO NOT Scale Celery Beat
Celery beat must always have exactly 1 replica to avoid duplicate scheduled tasks.

## Monitoring

### Check Logs
```bash
# Web logs
kubectl logs -n botmother -l component=web --tail=100 -f

# Worker logs
kubectl logs -n botmother -l component=celery-worker --tail=100 -f

# Beat logs
kubectl logs -n botmother -l component=celery-beat --tail=100 -f
```

### Check Resource Usage
```bash
kubectl top pods -n botmother
kubectl top nodes
```

## Troubleshooting

### Pods Not Starting
```bash
kubectl describe pod <pod-name> -n botmother
kubectl logs <pod-name> -n botmother
```

### Database Connection Issues
1. Check database credentials in secret
2. Verify network connectivity: `kubectl exec -it <pod-name> -n botmother -- nc -zv <DB_HOST> 5432`
3. Check database logs

### Redis Connection Issues
1. Check Redis credentials in secret
2. Verify network connectivity: `kubectl exec -it <pod-name> -n botmother -- nc -zv <REDIS_HOST> 6379`
3. Check Redis logs

### Storage Issues
1. Verify storage class supports ReadWriteMany
2. Check PVC status: `kubectl get pvc -n botmother`
3. Check PV status: `kubectl get pv`

## Updates and Rollbacks

### Update to New Version
```bash
kubectl set image deployment/botmother-web -n botmother \
  web=registry.jscorp.uz/botmother:v1.2.3
```

### Rollback
```bash
kubectl rollout undo deployment/botmother-web -n botmother
```

### Check Rollout Status
```bash
kubectl rollout status deployment/botmother-web -n botmother
```

## Migration from Docker Swarm

### Key Differences
1. **No supervisord**: Each process runs in its own pod
2. **External databases**: PostgreSQL and Redis are not in k8s
3. **Separate scaling**: Scale web, worker, beat independently
4. **Native features**: Use k8s ConfigMaps/Secrets instead of Docker configs
5. **Better observability**: Native k8s logging and monitoring

### Migration Steps
1. Set up external PostgreSQL and Redis
2. Update `secret.yaml` with connection details
3. Deploy to Kubernetes: `kubectl apply -k k8s/`
4. Verify all pods are running
5. Update DNS/load balancer to point to new nginx service
6. Test the application
7. Migrate data if needed
8. Decommission old Docker Swarm stack

## Best Practices

1. **Use specific image tags** in production (not `latest`)
2. **Set resource limits** to prevent resource exhaustion
3. **Use health checks** for automatic recovery
4. **Monitor resource usage** and adjust limits
5. **Regular backups** of PostgreSQL and persistent volumes
6. **Keep secrets secure** - use external secret managers
7. **Use NetworkPolicies** for additional security
8. **Regular updates** of images and dependencies
9. **Test in staging** before deploying to production
10. **Document changes** and maintain this documentation

## Support and Documentation

- Full deployment guide: `k8s/README.md`
- Kubernetes docs: https://kubernetes.io/docs/
- Django docs: https://docs.djangoproject.com/
- Celery docs: https://docs.celeryproject.org/

---

**Last Updated**: 2025-12-23
**Kubernetes Version**: v1.23+
**Application Version**: Latest
