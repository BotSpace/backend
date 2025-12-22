# Migration Guide: Docker Swarm to Kubernetes

This guide helps you migrate your BotMother backend from Docker Swarm to Kubernetes with external PostgreSQL and Redis.

## Overview

**Current Setup (Docker Swarm):**
- All services in one stack (stack.yaml)
- PostgreSQL and Redis running in Docker containers
- Deployed via `docker stack deploy`

**New Setup (Kubernetes):**
- Application running in K8s cluster
- PostgreSQL on external dedicated host
- Redis on external dedicated host
- Deployed via `kubectl` with Kustomize

## Pre-Migration Checklist

- [ ] Kubernetes cluster is set up and accessible
- [ ] kubectl is installed and configured
- [ ] Separate hosts prepared for PostgreSQL and Redis
- [ ] Backup of current PostgreSQL database
- [ ] Backup of current Redis data (if needed)
- [ ] Access to Docker registry for application images

## Migration Steps

### Phase 1: Setup External Services

#### 1.1 Setup External PostgreSQL

```bash
# On the new PostgreSQL host
# Install PostgreSQL 16
sudo apt update
sudo apt install -y postgresql-16

# Configure PostgreSQL
sudo -u postgres psql
CREATE DATABASE django;
CREATE USER postgres WITH PASSWORD 'your-strong-password';
GRANT ALL PRIVILEGES ON DATABASE django TO postgres;
ALTER DATABASE django OWNER TO postgres;
\q

# Configure remote access
sudo nano /etc/postgresql/16/main/postgresql.conf
# Set: listen_addresses = '*'

sudo nano /etc/postgresql/16/main/pg_hba.conf
# Add: host all all 0.0.0.0/0 md5  # Or restrict to K8s cluster subnet

sudo systemctl restart postgresql
```

#### 1.2 Setup External Redis

```bash
# On the new Redis host
# Install Redis
sudo apt update
sudo apt install -y redis-server

# Configure Redis for remote access
sudo nano /etc/redis/redis.conf
# Change: bind 127.0.0.1 ::1
# To: bind 0.0.0.0

# Optional: Set password
# requirepass your-strong-password

sudo systemctl restart redis-server

# Verify Redis is listening
sudo netstat -tlnp | grep 6379
```

#### 1.3 Migrate Database

```bash
# On current Swarm deployment
# Export data from existing PostgreSQL
docker exec <postgres-container-id> pg_dump -U postgres django > backup.sql

# Copy backup to new PostgreSQL host
scp backup.sql user@new-postgres-host:/tmp/

# On new PostgreSQL host
# Import data
psql -U postgres -d django < /tmp/backup.sql

# Verify data
psql -U postgres -d django
\dt  # List tables
SELECT COUNT(*) FROM <some_table>;
\q
```

#### 1.4 Migrate Redis Data (Optional)

```bash
# If you need to preserve Redis data:

# On current Swarm deployment
docker exec <redis-container-id> redis-cli SAVE
docker cp <redis-container-id>:/data/dump.rdb ./redis-backup.rdb

# Copy to new Redis host
scp redis-backup.rdb user@new-redis-host:/tmp/

# On new Redis host
sudo systemctl stop redis-server
sudo cp /tmp/redis-backup.rdb /var/lib/redis/dump.rdb
sudo chown redis:redis /var/lib/redis/dump.rdb
sudo systemctl start redis-server
```

### Phase 2: Configure Kubernetes Deployment

#### 2.1 Update Configuration Files

```bash
# Clone the repository on your workstation
git clone <repository-url>
cd backend

# Edit k8s/overlays/production/configmap-patch.yaml
# Update with actual IPs/hostnames:
DB_HOST: "10.x.x.x"  # PostgreSQL host IP
REDIS_HOST: "10.x.x.x"  # Redis host IP
REDIS_URL: "redis://10.x.x.x:6379"
ALLOWED_HOSTS: "your-domain.com,www.your-domain.com"
CSRF_TRUSTED_ORIGINS: "https://your-domain.com"
```

#### 2.2 Create Kubernetes Secrets

