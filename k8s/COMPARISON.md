# Deployment Comparison: Docker Swarm vs Kubernetes

## Overview

This document compares the old Docker Swarm deployment with the new Kubernetes deployment.

## Architecture Comparison

### Docker Swarm (Old - stack.yaml)

```
Single Stack:
├── PostgreSQL (container)
│   └── Volume: pg_data
├── Redis (container)
│   └── Volume: redis_data
├── Web (Django app)
│   ├── Replicas: 1
│   └── Volumes: media, static, logs, pycache, engine
└── Nginx (reverse proxy)
    ├── Replicas: 1
    └── Volumes: media (ro), static (ro)

Network: Overlay network (botmother)
Secrets: Docker secrets
Deployment: docker stack deploy -c stack.yaml
```

### Kubernetes (New - k8s/)

```
External Services:
├── PostgreSQL (dedicated host)
│   └── Connection: DB_HOST env var
└── Redis (dedicated host)
    └── Connection: REDIS_HOST env var

Kubernetes Cluster:
├── Namespace: botmother
├── Web (Django app)
│   ├── Replicas: 2 (HA)
│   ├── ConfigMap: botmother-config
│   ├── Secret: botmother-secret
│   └── PVCs: media, static, logs, pycache, engine
└── Nginx (reverse proxy)
    ├── Replicas: 2 (HA)
    └── PVCs: media (ro), static (ro)

Deployment: kubectl apply -k k8s/overlays/production
```

## Feature Comparison

| Feature | Docker Swarm | Kubernetes |
|---------|-------------|------------|
| **Scalability** | Manual, same host | Auto-scaling, multi-host |
| **High Availability** | Limited | Full HA with replicas |
| **Database** | In container | External dedicated host |
| **Redis** | In container | External dedicated host |
| **Replicas** | 1 each | 2+ each (configurable) |
| **Health Checks** | Basic | Advanced with probes |
| **Rolling Updates** | Basic | Advanced with strategies |
| **Rollback** | Manual | Built-in |
| **Secrets** | Docker secrets | Kubernetes secrets |
| **Storage** | Local volumes | PersistentVolumes |
| **Networking** | Overlay network | Service mesh ready |
| **Monitoring** | Limited | Rich ecosystem |
| **Resource Limits** | Basic | Granular |

## Deployment Commands

### Docker Swarm

```bash
# Deploy
docker stack deploy -c stack.yaml botmother

# Update
docker service update botmother_web --image registry.jscorp.uz/botmother:new-tag

# Scale
docker service scale botmother_web=3

# Logs
docker service logs botmother_web

# Remove
docker stack rm botmother
```

### Kubernetes

```bash
# Deploy
kubectl apply -k k8s/overlays/production

# Update
kubectl set image deployment/botmother-web web=registry.jscorp.uz/botmother:new-tag -n botmother

# Scale
kubectl scale deployment botmother-web --replicas=3 -n botmother

# Logs
kubectl logs -n botmother -l component=web --tail=100

# Remove
kubectl delete -k k8s/overlays/production
```

## Configuration Comparison

### Environment Variables

**Docker Swarm:**
- Configured in `stack.yaml` under `environment:`
- Hard-coded in stack file
- Some use `.env` file

**Kubernetes:**
- Stored in ConfigMap (`k8s/base/configmap.yaml`)
- Easily updatable without redeployment
- Supports overlays for different environments

### Secrets

**Docker Swarm:**
```bash
# Create secret
echo "mypassword" | docker secret create db_password -

# Reference in stack.yaml
secrets:
  - db_password
```

**Kubernetes:**
```bash
# Create secret
kubectl create secret generic botmother-secret \
  --from-literal=DB_PASSWORD='mypassword'

# Reference in deployment
envFrom:
  - secretRef:
      name: botmother-secret
```

### Storage

**Docker Swarm:**
- Local volumes on single node
- Simple volume declarations
- Limited sharing across replicas

**Kubernetes:**
- PersistentVolumeClaims
- Can use cloud storage (EBS, GCE PD, Azure Disk)
- ReadWriteMany for sharing
- Snapshots and backups

## Migration Impact

