# BotMother Backend API Documentation

> **Version:** 1.0.0  
> **Base URL:** `http://localhost:8081`  
> **Protocol:** HTTP/HTTPS

---

## 📋 Mundareja

1. [Kirish](#kirish)
2. [Autentifikatsiya](#autentifikatsiya)
   - [Ro'yxatdan o'tish](#royxatdan-otish)
   - [Login (Token olish)](#login-token-olish)
   - [Token yangilash](#token-yangilash)
   - [Token tekshirish](#token-tekshirish)
3. [Foydalanuvchi](#foydalanuvchi)
   - [Profil ma'lumotlari](#profil-malumotlari)
   - [Profilni yangilash](#profilni-yangilash)
   - [Parolni o'zgartirish](#parolni-ozgartirish)
4. [Parolni tiklash](#parolni-tiklash)
5. [Loyiha (Project)](#loyiha-project)
   - [Loyihalar ro'yxati](#loyihalar-royxati)
   - [Loyiha yaratish](#loyiha-yaratish)
   - [Loyiha ma'lumotlari](#loyiha-malumotlari)
   - [Loyihani yangilash](#loyihani-yangilash)
   - [Loyihani o'chirish](#loyihani-ochirish)
   - [Debug rejimi](#debug-rejimi)
   - [Debug ma'lumotlari](#debug-malumotlari)
   - [Debug to'xtatish](#debug-toxtatish)
6. [Release](#release)
   - [Releaselar ro'yxati](#releaselar-royxati)
   - [Release yaratish](#release-yaratish)
   - [Release ma'lumotlari](#release-malumotlari)
   - [Release to'xtatish](#release-toxtatish)
7. [Environment o'zgaruvchilari](#environment-ozgaruvchilari)
   - [Environment ro'yxati](#environment-royxati)
   - [Environment yaratish](#environment-yaratish)
   - [Environment ma'lumotlari](#environment-malumotlari)
   - [Environment yangilash](#environment-yangilash)
   - [Environment o'chirish](#environment-ochirish)
8. [CMS Collection](#cms-collection)
   - [Collection ro'yxati](#collection-royxati)
   - [Collection yaratish](#collection-yaratish)
   - [Collection ma'lumotlari](#collection-malumotlari)
   - [Collection yangilash](#collection-yangilash)
   - [Collection o'chirish](#collection-ochirish)
   - [Collection query operatsiyalari](#collection-query-operatsiyalari)
9. [Server-Sent Events (SSE)](#server-sent-events-sse)
10. [Sozlamalar](#sozlamalar)
11. [Telegram Auth](#telegram-auth)
12. [Xatoliklar](#xatoliklar)

---

## Kirish

BotMother - telegram bot yaratish va boshqarish platformasi. Bu API orqali siz bot loyihalarini yaratish, boshqarish, debug qilish va release chiqarishingiz mumkin.

### Asosiy xususiyatlar:

- 🔐 JWT autentifikatsiya
- 🤖 Telegram bot boshqaruvi
- 📊 CMS (Content Management System)
- 🔄 Real-time loglar (SSE)
- 🐳 Docker asosida bot deployment
- 🌍 Ko'p tillilik (Modeltranslation)

### Umumiy ma'lumotlar:

- **Content-Type:** `application/json`
- **Authentication:** Bearer Token (JWT)
- **Date Format:** ISO 8601 (`YYYY-MM-DDTHH:mm:ss.sssZ`)

---

## Autentifikatsiya

### Ro'yxatdan o'tish

Yangi foydalanuvchi ro'yxatdan o'tkazish uchun 3 bosqichli jarayon:

#### 1. Register (SMS yuborish)

```http
POST /auth/register/
```

**Request Body:**
```json
{
  "phone": "+998901234567",
  "first_name": "Ism",
  "last_name": "Familiya",
  "password": "qwerty123"
}
```

**Response:** `202 Accepted`
```json
{
  "detail": "Sms +998901234567 raqamiga yuborildi"
}
```

**Validation xatoliklari:**
- `phone` - telefon raqami allaqachon ro'yxatdan o'tgan
- `first_name`, `last_name` - majburiy maydonlar
- `password` - minimal uzunlik 6 ta belgi

---

#### 2. Confirm (Kodni tasdiqlash)

```http
POST /auth/confirm/
```

**Request Body:**
```json
{
  "phone": "+998901234567",
  "code": "1234"
}
```

**Response:** `202 Accepted`
```json
{
  "detail": "Tasdiqlash ko'di qabul qilindi",
  "token": {
    "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
  }
}
```

**Xatoliklar:**
- `403 Forbidden` - Noto'g'ri kod yoki muddati o'tgan

---

#### 3. Resend (Kodni qayta yuborish)

```http
POST /auth/resend/
```

**Request Body:**
```json
{
  "phone": "+998901234567"
}
```

**Response:** `200 OK`
```json
{
  "detail": "Sms +998901234567 raqamiga yuborildi"
}
```

---

### Login (Token olish)

Mavjud foydalanuvchi uchun token olish:

```http
POST /auth/token/
```

**Request Body:**
```json
{
  "phone": "+998901234567",
  "password": "qwerty123"
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Xatoliklar:**
- `401 Unauthorized` - Noto'g'ri telefon yoki parol

---

### Token yangilash

Access token muddati tugaganda yangilash:

```http
POST /auth/token/refresh/
```

**Request Body:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

### Token tekshirish

Tokenning haqiqiyligini tekshirish:

```http
POST /auth/token/verify/
```

**Request Body:**
```json
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:** `200 OK`
```json
{}
```

**Xatoliklar:**
- `401 Unauthorized` - Token noto'g'ri yoki muddati o'tgan

---

## Foydalanuvchi

### Profil ma'lumotlari

```http
GET /auth/me/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "phone": "+998901234567",
  "username": "user123",
  "first_name": "Ism",
  "last_name": "Familiya",
  "role": "USER",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z",
  "validated_at": "2024-01-01T12:00:00Z"
}
```

---

### Profilni yangilash

```http
PATCH /auth/user-update/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "first_name": "Yangi ism",
  "last_name": "Yangi familiya",
  "username": "newusername"
}
```

**Response:** `200 OK`
```json
{
  "detail": "Malumotlar yangilandi"
}
```

---

### Parolni o'zgartirish

```http
POST /auth/change-password/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "old_password": "eski_parol",
  "new_password": "yangi_parol"
}
```

**Response:** `200 OK`
```json
{
  "detail": "password changed successfully"
}
```

**Xatoliklar:**
- `403 Forbidden` - Eski parol noto'g'ri

---

## Parolni tiklash

### 1. Parolni tiklash so'rovi

```http
POST /auth/reset-password/
```

**Request Body:**
```json
{
  "phone": "+998901234567"
}
```

**Response:** `200 OK`
```json
{
  "detail": "Sms +998901234567 raqamiga yuborildi"
}
```

---

### 2. Kodni tasdiqlash

```http
POST /auth/reset-password-confirm/
```

**Request Body:**
```json
{
  "phone": "+998901234567",
  "code": "1234"
}
```

**Response:** `200 OK`
```json
{
  "token": "uuid-token-string",
  "created_at": "2024-01-01T12:00:00Z",
  "updated_at": "2024-01-01T12:00:00Z"
}
```

---

### 3. Yangi parol o'rnatish

```http
POST /auth/reset-password-set/
```

**Request Body:**
```json
{
  "token": "uuid-token-string",
  "password": "yangi_parol"
}
```

**Response:** `200 OK`
```json
{
  "detail": "password updated"
}
```

---

## Loyiha (Project)

### Loyihalar ro'yxati

```http
GET /api/project/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "Mening botim",
    "release": {
      "id": 5,
      "version": 3,
      "status": "running",
      "service_id": "bot_1_release_3",
      "created_at": "2024-01-01T12:00:00Z"
    }
  }
]
```

---

### Loyiha yaratish

```http
POST /api/project/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "name": "Yangi bot loyihasi",
  "flow": {
    "nodes": [],
    "edges": []
  }
}
```

**Response:** `201 Created`
```json
{
  "id": 2,
  "name": "Yangi bot loyihasi",
  "flow": {
    "nodes": [],
    "edges": []
  }
}
```

---

### Loyiha ma'lumotlari

```http
GET /api/project/{id}/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Mening botim",
  "debug": {
    "id": 1,
    "status": "running",
    "service_id": "bot_1_debug",
    "flow_hash": "abc123def456"
  },
  "release": {
    "id": 5,
    "version": 3,
    "status": "running",
    "service_id": "bot_1_release_3"
  },
  "debug_bot": true,
  "release_bot": false,
  "flow": {
    "nodes": [
      {
        "id": "node1",
        "type": "start",
        "data": {
          "label": "Start"
        }
      }
    ],
    "edges": []
  }
}
```

---

### Loyihani yangilash

```http
PATCH /api/project/{id}/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "name": "Yangilangan nom",
  "flow": {
    "nodes": [...],
    "edges": [...]
  }
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "Yangilangan nom",
  "flow": {...}
}
```

---

### Loyihani o'chirish

```http
DELETE /api/project/{id}/
Authorization: Bearer {access_token}
```

**Response:** `204 No Content`

---

### Debug rejimi

Loyihani debug rejimida ishga tushirish:

```http
GET /api/project/{id}/debug/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "detail": "Updated"
}
```

**Muhim:** Debug uchun `BOT_TOKEN` environment o'zgaruvchisi kerak!

---

### Debug ma'lumotlari

```http
GET /api/project/{id}/info/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "status": "running",
  "service_id": "bot_1_debug",
  "flow_hash": "abc123def456",
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Status qiymatlari:**
- `pending` - kutilmoqda
- `initializing` - ishga tushirilmoqda
- `running` - ishlayapti
- `stopping` - to'xtatilmoqda
- `stopped` - to'xtatilgan
- `error` - xatolik

---

### Debug to'xtatish

```http
GET /api/project/{id}/stop/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "detail": "Stopped"
}
```

---

## Release

### Releaselar ro'yxati

```http
GET /api/relase/?project={project_id}
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `project` (required) - loyiha ID

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "version": 1,
    "status": "running",
    "service_id": "bot_1_release_1",
    "created_at": "2024-01-01T12:00:00Z"
  },
  {
    "id": 2,
    "version": 2,
    "status": "stopped",
    "service_id": "bot_1_release_2",
    "created_at": "2024-01-02T12:00:00Z"
  }
]
```

---

### Release yaratish

```http
POST /api/relase/
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "project": 1
}
```

**Response:** `201 Created`
```json
{
  "id": 3,
  "version": 3,
  "status": "pending",
  "service_id": null,
  "flow": {
    "nodes": [...],
    "edges": [...]
  },
  "created_at": "2024-01-03T12:00:00Z"
}
```

**Eslatma:** Release yaratilganda avtomatik ravishda loyiha `flow` nusxalanadi va versiya 1 ga oshiriladi.

---

### Release ma'lumotlari

```http
GET /api/relase/{id}/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "version": 1,
  "status": "running",
  "service_id": "bot_1_release_1",
  "flow": {
    "nodes": [...],
    "edges": [...]
  },
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

### Release to'xtatish

```http
GET /api/relase/{id}/stop/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "detail": "Stopped"
}
```

---

## Environment o'zgaruvchilari

### Environment ro'yxati

```http
GET /api/enviroment/?project={project_id}
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `project` (required) - loyiha ID

**Response:** `200 OK`
```json
[
  {
    "key": "BOT_TOKEN",
    "value": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
    "created_at": "2024-01-01T12:00:00Z"
  },
  {
    "key": "RELEASE_BOT_TOKEN",
    "value": "987654:XYZ-ABC9876ghIkl-abc12W2v1u456ew22",
    "created_at": "2024-01-01T12:00:00Z"
  },
  {
    "key": "API_KEY",
    "value": "my-secret-api-key",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

---

### Environment yaratish

```http
POST /api/enviroment/?project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "project": 1,
  "key": "API_KEY",
  "value": "my-secret-value"
}
```

**Response:** `201 Created`
```json
{
  "key": "API_KEY",
  "value": "my-secret-value",
  "created_at": "2024-01-01T12:00:00Z"
}
```

**Unique constraint:** Bir loyihada bir xil `key` bo'la olmaydi.

---

### Environment ma'lumotlari

```http
GET /api/enviroment/{key}/?project={project_id}
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "key": "BOT_TOKEN",
  "value": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11",
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

### Environment yangilash

```http
PATCH /api/enviroment/{key}/?project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "value": "yangi-qiymat"
}
```

**Response:** `200 OK`
```json
{
  "key": "API_KEY",
  "value": "yangi-qiymat",
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

### Environment o'chirish

```http
DELETE /api/enviroment/{key}/?project={project_id}
Authorization: Bearer {access_token}
```

**Response:** `204 No Content`

---

## CMS Collection

CMS - MongoDB asosidagi dinamik ma'lumotlar bazasi. Siz o'z collection'laringizni yaratib, ular bilan ishlashingiz mumkin.

### Collection ro'yxati

```http
GET /api/collection/?project={project_id}
Authorization: Bearer {access_token}
```

**Query Parameters:**
- `project` (required) - loyiha ID

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "name": "users",
    "created_at": "2024-01-01T12:00:00Z"
  },
  {
    "id": 2,
    "name": "products",
    "created_at": "2024-01-01T12:00:00Z"
  }
]
```

---

### Collection yaratish

```http
POST /api/collection/?project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "name": "users",
  "project": 1,
  "fields": [
    {
      "name": "telegram_id",
      "type": "NUMBER",
      "required": true
    },
    {
      "name": "username",
      "type": "TEXT",
      "required": false
    },
    {
      "name": "balance",
      "type": "NUMBER",
      "required": true,
      "default": "0"
    },
    {
      "name": "is_active",
      "type": "BOOLEAN",
      "required": true,
      "default": "true"
    },
    {
      "name": "registered_at",
      "type": "DATE",
      "required": true
    }
  ]
}
```

**Field Types:**
- `TEXT` - matn
- `NUMBER` - raqam
- `BOOLEAN` - true/false
- `DATE` - sana

**Response:** `201 Created`
```json
{
  "id": 1,
  "name": "users",
  "fields": [
    {
      "id": 1,
      "name": "telegram_id",
      "type": "NUMBER",
      "required": true,
      "default": null
    },
    {
      "id": 2,
      "name": "username",
      "type": "TEXT",
      "required": false,
      "default": null
    },
    {
      "id": 3,
      "name": "balance",
      "type": "NUMBER",
      "required": true,
      "default": "0"
    },
    {
      "id": 4,
      "name": "is_active",
      "type": "BOOLEAN",
      "required": true,
      "default": "true"
    },
    {
      "id": 5,
      "name": "registered_at",
      "type": "DATE",
      "required": true,
      "default": null
    }
  ],
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

### Collection ma'lumotlari

```http
GET /api/collection/{name}/?project={project_id}
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "users",
  "fields": [
    {
      "id": 1,
      "name": "telegram_id",
      "type": "NUMBER",
      "required": true,
      "default": null
    },
    {
      "id": 2,
      "name": "username",
      "type": "TEXT",
      "required": false,
      "default": null
    }
  ],
  "created_at": "2024-01-01T12:00:00Z"
}
```

---

### Collection yangilash

```http
PATCH /api/collection/{name}/?project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "fields": [
    {
      "name": "telegram_id",
      "type": "NUMBER",
      "required": true
    },
    {
      "name": "email",
      "type": "TEXT",
      "required": false
    }
  ]
}
```

**Response:** `200 OK`
```json
{
  "id": 1,
  "name": "users",
  "fields": [...]
}
```

---

### Collection o'chirish

```http
DELETE /api/collection/{name}/?project={project_id}
Authorization: Bearer {access_token}
```

**Response:** `204 No Content`

---

### Collection query operatsiyalari

Collection ichidagi ma'lumotlar bilan ishlash uchun:

#### 1. Insert (Ma'lumot qo'shish)

```http
POST /api/collection/{name}/query/?action=insert&project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "telegram_id": 123456789,
  "username": "john_doe",
  "balance": 100,
  "is_active": true,
  "registered_at": "2024-01-01T12:00:00Z"
}
```

**Response:** `200 OK`
```json
{
  "inserted_id": "507f1f77bcf86cd799439011"
}
```

---

#### 2. Find (Ko'p ma'lumot qidirish)

```http
POST /api/collection/{name}/query/?action=find&project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "where": {
    "is_active": true,
    "balance": {
      "$gte": 50
    }
  },
  "limit": 10,
  "skip": 0,
  "sort": {
    "balance": -1
  }
}
```

**MongoDB Query Operators:**
- `$eq` - teng
- `$ne` - teng emas
- `$gt` - katta
- `$gte` - katta yoki teng
- `$lt` - kichik
- `$lte` - kichik yoki teng
- `$in` - massivda bor
- `$nin` - massivda yo'q

**Response:** `200 OK`
```json
[
  {
    "_id": {
      "$oid": "507f1f77bcf86cd799439011"
    },
    "telegram_id": 123456789,
    "username": "john_doe",
    "balance": 100,
    "is_active": true,
    "registered_at": {
      "$date": "2024-01-01T12:00:00Z"
    }
  },
  {
    "_id": {
      "$oid": "507f1f77bcf86cd799439012"
    },
    "telegram_id": 987654321,
    "username": "jane_smith",
    "balance": 200,
    "is_active": true,
    "registered_at": {
      "$date": "2024-01-02T12:00:00Z"
    }
  }
]
```

---

#### 3. Find One (Bitta ma'lumot qidirish)

```http
POST /api/collection/{name}/query/?action=find_one&project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "where": {
    "telegram_id": 123456789
  }
}
```

**Response:** `200 OK`
```json
{
  "_id": {
    "$oid": "507f1f77bcf86cd799439011"
  },
  "telegram_id": 123456789,
  "username": "john_doe",
  "balance": 100,
  "is_active": true,
  "registered_at": {
    "$date": "2024-01-01T12:00:00Z"
  }
}
```

**Agar topilmasa:** `404 Not Found`
```json
{
  "detail": "Not found"
}
```

---

#### 4. Update (Ma'lumot yangilash)

```http
POST /api/collection/{name}/query/?action=update&project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "where": {
    "telegram_id": 123456789
  },
  "data": {
    "$set": {
      "balance": 150,
      "username": "new_username"
    }
  }
}
```

**MongoDB Update Operators:**
- `$set` - qiymat o'rnatish
- `$inc` - raqamga qo'shish
- `$unset` - maydonni o'chirish
- `$push` - massivga qo'shish
- `$pull` - massivdan o'chirish

**Response:** `200 OK`
```json
{
  "modified_count": 1
}
```

---

#### 5. Delete (Ma'lumot o'chirish)

```http
POST /api/collection/{name}/query/?action=delete&project={project_id}
Authorization: Bearer {access_token}
```

**Request Body:**
```json
{
  "where": {
    "telegram_id": 123456789
  }
}
```

**Response:** `200 OK`
```json
{
  "deleted_count": 1
}
```

---

## Server-Sent Events (SSE)

Real-time log oqimi olish uchun:

```http
GET /sse/api/project/{service_id}/logs/
```

**Headers:**
- `Accept: text/event-stream`

**Response:** `200 OK` (Stream)
```
data: [INFO] Bot started successfully
data: [INFO] Connected to Telegram API
data: [DEBUG] Received message from user 123456789
data: [ERROR] Database connection failed
data: Container is not running
```

**Muhim:**
- Bu endpoint SSE (Server-Sent Events) protokoli bilan ishlaydi
- Stream ko'rinishida ma'lumot keladi
- Konteyner to'xtaganda `"Container is not running"` xabari keladi
- Frontend'da EventSource API ishlatish tavsiya etiladi

**JavaScript misoli:**
```javascript
const eventSource = new EventSource(
  `http://localhost:8081/sse/api/project/${serviceId}/logs/`
);

eventSource.onmessage = (event) => {
  console.log('Log:', event.data);
};

eventSource.onerror = (error) => {
  console.error('SSE Error:', error);
  eventSource.close();
};
```

---

## Sozlamalar

### Sozlamalar ro'yxati

```http
GET /api/settings/
Authorization: Bearer {access_token}
```

**Response:** `200 OK`
```json
[
  {
    "id": 1,
    "key": "theme",
    "value": "dark"
  }
]
```

---

## Telegram Auth

Telegram orqali autentifikatsiya:

```http
POST /authbot/login/
```

**Request Body:**
```json
{
  "id": 123456789,
  "first_name": "John",
  "username": "john_doe",
  "auth_date": 1234567890,
  "hash": "telegram-widget-hash"
}
```

**Response:** `200 OK`
```json
{
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

---

## Xatoliklar

### Umumiy xatolik kodlari:

#### `400 Bad Request`
Noto'g'ri so'rov parametrlari:
```json
{
  "field_name": [
    "Bu maydon majburiy",
    "Noto'g'ri format"
  ]
}
```

#### `401 Unauthorized`
Autentifikatsiya kerak yoki token noto'g'ri:
```json
{
  "detail": "Authentication credentials were not provided."
}
```

#### `403 Forbidden`
Ruxsat yo'q:
```json
{
  "detail": "You do not have permission to perform this action."
}
```

#### `404 Not Found`
Resurs topilmadi:
```json
{
  "detail": "Not found."
}
```

#### `500 Internal Server Error`
Server xatosi:
```json
{
  "detail": "Internal server error"
}
```

---

## Postman Collection

Postman collection'ni import qilish uchun quyidagi strukturani ishlating:

### Base URL
```
http://localhost:8081
```

### Headers (barcha autentifikatsiya talab qilingan endpoint'lar uchun):
```
Authorization: Bearer {{access_token}}
Content-Type: application/json
```

### Environment Variables
```json
{
  "access_token": "your-jwt-access-token",
  "refresh_token": "your-jwt-refresh-token",
  "base_url": "http://localhost:8081",
  "project_id": "1"
}
```

---

## Qo'shimcha ma'lumotlar

### Rate Limiting
- Register, Confirm, Resend endpoint'lari uchun rate limiting mavjud
- Default: 100 request/hour per user

### CORS
- Frontend development uchun CORS yoqilgan
- Production'da faqat belgilangan domain'lardan so'rov qabul qilinadi

### Pagination
Ro'yxat endpoint'larida default pagination mavjud emas, lekin qo'shilishi mumkin.

### Filtering
Ayrim endpoint'larda query parametrlari orqali filterlash mumkin:
- `?project=1` - loyiha bo'yicha
- `?search=text` - qidiruv (qo'shimcha qo'shilishi kerak)

---

## Muallif

**BotMother Team**  
© 2024 Barcha huquqlar himoyalangan

---

**Oxirgi yangilanish:** 2024-11-03