```bash
# Do NOT store secrets in Git!
# Create secrets directly in cluster:

kubectl create namespace botmother

kubectl create secret generic botmother-secret \
  --namespace=botmother \
  --from-literal=DJANGO_SECRET_KEY='your-long-random-secret-key-here' \
  --from-literal=DB_PASSWORD='your-postgresql-password' \
  --from-literal=SMS_LOGIN='your-sms-login' \
  --from-literal=SMS_PASSWORD='your-sms-password' \
  --from-literal=BOT_TOKEN='your-telegram-bot-token' \
  --from-literal=TEST_BOT_TOKEN='your-test-bot-token' \
  --from-literal=STORAGE_ID='your-storage-id' \
  --from-literal=STORAGE_KEY='your-storage-key' \
  --from-literal=STORAGE_URL='your-storage-url' \
  --from-literal=STORAGE_BUCKET_MEDIA='your-media-bucket' \
  --from-literal=STORAGE_BUCKET_STATIC='your-static-bucket' \
  --from-literal=API_URL='https://your-domain.com' \
  --from-literal=CLICK_SERVICE_ID='your-click-service-id' \
  --from-literal=CLICK_MERCHANT_ID='your-click-merchant-id' \
  --from-literal=CLICK_SECRET_KEY='your-click-secret-key' \
  --from-literal=PAYTECH_API_KEY='your-paytech-key' \
  --from-literal=PAYME_ID='your-payme-id' \
  --from-literal=PAYME_KEY='your-payme-key' \
  --from-literal=DOCKER_USERNAME='your-docker-username' \
  --from-literal=DOCKER_PASSWORD='your-docker-password' \
  --from-literal=DOCKER_REGISTRY='registry.jscorp.uz' \
  --from-literal=MONGO_URL='your-mongo-url-if-needed'

# If using RSA keys
kubectl create secret generic botmother-rsa-keys \
  --namespace=botmother \
  --from-file=PRIVATE_KEY=./keys/private.pem \
  --from-file=PUBLIC_KEY=./keys/public.pem
```

#### 2.3 Configure Storage Class

```bash
# Check available storage classes
kubectl get storageclass

# Update k8s/base/pvc.yaml with your storage class
# Replace 'standard' with your actual storage class name
```

### Phase 3: Deploy to Kubernetes

#### 3.1 Test Connectivity

```bash
# From your workstation, test connectivity to external services
nc -zv <postgres-host> 5432
nc -zv <redis-host> 6379

# Or from a test pod in K8s
kubectl run test-pod --image=busybox -it --rm -- sh
nc -zv <postgres-host> 5432
nc -zv <redis-host> 6379
```

#### 3.2 Deploy Application

```bash
# Dry run first to check for errors
kubectl apply -k k8s/overlays/production --dry-run=client

# Apply the deployment
kubectl apply -k k8s/overlays/production

# Watch the deployment
kubectl get pods -n botmother -w
```

#### 3.3 Verify Deployment

```bash
# Check all resources
kubectl get all -n botmother

# Check pod logs
kubectl logs -n botmother -l component=web --tail=100
kubectl logs -n botmother -l component=nginx --tail=100

# Check for errors
kubectl get events -n botmother --sort-by='.lastTimestamp'
```

#### 3.4 Run Migrations

```bash
# Run Django migrations
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py migrate

# Verify database connection
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py check --database default

# Create superuser (if needed)
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py createsuperuser
```

### Phase 4: Testing

#### 4.1 Health Check

```bash
# Get the service IP
kubectl get svc -n botmother botmother-nginx

# Test health endpoint
curl http://<external-ip>/health/

# Or port-forward for testing
kubectl port-forward -n botmother svc/botmother-nginx 8080:80
curl http://localhost:8080/health/
```

#### 4.2 Functional Testing

```bash
# Test admin panel
open http://<external-ip>/admin/

# Test API endpoints
curl http://<external-ip>/api/

# Check logs for any errors
kubectl logs -n botmother -l component=web -f
```

### Phase 5: Switch Traffic

#### 5.1 Update DNS (Gradual Migration)

