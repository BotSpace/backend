# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the BotMother backend application with node-local Redis access.

## Architecture Overview

The deployment consists of:
- **Redis DaemonSet**: Runs one Redis instance per Kubernetes node
- **API Deployment**: Django application that connects to Redis on the same node via node IP
- **Supporting resources**: ConfigMaps, Secrets, PVCs, Services

### Node-Local Redis Architecture

The key feature of this setup is that each API pod connects to the Redis instance running on the same physical node:

1. Redis runs as a **DaemonSet** with `hostNetwork: true`, making it accessible on each node's IP
2. The API Deployment uses Kubernetes **Downward API** to inject the node's IP as `NODE_IP` environment variable
3. The `REDIS_URL` is dynamically constructed as `redis://$(NODE_IP):6379`
4. This ensures the API pod always connects to the Redis instance on its node

## Files

- `namespace.yaml` - Creates the botmother namespace
- `redis-daemonset.yaml` - Redis DaemonSet configuration
- `api-deployment.yaml` - API application deployment
- `api-service.yaml` - Service to expose the API
- `api-configmap.yaml` - Configuration settings
- `api-secrets.yaml.example` - Secret template (copy and customize)
- `pvcs.yaml` - Persistent volume claims for logs, media, and static files

## Prerequisites

1. A running Kubernetes cluster
2. `kubectl` configured to access your cluster
3. A storage class named `standard` (or modify `pvcs.yaml` to use your storage class)
4. Docker images pushed to your registry

## Deployment Steps

### 1. Create Namespace

```bash
kubectl apply -f namespace.yaml
```

### 2. Create Secrets

Copy the secrets template and update with your actual values:

```bash
cp api-secrets.yaml.example api-secrets.yaml
# Edit api-secrets.yaml with your actual secret values
kubectl apply -f api-secrets.yaml
```

**Important**: Never commit `api-secrets.yaml` to version control!

### 3. Create ConfigMap

```bash
kubectl apply -f api-configmap.yaml
```

### 4. Create Persistent Volume Claims

```bash
kubectl apply -f pvcs.yaml
```

### 5. Deploy Redis DaemonSet

```bash
kubectl apply -f redis-daemonset.yaml
```

Verify Redis is running on all nodes:

```bash
kubectl get daemonset -n botmother
kubectl get pods -n botmother -l app=redis -o wide
```

### 6. Deploy API Application

```bash
kubectl apply -f api-deployment.yaml
kubectl apply -f api-service.yaml
```

### 7. Verify Deployment

Check that pods are running:

```bash
kubectl get pods -n botmother
```

Check API pod logs:

```bash
kubectl logs -n botmother -l app=api --tail=50
```

Verify Redis connection from API pod:

```bash
# Get the node IP and Redis URL being used
kubectl exec -n botmother deployment/api -- env | grep -E 'NODE_IP|REDIS'
```

## How Node-Local Redis Works

When an API pod starts:

1. Kubernetes Downward API injects `status.hostIP` into the `NODE_IP` environment variable
2. The `REDIS_URL` environment variable is set to `redis://$(NODE_IP):6379`
3. The application reads this URL and connects to Redis on the local node
4. Since Redis uses `hostNetwork: true`, it's accessible on the node's IP at port 6379

Example:
- API pod scheduled on node with IP `10.0.1.5`
- `NODE_IP` = `10.0.1.5`
- `REDIS_URL` = `redis://10.0.1.5:6379`
- The pod connects to Redis running on the same node

## Scaling

### Scaling the API

You can scale the API deployment:

```bash
kubectl scale deployment api -n botmother --replicas=3
```

Each pod will connect to the Redis instance on its respective node.

### Redis DaemonSet

The DaemonSet automatically runs one Redis instance per node. When you add nodes to your cluster, Redis will automatically be deployed on new nodes.

## Monitoring

Check Redis status on each node:

```bash
kubectl exec -n botmother daemonset/redis -- redis-cli ping
```

Check API health:

```bash
kubectl exec -n botmother deployment/api -- curl -f http://localhost:8000/health/
```

## Troubleshooting

### API cannot connect to Redis

1. Check if Redis is running on the node:
   ```bash
   kubectl get pods -n botmother -l app=redis -o wide
   ```

2. Verify NODE_IP is set correctly:
   ```bash
   kubectl exec -n botmother deployment/api -- printenv | grep NODE_IP
   ```

3. Check if Redis is accessible from the API pod:
   ```bash
   kubectl exec -n botmother deployment/api -- nc -zv $NODE_IP 6379
   ```

### Redis not running on a node

Check DaemonSet events:
```bash
kubectl describe daemonset redis -n botmother
```

Check node labels and taints:
```bash
kubectl describe node <node-name>
```

### Port conflicts

If port 6379 is already in use on a node, you'll need to:
1. Stop the conflicting service
2. Or modify the Redis port in both `redis-daemonset.yaml` and `api-deployment.yaml`

## Security Considerations

1. **Secrets**: Always use Kubernetes secrets for sensitive data, never hardcode them
2. **Network Policies**: Consider adding NetworkPolicies to restrict traffic
3. **RBAC**: Ensure proper RBAC policies are in place
4. **Redis Password**: For production, configure Redis with authentication:
   - Add `--requirepass <password>` to Redis args
   - Update `REDIS_URL` to include password: `redis://:<password>@$(NODE_IP):6379`

## Production Recommendations

1. **Use a proper storage class** for PVCs (e.g., SSD-backed storage)
2. **Configure resource limits** appropriately based on your workload
3. **Set up monitoring** (Prometheus, Grafana) for Redis and API metrics
4. **Enable Redis persistence** properly configured for your data durability needs
5. **Configure backup** for Redis data if needed
6. **Use Ingress** to expose the API service externally
7. **Add HorizontalPodAutoscaler** for API deployment to handle load

## Clean Up

To remove all resources:

```bash
kubectl delete -f api-service.yaml
kubectl delete -f api-deployment.yaml
kubectl delete -f redis-daemonset.yaml
kubectl delete -f pvcs.yaml
kubectl delete -f api-configmap.yaml
kubectl delete -f api-secrets.yaml
kubectl delete -f namespace.yaml
```

Or delete the entire namespace (this will remove all resources):

```bash
kubectl delete namespace botmother
```
