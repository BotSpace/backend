# Flux GitOps Deployment

This project is deployed using Flux v2 GitOps approach.

## What is Flux?

Flux is a GitOps operator for Kubernetes. It automatically syncs changes from the Git repository to the Kubernetes cluster.

**Benefits:**
- No kubeconfig needed in CI/CD
- Git is the single "source of truth"
- Automatic rollback capability
- Automatic image tag updates

## Installing Flux on Server

### 1. Install Flux CLI

```bash
# Linux
curl -s https://fluxcd.io/install.sh | sudo bash

# or with Homebrew
brew install fluxcd/tap/flux
```

### 2. Install Flux Components to Cluster

```bash
# Create a GitHub token (with repo and admin:repo_hook scopes)
export GITHUB_TOKEN=<your-token>
export GITHUB_USER=BotMather
export GITHUB_REPO=backend

# Bootstrap Flux
flux bootstrap github \
  --owner=$GITHUB_USER \
  --repository=$GITHUB_REPO \
  --branch=main \
  --path=./flux/clusters/production \
  --personal
```

### 3. Create Image Registry Secret (if using private registry)

```bash
kubectl create secret docker-registry regcred \
  --namespace=botmother \
  --docker-server=registry.jscorp.uz \
  --docker-username=<username> \
  --docker-password=<password>
```

### 4. Verify Flux Components

```bash
# Check Flux status
flux check

# View Source and Kustomization status
flux get sources git
flux get kustomizations

# View image automation status
flux get image repository
flux get image policy
flux get image update
```

## Deployment Flow

1. **Developer** changes code and pushes to GitHub
2. **GitHub Actions** builds Docker image and pushes to registry
3. **Flux Image Automation** detects the new image tag
4. **Flux** automatically updates the image tag in `k8s/kustomization.yaml`
5. **Flux Kustomize Controller** applies changes to Kubernetes

## Manual Sync (if needed)

```bash
# Sync all resources
flux reconcile source git flux-system

# Sync Kustomization
flux reconcile kustomization botmother
```

## Troubleshooting

```bash
# View Flux logs
kubectl logs -n flux-system deployment/source-controller
kubectl logs -n flux-system deployment/kustomize-controller
kubectl logs -n flux-system deployment/image-automation-controller

# View events
kubectl get events -n flux-system --sort-by='.lastTimestamp'

# View Kustomization status
kubectl describe kustomization botmother -n flux-system
```

## Important Files

- `flux/clusters/production/` - Production cluster configuration
- `flux/clusters/production/gotk-components.yaml` - Flux components (created via bootstrap)
- `flux/clusters/production/gotk-sync.yaml` - Git repository sync (created via bootstrap)
- `flux/apps/botmother.yaml` - BotMother application Kustomization
- `flux/apps/image-automation.yaml` - Image automatic update configuration

## Kubernetes Events Watcher

A dedicated command exists to watch Kubernetes events:

```bash
# Watch pod events (from all nodes)
python manage.py watch_k8s_events

# With verbose mode
python manage.py watch_k8s_events --verbose

# With specific namespace
python manage.py watch_k8s_events --namespace=botmother
```

**Important:** The Kubernetes API automatically aggregates pod events from all nodes, so a single watcher is sufficient.
