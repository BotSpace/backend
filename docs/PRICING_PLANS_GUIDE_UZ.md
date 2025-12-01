# Botmother Backend - Tarif Tizimi va MongoDB Yangilanishlari

## O'zgarishlar

### 1. MongoDB Arxitekturasi
- Har bir loyiha uchun **alohida MongoDB database** (`project_{id}`)
- Har bir loyiha uchun **alohida MongoDB user** (faqat o'z databasega kirish huquqi bilan)
- Class-based architecture va dependency injection

### 2. Tarif Tizimi (Pricing Plans)
- **4 ta tarif**: FREE, START, PRO, ENTERPRISE
- Foydalanuvchilar soni limitiga qarab
- 3 kunlik grace period
- Avtomatik monitoring va bot to'xtatish

### 3. Docker Konfiguratsiyasi
- MongoDB service qo'shildi (CPU limit: 1 core)
- Bot servislarga MONGO_ADDR va MONGO_DB_NAME beriladi

## Tarif Rejalari

| Tarif | Narx | Foydalanuvchilar | Xususiyatlar |
|-------|------|------------------|--------------|
| FREE | $0 | 100 | Powered by BotMother |
| START | $2 | 5,000 | Branding yo'q |
| PRO | $10 | 100,000 | Custom domain, Priority support |
| ENTERPRISE | Kelishiladi | Cheksiz | Barcha xususiyatlar |

## O'rnatish

### 1. Database migratsiyalari
```bash
docker-compose exec web python manage.py migrate
```

### 2. Tariflarni yaratish
```bash
docker-compose exec web python manage.py create_pricing_plans
```

### 3. Mavjud loyihalarga FREE tarif biriktirish
```bash
docker-compose exec web python manage.py assign_plans_to_projects
```

### 4. MongoDB userlarni yaratish (ixtiyoriy)
```bash
docker-compose exec web python manage.py create_mongo_users
```

## API Endpoints

### Tariflarni ko'rish (public)
```http
GET /api/plans/
```

Response:
```json
[
  {
    "id": 1,
    "name": "free",
    "name_display": "Bepul",
    "price": "0.00",
    "max_users": 100,
    "powered_by_botmother": true,
    "description": "Bepul tarif - 100 tagacha foydalanuvchi",
    ...
  }
]
```

### Loyihaning tarifini ko'rish
```http
GET /api/projects/{project_id}/plan/
Authorization: Bearer <token>
```

Response:
```json
{
  "id": 1,
  "plan_details": {
    "name_display": "Bepul",
    "price": "0.00",
    "max_users": 100
  },
  "status": "active",
  "current_users": 45,
  "limit_exceeded": false,
  "can_add_user": true,
  "days_until_suspension": null
}
```

### Tarifni yangilash
```http
POST /api/projects/{project_id}/plan/upgrade/
Authorization: Bearer <token>
Content-Type: application/json

{
  "plan_id": 2
}
```

Response:
```json
{
  "message": "Plan successfully upgraded",
  "previous_plan": "Bepul",
  "new_plan": "Start",
  "data": { ... }
}
```

### Foydalanish statistikasi
```http
GET /api/projects/{project_id}/plan/usage/
Authorization: Bearer <token>
```

Response:
```json
{
  "current_users": 45,
  "max_users": 100,
  "usage_percentage": 45.0,
  "limit_exceeded": false,
  "can_add_user": true,
  "status": "active",
  "plan_name": "Bepul"
}
```

### Loyiha yaratish (tarif tanlash bilan)
```http
POST /api/projects/
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "Mening botim",
  "plan_id": 2  // ixtiyoriy, default: FREE
}
```

## Limit Monitoring

### Avtomatik monitoring
- Har kuni Celery task ishga tushadi
- Foydalanuvchilar sonini tekshiradi
- Limitdan oshsa:
  1. Status `grace_period` ga o'zgaradi
  2. Foydalanuvchiga notification yuboriladi
  3. 3 kun kutiladi
  4. 3 kundan keyin bot to'xtatiladi (`suspended`)

### Celery konfiguratsiyasi
```python
# config/settings/base.py yoki celery.py da
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'monitor-plan-limits': {
        'task': 'core.apps.api.tasks.plan_monitor.monitor_plan_limits',
        'schedule': crontab(hour=0, minute=0),  # Har kuni yarim tunda
    },
}
```

## Admin Panel

### Tariflar boshqaruvi
URL: `/admin/api/planmodel/`

Xususiyatlar:
- Tariflarni yaratish/tahrirlash
- Limitlarni o'zgartirish
- Faol/nofaol qilish

### Loyiha tariflari monitoring
URL: `/admin/api/projectplanmodel/`

Xususiyatlar:
- Barcha obunalarni ko'rish
- Foydalanish statistikasi (progress bar)
- Grace period tracking
- Bulk actions (faollashtirish, to'xtatish)

## Frontend Integration

### Loyihalar ro'yxatida tarif ko'rsatish
```javascript
// GET /api/projects/ response
{
  "id": 1,
  "name": "My Bot",
  "plan": {
    "id": 1,
    "name": "Bepul",
    "status": "active",
    "current_users": 45,
    "max_users": 100
  }
}
```

### Tarif yangilash oynasi
```javascript
// 1. Barcha tariflarni olish
const plans = await api.get('/api/plans/');

// 2. Foydalanuvchiga ko'rsatish va tanlash
// 3. Yangilash
await api.post(`/api/projects/${projectId}/plan/upgrade/`, {
  plan_id: selectedPlanId
});
```

### Limit warning ko'rsatish
```javascript
const { limit_exceeded, days_until_suspension } = await api.get(
  `/api/projects/${projectId}/plan/usage/`
);

if (limit_exceeded && days_until_suspension) {
  showWarning(`Limit oshib ketdi! ${days_until_suspension} kun qoldi.`);
}
```

## MongoDB Per-Project

### Har bir loyiha uchun:
- Database: `project_{id}`
- User: `project_{id}_user`
- Password: avtomatik generatsiya qilinadi

### Bot servislarda:
```bash
MONGO_ADDR=mongodb://project_123_user:password@mongo:27017/project_123
MONGO_DB_NAME=project_123
```

## Testlar

Barcha testlar muvaffaqiyatli:
```bash
docker-compose exec web python -m pytest core/apps/cms/tests/ -v
# 25 passed in 1.30s
```

## Muammolarni hal qilish

### Plan topilmadi
```bash
# Tariflarni qayta yaratish
docker-compose exec web python manage.py create_pricing_plans --update
```

### Loyihaga tarif biriktirilmagan
```bash
# Avtomatik FREE tarif biriktirish
docker-compose exec web python manage.py assign_plans_to_projects
```

### MongoDB user yaratilmagan
```bash
# Barcha loyihalar uchun userlar yaratish
docker-compose exec web python manage.py create_mongo_users
```

## Xavfsizlik

- Har bir loyihaning MongoDB useri faqat o'z databasega kirishi mumkin
- Parollar xavfsiz generatsiya qilinadi (32 ta belgi)
- Admin orqali barcha monitoring mumkin

## Kelgusi Yangilanishlar

- [ ] Tariflarni Stripe orqali to'lash
- [ ] Tariflar bo'yicha hisobot
- [ ] Custom domain sozlamalari
- [ ] Email notification templates
