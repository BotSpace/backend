# Kubernetes Deployment - Quick Start (O'zbek)

Bu qo'llanma BotMother backend dasturini Kubernetes'ga deploy qilish bo'yicha tez yo'riqnoma.

## Talablar

1. **Kubernetes Cluster** - ishlaydigan K8s cluster
2. **kubectl** - o'rnatilgan va sozlangan
3. **Tashqi PostgreSQL** - alohida hostda o'rnatilgan
4. **Tashqi Redis** - alohida hostda o'rnatilgan

## Tez Sozlash

### 1. Tashqi PostgreSQL va Redis ni Sozlang

#### PostgreSQL
```bash
# PostgreSQL serverida database yarating
psql -U postgres
CREATE DATABASE django;
CREATE USER postgres WITH PASSWORD 'kuchli-parol';
GRANT ALL PRIVILEGES ON DATABASE django TO postgres;
\q

# postgresql.conf faylida:
listen_addresses = '*'

# pg_hba.conf faylida K8s cluster uchun ruxsat bering:
host    all             all             10.0.0.0/8              md5
```

#### Redis
```bash
# redis.conf faylida:
bind 0.0.0.0
# yoki maxfiy parol o'rnating:
requirepass kuchli-parol
```

### 2. Konfiguratsiyani Yangilang

**`k8s/overlays/production/configmap-patch.yaml`** faylini tahrirlang:
```yaml
DB_HOST: "sizning-postgres-ip"        # O'zgartiring!
REDIS_HOST: "sizning-redis-ip"        # O'zgartiring!
REDIS_URL: "redis://sizning-redis-ip:6379"
ALLOWED_HOSTS: "web,botmother-web,sizning-domen.com"
```

**Maxfiy ma'lumotlarni sozlang:**
```bash
# Secret yarating (faylda saqlamaslik uchun)
kubectl create secret generic botmother-secret \
  --namespace=botmother \
  --from-literal=DJANGO_SECRET_KEY='uzun-tasodifiy-kalit' \
  --from-literal=DB_PASSWORD='postgresql-parol' \
  --from-literal=BOT_TOKEN='telegram-bot-token'
```

### 3. Image Tag ni Yangilang

**`k8s/overlays/production/kustomization.yaml`** faylida:
```yaml
images:
  - name: registry.jscorp.uz/botmother
    newTag: "latest"  # yoki versiya raqami
```

### 4. Deploy Qiling

```bash
# Barcha o'zgarishlarni ko'rib chiqing
kubectl apply -k k8s/overlays/production --dry-run=client

# Deploy qiling
kubectl apply -k k8s/overlays/production

# Statusni kuzating
kubectl get pods -n botmother -w
```

### 5. Database Migratsiya

```bash
# Migratsiyalarni ishga tushiring
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py migrate

# Superuser yarating
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py createsuperuser
```

### 6. Dasturga Kirish

```bash
# Service IP ni oling
kubectl get svc -n botmother botmother-nginx

# LoadBalancer IP orqali kirish:
curl http://<EXTERNAL-IP>/health/
```

## Deploy Script Yordamida

```bash
# Deploy skriptini ishga tushiring
cd k8s
./deploy.sh

# Menyu ko'rinadi:
# 1. Deploy qilish
# 2. Yangilash
# 3. Status ko'rish
# 4. Loglarni ko'rish
# 5. Migratsiya
# 6. Superuser yaratish
# va boshqalar...
```

## Monitoring

```bash
# Pod statusini ko'rish
kubectl get pods -n botmother

# Loglarni ko'rish
kubectl logs -n botmother -l component=web --tail=100
kubectl logs -n botmother -l component=nginx --tail=100

# Resource ishlatilishini ko'rish
kubectl top pods -n botmother
```

## Muammolarni Hal Qilish

### Podlar ishga tushmayapti
```bash
kubectl describe pod -n botmother <pod-nomi>
kubectl logs -n botmother <pod-nomi>
```

### Database bilan bog'lanish muammosi
```bash
# Pod ichidan test qiling
kubectl exec -n botmother -it deployment/botmother-web -- sh
nc -zv <db-host> 5432
```

### Redis bilan bog'lanish muammosi
```bash
kubectl exec -n botmother -it deployment/botmother-web -- sh
nc -zv <redis-host> 6379
```

## Scaling

```bash
# Replikalarni ko'paytirish
kubectl scale deployment botmother-web --replicas=3 -n botmother
```

## Rollback

```bash
# Oldingi versiyaga qaytish
kubectl rollout undo deployment/botmother-web -n botmother

# History ko'rish
kubectl rollout history deployment/botmother-web -n botmother
```

## Yangilash

```bash
# Yangi image bilan yangilash
kubectl set image deployment/botmother-web web=registry.jscorp.uz/botmother:v1.0.1 -n botmother

# yoki kustomize orqali
# kustomization.yaml da newTag ni o'zgartiring va:
kubectl apply -k k8s/overlays/production
```

## Muhim Eslatmalar

⚠️ **Xavfsizlik:**
- Hamma maxfiy ma'lumotlarni production'da o'zgartiring
- Secret fayllarni git'ga commit qilmang
- HTTPS ni yoqing production'da
- PostgreSQL va Redis uchun kuchli parollar ishlating

📋 **Production Checklist:**
- [ ] PostgreSQL o'rnatilgan va sozlangan
- [ ] Redis o'rnatilgan va sozlangan
- [ ] ConfigMap'da to'g'ri IP manzillar
- [ ] Secret'lar yaratilgan va to'ldirilgan
- [ ] Image tag to'g'ri ko'rsatilgan
- [ ] StorageClass mavjud va sozlangan
- [ ] Migratsiyalar ishga tushirilgan
- [ ] Health check ishlayapti

## Batafsil Ma'lumot

Batafsil qo'llanma uchun `k8s/README.md` faylini o'qing.