### Breaking Changes
- ❌ PostgreSQL and Redis must be on external hosts
- ❌ Different connection strings (DB_HOST, REDIS_HOST)
- ❌ Different deployment commands
- ❌ Secrets must be recreated in Kubernetes

### Compatible Features
- ✅ Same Docker images can be used
- ✅ Same application code
- ✅ Same environment variables (mostly)
- ✅ Same health check endpoints
- ✅ Same CI/CD can build images

## Performance Comparison

### Resource Usage

**Docker Swarm:**
- Lower overhead (simpler orchestration)
- All on one node (less network latency)
- Limited resource isolation

**Kubernetes:**
- Higher overhead (more components)
- Distributed (may have network latency)
- Better resource isolation and limits

### Scalability

**Docker Swarm:**
- Limited to node resources
- Manual scaling
- Single point of failure

**Kubernetes:**
- Horizontal scaling across nodes
- Auto-scaling possible
- High availability built-in

## Operations Comparison

### Deployment Time

**Docker Swarm:**
- Fast (seconds)
- Simple process
- Less validation

**Kubernetes:**
- Moderate (30-60 seconds)
- More validation
- Health checks before ready

### Troubleshooting

**Docker Swarm:**
```bash
docker service ls
docker service ps botmother_web
docker service logs botmother_web -f
```

**Kubernetes:**
```bash
kubectl get pods -n botmother
kubectl describe pod -n botmother <pod-name>
kubectl logs -n botmother <pod-name> -f
kubectl get events -n botmother
```

## When to Use Each

### Use Docker Swarm When:
- ❌ Small, simple deployments
- ❌ Single node is sufficient
- ❌ Minimal operations overhead needed
- ❌ Learning curve is a concern
- **Note:** Docker Swarm mode is being phased out by Docker

### Use Kubernetes When:
- ✅ Production workloads (recommended)
- ✅ Need high availability
- ✅ Multi-host deployments
- ✅ Advanced features needed (auto-scaling, etc.)
- ✅ Industry-standard platform
- ✅ Rich ecosystem and community

## Migration Benefits

### Advantages of Kubernetes

1. **Better Scalability**: Easy horizontal scaling across multiple nodes
2. **High Availability**: Multiple replicas with automatic failover
3. **External Databases**: PostgreSQL and Redis on dedicated hosts for better performance
4. **Resource Management**: Fine-grained CPU/memory limits
5. **Rolling Updates**: Zero-downtime deployments
6. **Self-Healing**: Automatic restart of failed pods
7. **Rich Ecosystem**: Monitoring, logging, service mesh options
8. **Industry Standard**: Better support and documentation
9. **Future-Proof**: Active development and community

### Trade-offs

1. **Complexity**: More complex than Docker Swarm
2. **Learning Curve**: Requires Kubernetes knowledge
3. **Overhead**: More resources for Kubernetes itself
4. **Setup Time**: Initial setup takes longer

## Cost Comparison

### Docker Swarm
- **Infrastructure**: Single server or small cluster
- **Maintenance**: Lower (simpler system)
- **Licensing**: Free (Docker Engine)
- **Total**: Lower initial cost, limited scalability

### Kubernetes
- **Infrastructure**: Cluster (3+ nodes recommended)
- **Maintenance**: Higher (more components)
- **External DB/Redis**: Additional servers
- **Licensing**: Free (open source)
- **Total**: Higher cost but better value at scale

## Conclusion

The migration from Docker Swarm to Kubernetes represents a move to a more robust, scalable, and industry-standard platform. While Kubernetes has a steeper learning curve, it provides better:

- **Production readiness**
- **High availability**
- **Scalability**
- **Operational features**
- **Long-term support**

The investment in learning Kubernetes pays off with a more maintainable and scalable infrastructure.

## Recommended Path

1. ✅ Learn Kubernetes basics
2. ✅ Setup external PostgreSQL and Redis
3. ✅ Deploy to test environment first
4. ✅ Test thoroughly
5. ✅ Migrate production with proper planning
6. ✅ Monitor and optimize

---

**Status**: Migration complete. Kubernetes deployment ready.
