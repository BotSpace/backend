# Pre-Deployment Checklist

Use this checklist before deploying to Kubernetes to ensure everything is properly configured.

## Infrastructure Setup

### External PostgreSQL
- [ ] PostgreSQL 16 installed on dedicated host
- [ ] Database `django` created
- [ ] User `postgres` created with strong password
- [ ] All privileges granted to user
- [ ] `postgresql.conf`: `listen_addresses = '*'` (or specific IPs)
- [ ] `pg_hba.conf`: Kubernetes cluster network has access
- [ ] PostgreSQL service is running
- [ ] Port 5432 is accessible from Kubernetes nodes
- [ ] Firewall allows connections from Kubernetes cluster
- [ ] Test connection from a K8s node: `nc -zv <postgres-host> 5432`

### External Redis
- [ ] Redis 7 installed on dedicated host
- [ ] `redis.conf`: Configured to accept external connections
- [ ] Password set (if using authentication)
- [ ] Redis service is running
- [ ] Port 6379 is accessible from Kubernetes nodes
- [ ] Firewall allows connections from Kubernetes cluster
- [ ] Test connection from a K8s node: `nc -zv <redis-host> 6379`

### Kubernetes Cluster
- [ ] Kubernetes cluster is running (v1.20+)
- [ ] kubectl is installed and configured
- [ ] Access to cluster verified: `kubectl cluster-info`
- [ ] Sufficient resources available (CPU, memory)
- [ ] Storage class available for PersistentVolumes
- [ ] Storage class supports ReadWriteMany (for shared volumes)
- [ ] Ingress controller installed (if using Ingress)
- [ ] cert-manager installed (if using TLS certificates)

## Configuration Files

### Image Registry
- [ ] Docker image built and pushed to registry
- [ ] Registry credentials available (if private)
- [ ] Image tag specified in `k8s/overlays/production/kustomization.yaml`
- [ ] Registry pull secret created (if needed): `./k8s/create-registry-secret.sh`
- [ ] Pull secret referenced in deployments (if using private registry)

### ConfigMap (`k8s/overlays/production/configmap-patch.yaml`)
- [ ] `DB_HOST`: Set to PostgreSQL server IP/hostname
- [ ] `REDIS_HOST`: Set to Redis server IP/hostname
- [ ] `REDIS_URL`: Set to Redis connection URL
- [ ] `ALLOWED_HOSTS`: Includes your domain(s)
- [ ] `CSRF_TRUSTED_ORIGINS`: Includes your domain(s) with protocol
- [ ] `K8S_NAMESPACE`: Set to correct namespace (default: botmother)
- [ ] `PROJECT_ENV`: Set to "prod"
- [ ] `DEBUG`: Set to "False"
- [ ] `PROTOCOL_HTTPS`: Set to "True" (for production)

### Secrets (`k8s/base/secret.yaml` or kubectl create)
- [ ] `DJANGO_SECRET_KEY`: Long, random, secure string (50+ characters)
- [ ] `DB_PASSWORD`: Strong database password
- [ ] `SMS_LOGIN`: SMS service login (if using SMS)
- [ ] `SMS_PASSWORD`: SMS service password (if using SMS)
- [ ] `BOT_TOKEN`: Valid Telegram bot token
- [ ] `TEST_BOT_TOKEN`: Valid test bot token (if needed)
- [ ] `STORAGE_ID`: Storage service ID (if using S3/MinIO)
- [ ] `STORAGE_KEY`: Storage service key (if using S3/MinIO)
- [ ] `STORAGE_URL`: Storage service URL (if using S3/MinIO)
- [ ] `API_URL`: Your application's public URL
- [ ] `CLICK_*`: Payment service credentials (if using Click)
- [ ] `PAYME_*`: Payment service credentials (if using Payme)
- [ ] `DOCKER_USERNAME`: Docker registry username
- [ ] `DOCKER_PASSWORD`: Docker registry password
- [ ] `PRIVATE_KEY`: RSA private key (if needed)
- [ ] `PUBLIC_KEY`: RSA public key (if needed)
- [ ] Secret created in cluster, NOT committed to Git

### Storage (`k8s/base/pvc.yaml`)
- [ ] `storageClassName`: Changed from "standard" to your cluster's storage class
- [ ] Storage sizes appropriate for your needs:
  - [ ] `botmother-media`: Default 10Gi
  - [ ] `botmother-static`: Default 5Gi
  - [ ] `botmother-logs`: Default 5Gi
  - [ ] `botmother-pycache`: Default 1Gi
  - [ ] `botmother-engine`: Default 20Gi

### Resource Limits (`k8s/overlays/production/deployment-patch.yaml`)
- [ ] Web deployment replicas: Set appropriately (default: 2)
- [ ] Web resources: Requests and limits configured
- [ ] Nginx deployment replicas: Set appropriately (default: 2)
- [ ] Nginx resources: Requests and limits configured

