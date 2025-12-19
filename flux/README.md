# Flux GitOps Deployment

Bu loyiha Flux v2 orqali GitOps yondashuvi bilan deploy qilinadi.

## Flux nima?

Flux - bu Kubernetes uchun GitOps operatori. U Git repositoriydagi o'zgarishlarni avtomatik ravishda Kubernetes klasteriga sync qiladi.

**Afzalliklari:**
- CI/CD dan kubeconfig kerak emas
- Git - yagona "source of truth"
- Avtomatik rollback imkoniyati
- Image taglarni avtomatik yangilash

## Serverda Flux o'rnatish

### 1. Flux CLI o'rnatish

```bash
# Linux
curl -s https://fluxcd.io/install.sh | sudo bash

# yoki Homebrew bilan
brew install fluxcd/tap/flux
```

### 2. Flux komponenetlarini klasterga o'rnatish

```bash
# GitHub token yarating (repo va admin:repo_hook scopelari bilan)
export GITHUB_TOKEN=<your-token>
export GITHUB_USER=BotMather
export GITHUB_REPO=backend

# Flux bootstrap
flux bootstrap github \
  --owner=$GITHUB_USER \
  --repository=$GITHUB_REPO \
  --branch=main \
  --path=./flux/clusters/production \
  --personal
```

### 3. Image Registry Secret yaratish (agar private registry bo'lsa)

```bash
kubectl create secret docker-registry regcred \
  --namespace=botmother \
  --docker-server=registry.jscorp.uz \
  --docker-username=<username> \
  --docker-password=<password>
```

### 4. Flux komponentalarini tekshirish

```bash
# Flux holati
flux check

# Source va Kustomization holatini ko'rish
flux get sources git
flux get kustomizations

# Image automation holatini ko'rish
flux get image repository
flux get image policy
flux get image update
```

## Deployment jarayoni

1. **Developer** kod o'zgartiradi va push qiladi
2. **GitHub Actions** Docker image build qiladi va registry ga push qiladi
3. **Flux Image Automation** yangi image tag ni aniqlaydi
4. **Flux** avtomatik ravishda `k8s/kustomization.yaml` dagi image tag ni yangilaydi
5. **Flux Kustomize Controller** o'zgarishlarni Kubernetes ga apply qiladi

## Manual sync (agar kerak bo'lsa)

```bash
# Barcha resurslarni sync qilish
flux reconcile source git flux-system

# Kustomization ni sync qilish
flux reconcile kustomization botmother
```

## Troubleshooting

```bash
# Flux loglarini ko'rish
kubectl logs -n flux-system deployment/source-controller
kubectl logs -n flux-system deployment/kustomize-controller
kubectl logs -n flux-system deployment/image-automation-controller

# Event larni ko'rish
kubectl get events -n flux-system --sort-by='.lastTimestamp'

# Kustomization statusini ko'rish
kubectl describe kustomization botmother -n flux-system
```

## Muhim fayllar

- `flux/clusters/production/` - Production klaster konfiguratsiyasi
- `flux/clusters/production/gotk-components.yaml` - Flux komponentalari (bootstrap orqali yaratiladi)
- `flux/clusters/production/gotk-sync.yaml` - Git repository sync (bootstrap orqali yaratiladi)
- `flux/apps/botmother.yaml` - Botmother ilovasi Kustomization
- `flux/apps/image-automation.yaml` - Image avtomatik yangilash

## Kubernetes Events Watcher

Kubernetes eventlarini kuzatish uchun alohida command mavjud:

```bash
# Pod eventlarni kuzatish (barcha node lardan)
python manage.py watch_k8s_events

# Verbose mode bilan
python manage.py watch_k8s_events --verbose

# Ma'lum namespace bilan
python manage.py watch_k8s_events --namespace=botmother
```

**Muhim:** Kubernetes API barcha node lardagi pod eventlarni avtomatik ravishda yig'adi, shuning uchun bitta watcher yetarli.
