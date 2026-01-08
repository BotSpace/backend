# Kubernetes Deployment Guide for Encrypted Flow API

## Overview

Bu qo'llanma Flow encryption keylarni Kubernetes secrets orqali deployment qilish uchun.

## 1. Kubernetes Secret yaratish

### Usul 1: File dan Secret yaratish (tavsiya etiladi)

```bash
# Private va public keylarni Kubernetes secret sifatida yarating
kubectl create secret generic flow-keys \
  --from-file=private.pem=keys/private.pem \
  --from-file=public.pem=keys/public.pem \
  -n botmother
```

### Usul 2: YAML file orqali

```bash
# PEM fayllarni base64 ga encode qiling
PRIVATE_KEY_BASE64=$(cat keys/private.pem | base64 -w 0)
PUBLIC_KEY_BASE64=$(cat keys/public.pem | base64 -w 0)

# Secret YAML yarating
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Secret
metadata:
  name: flow-keys
  namespace: botmother
type: Opaque
data:
  private.pem: ${PRIVATE_KEY_BASE64}
  public.pem: ${PUBLIC_KEY_BASE64}
EOF
```

## 2. Deployment da Secret ishlatish

Deployment YAML faylingizga quyidagi environment variablelarni qo'shing:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: backend
  namespace: botmother
spec:
  template:
    spec:
      containers:
      - name: backend
        image: your-backend-image:latest
        env:
        # Flow encryption keys from Kubernetes secret
        - name: FLOW_PRIVATE_KEY
          valueFrom:
            secretKeyRef:
              name: flow-keys
              key: private.pem
        - name: FLOW_PUBLIC_KEY
          valueFrom:
            secretKeyRef:
              name: flow-keys
              key: public.pem
        # ... boshqa environment variablelar
```

## 3. Secret tekshirish

```bash
# Secret mavjudligini tekshirish
kubectl get secret flow-keys -n botmother

# Secret ma'lumotlarini ko'rish (debug uchun)
kubectl describe secret flow-keys -n botmother

# Secret ichidagi keylarni ko'rish
kubectl get secret flow-keys -n botmother -o jsonpath='{.data}'
```

## 4. Key rotation (yangilash)

Keylarni yangilash kerak bo'lsa:

```bash
# Eski secretni o'chirish
kubectl delete secret flow-keys -n botmother

# Yangi keylar bilan secret yaratish
kubectl create secret generic flow-keys \
  --from-file=private.pem=keys/new_private.pem \
  --from-file=public.pem=keys/new_public.pem \
  -n botmother

# Podlarni restart qilish (yangi keylarni olish uchun)
kubectl rollout restart deployment/backend -n botmother
```

## 5. Xavfsizlik

### ⚠️ Muhim xavfsizlik qoidalari:

1. **Private keyni hech qachon Git ga commit qilmang**
   ```bash
   # .gitignore faylga qo'shing
   keys/private.pem
   keys/*.pem
   ```

2. **Secretga faqat zarur podlar kirishi mumkin**
   ```yaml
   # RBAC ni sozlang
   apiVersion: rbac.authorization.k8s.io/v1
   kind: Role
   metadata:
     name: secret-reader
     namespace: botmother
   rules:
   - apiGroups: [""]
     resources: ["secrets"]
     resourceNames: ["flow-keys"]
     verbs: ["get"]
   ```

3. **Production da kuchli keylar ishlating**
   ```bash
   # 4096-bit RSA key yaratish (tavsiya etiladi)
   openssl genrsa -out keys/private.pem 4096
   openssl rsa -in keys/private.pem -pubout -out keys/public.pem
   ```

4. **Secretni encrypt qiling (agar cluster encrypt qilmagan bo'lsa)**
   - Sealed Secrets ishlatish
   - External Secrets Operator ishlatish
   - Cloud provider secrets (AWS Secrets Manager, Azure Key Vault, etc.)

## 6. Troubleshooting

### Pod keylarni yuklay olmayapti?

```bash
# Pod loglarini tekshiring
kubectl logs -f deployment/backend -n botmother

# Pod environment variablelarini tekshiring
kubectl exec -it deployment/backend -n botmother -- env | grep FLOW
```

### Secret noto'g'ri formatda?

```bash
# Secret ichidagi keyni dekod qiling va tekshiring
kubectl get secret flow-keys -n botmother -o jsonpath='{.data.private\.pem}' | base64 -d | head -1

# -----BEGIN PRIVATE KEY----- ko'rinishi kerak
```

### Pod restart bo'lganda keylar yo'qolmoqda?

Secretlar har doim pod restart bo'lganda qayta yuklanadi. Agar muammo bo'lsa:
- Secret to'g'ri namespace da ekanligini tekshiring
- RBAC permissions to'g'ri sozlanganligini tekshiring

## 7. Local development

Local developmentda file path ishlatishingiz mumkin:

```bash
# .env faylda
FLOW_PRIVATE_KEY=/path/to/keys/private.pem
FLOW_PUBLIC_KEY=/path/to/keys/public.pem
```

Yoki PEM contentni to'g'ridan-to'g'ri:

```bash
# .env faylda (multiline)
FLOW_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----
MIIEvQIBADANBgkqhkiG9w0BAQE...
-----END PRIVATE KEY-----"
```

## 8. Monitoring

Backend logs orqali key loading statusini kuzating:

```bash
# Backend start bo'lganda log tekshiring
kubectl logs -f deployment/backend -n botmother | grep -i "key\|encrypt"
```

## Qo'shimcha ma'lumot

- Backend avtomatik ravishda environment variableni PEM content yoki file path ekanligini aniqlaydi
- `-----BEGIN` bilan boshlansa - PEM content deb hisoblanadi
- Aks holda - file path deb hisoblanadi
- Hech narsa o'rnatilmasa - default `keys/private.pem` va `keys/public.pem` ishlatiladi