### Service Exposure (`k8s/base/service.yaml`)
- [ ] Service type chosen (LoadBalancer, NodePort, or ClusterIP with Ingress)
- [ ] If using NodePort: Port specified (30000-32767)
- [ ] If using LoadBalancer: Cloud provider supports it
- [ ] If using Ingress: Ingress resource created and configured

## Pre-Deployment Tests

### Connectivity Tests
- [ ] Can reach PostgreSQL from K8s: `kubectl run test --image=busybox -it --rm -- nc -zv <db-host> 5432`
- [ ] Can reach Redis from K8s: `kubectl run test --image=busybox -it --rm -- nc -zv <redis-host> 6379`
- [ ] Can pull Docker image: `kubectl run test --image=<your-image> -- echo "test"`

### Validation
- [ ] Kustomize build succeeds: `kubectl kustomize k8s/overlays/production`
- [ ] No syntax errors in YAML files
- [ ] All referenced secrets exist
- [ ] All referenced configmaps exist
- [ ] Storage class exists: `kubectl get storageclass`

## Security Checklist

- [ ] All secrets use strong, random values
- [ ] No default passwords in use
- [ ] Database password is strong and unique
- [ ] Django secret key is long and random
- [ ] Secret files NOT committed to Git (in .gitignore)
- [ ] PostgreSQL requires password authentication
- [ ] Redis uses authentication (if exposed)
- [ ] TLS/HTTPS enabled for production
- [ ] Network policies defined (optional but recommended)
- [ ] RBAC configured appropriately

## Data Migration (if applicable)

- [ ] Database backup created from old system
- [ ] Database imported to new PostgreSQL server
- [ ] Data integrity verified
- [ ] Redis data migrated (if needed)
- [ ] Test database connection with migrated data

## DNS and Networking

- [ ] Domain name points to correct IP (or will be updated)
- [ ] DNS TTL lowered before migration (for quick rollback)
- [ ] LoadBalancer IP obtained (if using LoadBalancer)
- [ ] Ingress configured with correct domain
- [ ] TLS certificates configured (if using HTTPS)
- [ ] Firewall rules allow traffic to K8s cluster

## Monitoring and Logging

- [ ] Plan for viewing logs: `kubectl logs`
- [ ] Log aggregation system (optional, e.g., ELK, Loki)
- [ ] Monitoring system (optional, e.g., Prometheus, Grafana)
- [ ] Alerting configured (optional)
- [ ] Health check endpoints verified

## Deployment

- [ ] Namespace created: `kubectl create namespace botmother`
- [ ] Secrets created: `kubectl create secret ...`
- [ ] Registry credentials created (if needed)
- [ ] Deploy command tested: `kubectl apply -k k8s/overlays/production --dry-run=client`
- [ ] Ready to deploy: `kubectl apply -k k8s/overlays/production`

## Post-Deployment

- [ ] All pods running: `kubectl get pods -n botmother`
- [ ] No errors in pod logs: `kubectl logs -n botmother <pod-name>`
- [ ] Health checks passing
- [ ] Database migrations run: `kubectl exec ... -- python manage.py migrate`
- [ ] Superuser created: `kubectl exec ... -- python manage.py createsuperuser`
- [ ] Static files collected (if needed)
- [ ] Application accessible via service IP
- [ ] All API endpoints responding correctly
- [ ] Admin panel accessible and working
- [ ] Test key functionality

## Rollback Plan

- [ ] Previous deployment still available (if migrating)
- [ ] Database backup taken before migration
- [ ] Rollback procedure documented
- [ ] DNS can be quickly switched back (if needed)
- [ ] Team knows how to rollback: `kubectl rollout undo ...`

## Documentation

- [ ] Deployment process documented
- [ ] Environment-specific settings documented
- [ ] Access credentials stored securely (password manager)
- [ ] Team members have access to documentation
- [ ] Emergency contacts listed

## Final Checks

- [ ] Dry run successful: `kubectl apply -k k8s/overlays/production --dry-run=client`
- [ ] Team notified of deployment
- [ ] Deployment window scheduled (low traffic time)
- [ ] Rollback plan reviewed
- [ ] On-call support available during deployment

---

## Quick Command Reference

```bash
# Validate configuration
kubectl kustomize k8s/overlays/production

# Dry run
kubectl apply -k k8s/overlays/production --dry-run=client

# Deploy
kubectl apply -k k8s/overlays/production

# Check status
kubectl get all -n botmother

# View logs
kubectl logs -n botmother -l component=web --tail=100

# Run migrations
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py migrate

# Rollback
kubectl rollout undo deployment/botmother-web -n botmother
```

## Support

If issues occur:
1. Check logs: `kubectl logs -n botmother <pod-name>`
2. Check events: `kubectl get events -n botmother --sort-by='.lastTimestamp'`
3. Check pod status: `kubectl describe pod -n botmother <pod-name>`
4. Review this checklist for missed steps
5. Consult the troubleshooting section in `k8s/README.md`
