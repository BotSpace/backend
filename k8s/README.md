# Kubernetes Deployment Guide

This directory contains Kubernetes manifests for deploying the BotMother backend application.

## Architecture

The deployment consists of:
- **Web Service**: Django application running the backend API
- **Nginx Service**: Reverse proxy and static file server
- **External PostgreSQL**: Database running on a separate host
- **External Redis**: Cache server running on a separate host

## Directory Structure

```
k8s/
├── base/                          # Base Kubernetes manifests
│   ├── namespace.yaml            # Namespace definition
│   ├── configmap.yaml            # Environment variables
│   ├── secret.yaml               # Sensitive configuration
│   ├── pvc.yaml                  # Persistent Volume Claims
│   ├── deployment-web.yaml       # Web deployment
│   ├── deployment-nginx.yaml     # Nginx deployment
│   ├── service.yaml              # Service definitions
│   └── kustomization.yaml        # Base kustomization
└── overlays/
    └── production/               # Production-specific configs
        ├── configmap-patch.yaml  # Production config overrides
        ├── deployment-patch.yaml # Production resource limits
        └── kustomization.yaml    # Production kustomization
```

## Prerequisites

1. **Kubernetes Cluster**: v1.20 or higher
2. **kubectl**: Configured to access your cluster
3. **kustomize**: For manifest management (built into kubectl 1.14+)
4. **External PostgreSQL**: Running on a separate host
5. **External Redis**: Running on a separate host
6. **Storage Class**: For persistent volumes (ReadWriteMany support recommended)

## Setup Instructions

### 1. Configure External Services

Before deploying, ensure your external PostgreSQL and Redis servers are set up:

#### PostgreSQL Setup
```bash
# On your PostgreSQL server, create the database and user
psql -U postgres
CREATE DATABASE django;
CREATE USER postgres WITH PASSWORD 'your-secure-password';
GRANT ALL PRIVILEGES ON DATABASE django TO postgres;
\q
```

Ensure PostgreSQL is configured to accept connections from your Kubernetes cluster:
- Edit `postgresql.conf`: Set `listen_addresses = '*'`
- Edit `pg_hba.conf`: Add entry for your K8s cluster network
- Restart PostgreSQL

#### Redis Setup
```bash
# On your Redis server, ensure it's configured to accept external connections
# Edit redis.conf:
# bind 0.0.0.0
# protected-mode no  # Or use requirepass for authentication
# Restart Redis
```

### 2. Update Configuration

Edit the following files with your actual values:

#### `k8s/overlays/production/configmap-patch.yaml`
```yaml
DB_HOST: "your-postgres-server-ip-or-hostname"
REDIS_HOST: "your-redis-server-ip-or-hostname"
REDIS_URL: "redis://your-redis-server-ip:6379"
ALLOWED_HOSTS: "web,botmother-web,your-domain.com"
CSRF_TRUSTED_ORIGINS: "https://your-domain.com"
```

#### `k8s/base/secret.yaml`
Update all secret values:
```bash
# It's recommended to create secrets using kubectl instead of storing them in files
kubectl create secret generic botmother-secret \
  --namespace=botmother \
  --from-literal=DJANGO_SECRET_KEY='your-long-random-secret-key' \
  --from-literal=DB_PASSWORD='your-db-password' \
  --from-literal=SMS_LOGIN='your-sms-login' \
  --from-literal=SMS_PASSWORD='your-sms-password' \
  --from-literal=BOT_TOKEN='your-bot-token' \
  --dry-run=client -o yaml > k8s/base/secret-generated.yaml
```

### 3. Update Storage Class

Edit `k8s/base/pvc.yaml` and change `storageClassName` to match your cluster's storage class:

```bash
# List available storage classes
kubectl get storageclass

# Update PVC files with the appropriate storage class
```

### 4. Update Image Registry

Edit `k8s/overlays/production/kustomization.yaml`:
```yaml
images:
  - name: registry.jscorp.uz/botmother
    newTag: "your-image-tag"  # e.g., v1.0.0, latest, etc.
```

If using a private registry, create an image pull secret:
```bash
kubectl create secret docker-registry registry-credentials \
  --namespace=botmother \
  --docker-server=registry.jscorp.uz \
  --docker-username=your-username \
  --docker-password=your-password \
  --docker-email=your-email
```

Then uncomment the `imagePullSecrets` section in deployment files.

### 5. Deploy to Kubernetes

#### Using kubectl with kustomize
```bash
# Dry run to preview changes
kubectl apply -k k8s/overlays/production --dry-run=client

# Apply the manifests
kubectl apply -k k8s/overlays/production

# Watch the deployment
kubectl get pods -n botmother -w
```

#### Using kustomize separately
```bash
# Build the manifests
kustomize build k8s/overlays/production > deployment.yaml

# Review the output
cat deployment.yaml

# Apply
kubectl apply -f deployment.yaml
```

### 6. Verify Deployment

```bash
# Check all resources
kubectl get all -n botmother

# Check pod logs
kubectl logs -n botmother -l component=web --tail=100
kubectl logs -n botmother -l component=nginx --tail=100

# Check pod status
kubectl describe pod -n botmother <pod-name>

# Test database connectivity
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py check --database default

# Run migrations
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py migrate

# Create superuser
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py createsuperuser
```

