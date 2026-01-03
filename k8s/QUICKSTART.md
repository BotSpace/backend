# Quick Start Guide - Kubernetes Deployment

Bu qo'llanma backend ilovasini Kubernetes da node-local Redis bilan deploy qilishni ko'rsatadi.

## Muhim: Node-local Redis nima?

Har bir Kubernetes node da bitta Redis instance ishga tushadi (DaemonSet).
API deployment qaysi node da ishga tushsa, shu node dagi Redis ga ulanadi.

Bu qanday ishlaydi:
1. Redis DaemonSet har bir node da ishga tushadi
2. API pod o'zining node IP sini oladi (Kubernetes Downward API orqali)
3. Redis URL `redis://NODE_IP:6379` ko'rinishida bo'ladi
4. Shu orqali har bir API pod o'z node dagi Redis ga ulanadi

## Tez Deploy qilish

```bash
cd k8s

# 1. Secrets faylini tayyorlang
cp api-secrets.yaml.example api-secrets.yaml
# api-secrets.yaml ni tahrirlang va haqiqiy qiymatlarni kiriting

# 2. Deploy skriptini ishga tushiring
./deploy.sh
```

## Yoki qo'lda deploy qilish

```bash
# Namespace yaratish
kubectl apply -f namespace.yaml

# Secrets va ConfigMap
kubectl apply -f api-secrets.yaml
kubectl apply -f api-configmap.yaml

# Storage
kubectl apply -f pvcs.yaml

# Redis DaemonSet
kubectl apply -f redis-daemonset.yaml

# API deployment
kubectl apply -f api-deployment.yaml
kubectl apply -f api-service.yaml
```

## Tekshirish

```bash
# Barcha resurslarni ko'rish
kubectl get all -n botmother

# Redis podlarni har bir node da ko'rish
kubectl get pods -n botmother -l app=redis -o wide

# API podning node IP va Redis URL ni ko'rish
kubectl exec -n botmother deployment/api -- env | grep -E 'NODE_IP|REDIS'

# Redis bilan aloqani tekshirish
API_POD=$(kubectl get pod -n botmother -l app=api -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n botmother $API_POD -- sh -c 'echo PING | nc -w 2 $NODE_IP 6379'
```

## Loglarni ko'rish

```bash
# API logs
kubectl logs -n botmother -l app=api -f

# Redis logs
kubectl logs -n botmother -l app=redis -f
```

## Scale qilish

```bash
# API ni scale qilish
kubectl scale deployment api -n botmother --replicas=3

# Har bir pod o'z node dagi Redis ga ulanadi
```

## Muammolarni hal qilish

### API Redis ga ulana olmayapti

```bash
# 1. Redis ishga tushganini tekshiring
kubectl get pods -n botmother -l app=redis -o wide

# 2. NODE_IP to'g'ri o'rnatilganini tekshiring
kubectl exec -n botmother deployment/api -- printenv NODE_IP

# 3. Port ochiqligini tekshiring
kubectl exec -n botmother deployment/api -- nc -zv $NODE_IP 6379
```

### Redis pod ishga tushmayapti

```bash
# DaemonSet eventlarini ko'rish
kubectl describe daemonset redis -n botmother

# Node holatini tekshirish
kubectl get nodes
kubectl describe node <node-name>
```

## O'chirish

```bash
# Barcha resurslarni o'chirish
kubectl delete namespace botmother
```

## Batafsil ma'lumot

README.md faylida to'liq documentation mavjud.
