# Kubernetes Deployment Documentation Index

Welcome to the Kubernetes deployment documentation for BotMather backend.

## Quick Navigation

### 🚀 Getting Started
- **[QUICK-START.md](QUICK-START.md)** - Quick deployment guide (O'zbek/Uzbek language)
- **[SUMMARY.md](SUMMARY.md)** - Overview of what was done and key changes

### 📚 Comprehensive Guides
- **[README.md](README.md)** - Complete deployment guide with detailed instructions
- **[MIGRATION.md](MIGRATION.md)** - Step-by-step migration from Docker Swarm
- **[COMPARISON.md](COMPARISON.md)** - Docker Swarm vs Kubernetes comparison

### ✅ Preparation
- **[CHECKLIST.md](CHECKLIST.md)** - Pre-deployment checklist

### 🛠️ Tools & Scripts
- **[deploy.sh](deploy.sh)** - Interactive deployment helper script
- **[create-registry-secret.sh](create-registry-secret.sh)** - Registry credentials setup
- **[validate.sh](validate.sh)** - Pre-deployment validation script

### 📁 Manifests
- **[base/](base/)** - Base Kubernetes manifests
  - `namespace.yaml` - Namespace definition
  - `configmap.yaml` - Environment variables
  - `secret.yaml` - Sensitive configuration template
  - `pvc.yaml` - Persistent Volume Claims
  - `deployment-web.yaml` - Web service deployment
  - `deployment-nginx.yaml` - Nginx deployment
  - `service.yaml` - Service definitions
  - `kustomization.yaml` - Base kustomization
  - `ingress.yaml.example` - Optional Ingress example

- **[overlays/production/](overlays/production/)** - Production overrides
  - `configmap-patch.yaml` - Production configuration
  - `deployment-patch.yaml` - Production resource limits
  - `kustomization.yaml` - Production kustomization

## Documentation Map

```
┌─────────────────────────────────────────────────────┐
│  First Time? Start Here                             │
├─────────────────────────────────────────────────────┤
│  1. QUICK-START.md (O'zbek) or README.md (English) │
│  2. CHECKLIST.md - Check prerequisites              │
│  3. Run validate.sh to verify setup                 │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Migrating from Docker Swarm?                       │
├─────────────────────────────────────────────────────┤
│  1. COMPARISON.md - Understand differences          │
│  2. MIGRATION.md - Follow migration steps           │
│  3. CHECKLIST.md - Verify prerequisites             │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│  Need Help?                                         │
├─────────────────────────────────────────────────────┤
│  → README.md - Troubleshooting section              │
│  → COMPARISON.md - Feature comparison               │
│  → Use deploy.sh for interactive operations         │
└─────────────────────────────────────────────────────┘
```

## Common Tasks

### Initial Deployment
```bash
# 1. Validate prerequisites
./k8s/validate.sh

# 2. Update configuration
vim k8s/overlays/production/configmap-patch.yaml

# 3. Create secrets
kubectl create secret generic botmother-secret \
  --namespace=botmother \
  --from-literal=DJANGO_SECRET_KEY='...'

# 4. Deploy
kubectl apply -k k8s/overlays/production

# 5. Run migrations
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py migrate
```

### Using Helper Script
```bash
cd k8s
./deploy.sh
# Select from menu: deploy, update, logs, migrations, etc.
```

### Monitoring
```bash
# Check status
kubectl get all -n botmother

# View logs
kubectl logs -n botmother -l component=web --tail=100 -f

# Check events
kubectl get events -n botmother --sort-by='.lastTimestamp'
```

### Updates
```bash
# Update image
kubectl set image deployment/botmother-web \
  web=registry.jscorp.uz/botmother:v1.0.1 -n botmother

# Or use interactive script
./k8s/deploy.sh  # Select option 2
```

## File Size Reference

| File | Lines | Purpose |
|------|-------|---------|
| README.md | ~400 | Complete deployment guide |
| MIGRATION.md | ~460 | Migration from Docker Swarm |
| QUICK-START.md | ~200 | Quick start (Uzbek) |
| COMPARISON.md | ~310 | Swarm vs K8s comparison |
| CHECKLIST.md | ~350 | Pre-deployment checklist |
| SUMMARY.md | ~280 | Project summary |
| deploy.sh | ~150 | Deployment helper |
| validate.sh | ~200 | Validation script |
| create-registry-secret.sh | ~60 | Registry setup |

## Architecture Overview

```
┌──────────────────────────────────────────────────────┐
│              External Infrastructure                  │
├──────────────────────────────────────────────────────┤
│  PostgreSQL Host          Redis Host                 │
│  - Port: 5432            - Port: 6379                │
│  - Database: django      - Auth: optional            │
└──────────────────────────────────────────────────────┘
                          ↓
┌──────────────────────────────────────────────────────┐
│           Kubernetes Cluster (botmother)             │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────┐      ┌─────────────┐               │
│  │ Web (x2)    │      │ Nginx (x2)  │               │
│  │ Django      │←────→│ Reverse     │               │
│  │ App         │      │ Proxy       │               │
│  └─────────────┘      └─────────────┘               │
│        ↓                     ↓                       │
│  ┌─────────────────────────────────┐                │
│  │    Persistent Volumes (PVCs)    │                │
│  │  - media, static, logs, engine  │                │
│  └─────────────────────────────────┘                │
│                                                       │
│  ConfigMap: botmother-config                         │
│  Secret: botmother-secret                            │
└──────────────────────────────────────────────────────┘
```

## Support & Troubleshooting

### Common Issues

1. **Pods not starting** → Check `kubectl describe pod -n botmother <pod-name>`
2. **Database connection failed** → Verify DB_HOST in configmap-patch.yaml
3. **Redis connection failed** → Verify REDIS_HOST in configmap-patch.yaml
4. **Image pull failed** → Create registry credentials with create-registry-secret.sh
5. **Storage issues** → Check storage class with `kubectl get storageclass`

### Getting Help

1. Review the troubleshooting section in [README.md](README.md)
2. Check pod logs: `kubectl logs -n botmother <pod-name>`
3. Check events: `kubectl get events -n botmother --sort-by='.lastTimestamp'`
4. Run validation: `./k8s/validate.sh`

## Version Information

- **Kubernetes**: v1.20+ required
- **PostgreSQL**: v16 recommended
- **Redis**: v7 recommended
- **Storage**: ReadWriteMany support recommended

## Security Notes

⚠️ **Important Security Considerations:**

1. Never commit secrets to Git
2. Replace all placeholders in production
3. Use strong passwords for DB/Redis
4. Enable HTTPS in production
5. Review Docker socket security warning in README.md
6. Consider network policies for isolation
7. Use RBAC for access control

## Quick Links

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [Kustomize Documentation](https://kustomize.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Redis Documentation](https://redis.io/documentation)

## Contributing

To improve this documentation:
1. Make changes to the relevant files
2. Test your changes
3. Submit a pull request

---

**Last Updated**: 2025-12-22  
**Status**: ✅ Complete and ready for deployment

For the main project README, see [../README.MD](../README.MD)