### 7. Access the Application

#### Using LoadBalancer (if supported)
```bash
# Get the external IP
kubectl get svc -n botmother botmother-nginx

# Access the application
curl http://<EXTERNAL-IP>/health/
```

#### Using NodePort
Edit `k8s/base/service.yaml` to change service type to NodePort and set a nodePort:
```yaml
spec:
  type: NodePort
  ports:
  - port: 80
    targetPort: 80
    nodePort: 30080  # Choose a port in range 30000-32767
```

Access via: `http://<node-ip>:30080`

#### Using Ingress
Create an Ingress resource (example):
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: botmother-ingress
  namespace: botmother
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - your-domain.com
    secretName: botmother-tls
  rules:
  - host: your-domain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: botmother-nginx
            port:
              number: 80
```

## Updating the Application

### Update Image Tag
```bash
# Edit kustomization.yaml
cd k8s/overlays/production
# Change newTag to new version

# Apply changes
kubectl apply -k .

# Or use kubectl set image
kubectl set image deployment/botmother-web web=registry.jscorp.uz/botmother:new-tag -n botmother
kubectl set image deployment/botmother-nginx nginx=jscorptech/nginx:new-tag -n botmother
```

### Update Configuration
```bash
# Edit configmap or secret files
# Apply changes
kubectl apply -k k8s/overlays/production

# Restart deployments to pick up changes
kubectl rollout restart deployment/botmother-web -n botmother
kubectl rollout restart deployment/botmother-nginx -n botmother
```

## Scaling

```bash
# Scale web deployment
kubectl scale deployment botmother-web --replicas=3 -n botmother

# Scale nginx deployment
kubectl scale deployment botmother-nginx --replicas=3 -n botmother

# Or edit the deployment-patch.yaml file and apply
```

## Troubleshooting

### Pods Not Starting
```bash
# Check pod events
kubectl describe pod -n botmother <pod-name>

# Check logs
kubectl logs -n botmother <pod-name>

# Check if image can be pulled
kubectl get events -n botmother --sort-by='.lastTimestamp'
```

### Database Connection Issues
```bash
# Test connectivity from a pod
kubectl exec -n botmother -it deployment/botmother-web -- sh
# Inside the pod:
nc -zv <db-host> 5432
# or
python manage.py check --database default
```

### Redis Connection Issues
```bash
# Test connectivity from a pod
kubectl exec -n botmother -it deployment/botmother-web -- sh
# Inside the pod:
nc -zv <redis-host> 6379
# or
python -c "import redis; r=redis.Redis(host='<redis-host>'); r.ping()"
```

### Persistent Volume Issues
```bash
# Check PVC status
kubectl get pvc -n botmother

# Check PV status
kubectl get pv

# Describe PVC for details
kubectl describe pvc -n botmother <pvc-name>
```

## Monitoring

```bash
# Watch pods
kubectl get pods -n botmother -w

# Check resource usage
kubectl top pods -n botmother
kubectl top nodes

# View logs continuously
kubectl logs -n botmother -l component=web -f
```

## Backup and Restore

### Database Backup
Since PostgreSQL is external, use standard PostgreSQL backup tools:
```bash
# On PostgreSQL server
pg_dump -U postgres django > backup.sql

# Restore
psql -U postgres django < backup.sql
```

### Persistent Volumes Backup
Use your cloud provider's snapshot features or tools like Velero for Kubernetes-native backups.

## Security Best Practices

1. **Use Secrets Manager**: Consider using external secrets management (e.g., HashiCorp Vault, AWS Secrets Manager)
2. **Network Policies**: Implement network policies to restrict traffic
3. **RBAC**: Configure proper Role-Based Access Control
4. **Pod Security**: Use Pod Security Standards/Policies
5. **TLS**: Enable TLS for all external communications
6. **Regular Updates**: Keep images and dependencies updated

## Rollback

```bash
# View rollout history
kubectl rollout history deployment/botmother-web -n botmother

# Rollback to previous version
kubectl rollout undo deployment/botmother-web -n botmother

# Rollback to specific revision
kubectl rollout undo deployment/botmother-web --to-revision=2 -n botmother
```

## Clean Up

```bash
# Delete all resources
kubectl delete -k k8s/overlays/production

# Or delete namespace (this will delete everything in it)
kubectl delete namespace botmother
```

## Migration from Docker Swarm

If you're migrating from Docker Swarm:

1. **Export Data**: Backup your PostgreSQL and Redis data from the Swarm deployment
2. **Setup External Services**: Install PostgreSQL and Redis on separate hosts and restore data
3. **Update Configs**: Configure the Kubernetes manifests with external service endpoints
4. **Deploy to K8s**: Follow the deployment instructions above
5. **Verify**: Test all functionality before decommissioning the Swarm stack
6. **Switch Traffic**: Update DNS/load balancer to point to the new K8s service

## Support

For issues:
- Check pod logs: `kubectl logs -n botmother <pod-name>`
- Check events: `kubectl get events -n botmother --sort-by='.lastTimestamp'`
- Review [Kubernetes documentation](https://kubernetes.io/docs/)
