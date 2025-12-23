# Kubernetes Deployment

This directory contains Kubernetes manifests for deploying the BotMother backend application.

## Architecture

The application is deployed with the following components:

- **Web Application** (`deployment-web.yaml`): Django application running with Gunicorn/Uvicorn
- **Celery Worker** (`deployment-celery-worker.yaml`): Background task processor
- **Celery Beat** (`deployment-celery-beat.yaml`): Periodic task scheduler
- **Nginx** (`deployment-nginx.yaml`): Reverse proxy and static file server

**Note**: PostgreSQL and Redis are external services and not deployed in Kubernetes.

## Prerequisites

1. A Kubernetes cluster (v1.20+)
2. `kubectl` configured to access your cluster
3. External PostgreSQL database
4. External Redis instance
5. Storage class `standard` available in your cluster (or modify `pvc.yaml` to use your storage class)

## Deployment Steps

### 1. Update Secrets

Edit `secret.yaml` and update all placeholder values:
- `DJANGO_SECRET_KEY`
- `DB_HOST` and `DB_PASSWORD` (PostgreSQL connection)
- `REDIS_HOST` and `REDIS_URL` (Redis connection)
- `BOT_TOKEN`, `API_URL`
- Payment gateway credentials
- Storage credentials
- And other sensitive values

### 2. Update ConfigMap (if needed)

Edit `configmap.yaml` if you need to change any non-sensitive configuration values.

### 3. Create the namespace

```bash
kubectl apply -f namespace.yaml
```

### 4. Apply all manifests using Kustomize

```bash
kubectl apply -k .
```

Or apply individually:

```bash
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml
kubectl apply -f pvc.yaml
kubectl apply -f deployment-web.yaml
kubectl apply -f deployment-celery-worker.yaml
kubectl apply -f deployment-celery-beat.yaml
kubectl apply -f deployment-nginx.yaml
kubectl apply -f service-web.yaml
```

### 5. Verify deployment

```bash
# Check all pods are running
kubectl get pods -n botmother

# Check services
kubectl get svc -n botmother

# Check logs
kubectl logs -n botmother -l component=web
kubectl logs -n botmother -l component=celery-worker
kubectl logs -n botmother -l component=celery-beat
```

## Scaling

To scale the web application or celery workers:

```bash
# Scale web pods
kubectl scale deployment botmother-web -n botmother --replicas=3

# Scale celery worker pods
kubectl scale deployment botmother-celery-worker -n botmother --replicas=4
```

**Note**: Celery beat should always have exactly 1 replica to avoid duplicate scheduled tasks.

## Updates

To update the application with a new image:

1. Update the image tag in `kustomization.yaml`
2. Apply the changes:
   ```bash
   kubectl apply -k .
   ```

Or use kubectl set image:

```bash
kubectl set image deployment/botmother-web -n botmother web=registry.jscorp.uz/botmother:v1.2.3
kubectl set image deployment/botmother-celery-worker -n botmother celery-worker=registry.jscorp.uz/botmother:v1.2.3
kubectl set image deployment/botmother-celery-beat -n botmother celery-beat=registry.jscorp.uz/botmother:v1.2.3
```

## Monitoring

Check the status of deployments:

```bash
kubectl get deployments -n botmother
kubectl describe deployment botmother-web -n botmother
```

View logs:

```bash
# Web application logs
kubectl logs -n botmother -l component=web --tail=100 -f

# Celery worker logs
kubectl logs -n botmother -l component=celery-worker --tail=100 -f

# Celery beat logs
kubectl logs -n botmother -l component=celery-beat --tail=100 -f
```

## Troubleshooting

### Pods not starting

Check pod status and events:
```bash
kubectl describe pod <pod-name> -n botmother
```

### Database connection issues

Verify the database credentials in the secret and ensure the external PostgreSQL is accessible from the cluster.

### Redis connection issues

Verify the Redis credentials in the secret and ensure the external Redis is accessible from the cluster.

## Resource Requirements

Default resource requests and limits:

- **Web**: 500m CPU, 512Mi RAM (limit: 2 CPU, 2Gi RAM)
- **Celery Worker**: 250m CPU, 256Mi RAM (limit: 1 CPU, 1Gi RAM)
- **Celery Beat**: 100m CPU, 128Mi RAM (limit: 500m CPU, 512Mi RAM)
- **Nginx**: 100m CPU, 64Mi RAM (limit: 500m CPU, 256Mi RAM)

Adjust these values in the deployment files based on your workload.

## Differences from Docker Swarm

Key changes from the previous Docker Swarm deployment (`stack.yaml`):

1. **No supervisord**: Each component runs in its own pod with a single process
2. **Separate deployments**: Web, Celery worker, and Celery beat are independent deployments
3. **External databases**: PostgreSQL and Redis are not deployed in Kubernetes
4. **Native Kubernetes features**: Using ConfigMaps, Secrets, and Deployments instead of Docker configs
5. **Better scaling**: Each component can be scaled independently