```bash
# Option 1: Gradual migration with DNS weights
# Update DNS to point to new K8s service
# Use low TTL initially for quick rollback

# Option 2: Blue-Green deployment
# Keep Swarm running, test K8s thoroughly
# Switch DNS when confident

# Option 3: Canary deployment
# Route small percentage to K8s
# Gradually increase traffic
```

#### 5.2 Monitor

```bash
# Monitor pods
kubectl top pods -n botmother

# Watch logs
kubectl logs -n botmother -l component=web -f

# Check for errors
kubectl get events -n botmother --watch
```

### Phase 6: Cleanup Old Deployment

⚠️ **Only after confirming K8s deployment is stable!**

```bash
# On Swarm manager node
# Remove the stack
docker stack rm <stack-name>

# Clean up volumes (after backing up!)
docker volume ls
docker volume rm <volume-name>

# Optional: Leave Swarm mode
docker swarm leave --force
```

## Rollback Plan

If issues occur with K8s deployment:

### Quick Rollback to Swarm

```bash
# On Swarm manager
docker stack deploy -c stack.yaml <stack-name>

# Update DNS to point back to Swarm

# Restore database if needed
psql -U postgres -d django < backup-before-k8s.sql
```

### Rollback in Kubernetes

```bash
# Rollback to previous version
kubectl rollout undo deployment/botmother-web -n botmother

# Or to specific revision
kubectl rollout history deployment/botmother-web -n botmother
kubectl rollout undo deployment/botmother-web --to-revision=2 -n botmother
```

## Post-Migration Tasks

- [ ] Update documentation with new deployment process
- [ ] Update CI/CD pipelines to deploy to K8s instead of Swarm
- [ ] Set up monitoring and alerting for K8s
- [ ] Configure automatic backups for external PostgreSQL
- [ ] Configure automatic backups for PersistentVolumes
- [ ] Set up log aggregation (ELK, Loki, etc.)
- [ ] Review and optimize resource limits
- [ ] Set up auto-scaling if needed
- [ ] Configure network policies for security
- [ ] Review and update disaster recovery procedures

## Troubleshooting

### Pods Not Starting

```bash
kubectl describe pod -n botmother <pod-name>
kubectl logs -n botmother <pod-name>
```

### Database Connection Failed

```bash
# Check connectivity from pod
kubectl exec -n botmother -it deployment/botmother-web -- sh
nc -zv <db-host> 5432

# Check credentials
kubectl get secret botmother-secret -n botmother -o yaml
echo "<base64-password>" | base64 -d

# Check PostgreSQL logs on external host
sudo tail -f /var/log/postgresql/postgresql-16-main.log
```

### Redis Connection Failed

```bash
# Check connectivity
kubectl exec -n botmother -it deployment/botmother-web -- sh
nc -zv <redis-host> 6379

# Check Redis logs
sudo tail -f /var/log/redis/redis-server.log
```

### Storage Issues

```bash
# Check PVC status
kubectl get pvc -n botmother
kubectl describe pvc -n botmother <pvc-name>

# Check PV status
kubectl get pv

# Check storage class
kubectl get storageclass
```

## Best Practices

1. **Always test in staging first** before migrating production
2. **Maintain backups** throughout the migration process
3. **Document changes** for team members
4. **Monitor closely** during and after migration
5. **Keep rollback plan ready** and tested
6. **Migrate during low-traffic period** if possible
7. **Use health checks** to verify service availability
8. **Test all critical functionality** before switching traffic

## Support

For issues during migration:
- Check logs: `kubectl logs -n botmother <pod-name>`
- Check events: `kubectl get events -n botmother`
- Review this guide's troubleshooting section
- Consult Kubernetes documentation

## Summary

This migration moves from a single-node Docker Swarm deployment to a more scalable Kubernetes deployment with externalized databases. The key benefits:

✅ Better scalability and high availability
✅ Separation of stateful services (PostgreSQL, Redis)
✅ Easier horizontal scaling
✅ Better resource management
✅ Industry-standard deployment platform

Remember to test thoroughly and maintain good backups!
