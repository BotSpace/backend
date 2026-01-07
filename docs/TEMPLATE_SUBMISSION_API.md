# Template Submission API - Templatelar yuborish API'si

> **Versiya:** 1.0.0  
> **Base URL:** `http://localhost:8081`  
> **Authentifikatsiya:** JWT Token (Bearer)

---

## Kirish

Ushbu API foydalanuvchilarga o'z loyihalarini template sifatida yuborishga imkon beradi. Administratorlar yuborilgan templatelarni tasdiqlashi yoki rad etishi mumkin. Tasdiqlangan templatelar umumiy templatelar ro'yxatida ko'rinadi.

---

## 📋 Mundaraja

1. [Authentifikatsiya](#authentifikatsiya)
2. [Template Submission - Yuborish](#template-submission-yuborish)
   - [Template yuborish](#template-yuborish)
   - [Yuborishlar ro'yxati](#yuborishlar-royxati)
   - [Yuborish ma'lumotlari](#yuborish-malumotlari)
   - [Yuborishni tahrirlash](#yuborishni-tahrirlash)
   - [Yuborishni o'chirish](#yuborishni-ochirish)
3. [Admin - Tasdiqlash/Rad etish](#admin-tasdiqlashrad-etish)
   - [Template yuborishini tasdiqlash](#template-yuborishini-tasdiqlash)
   - [Template yuborishini rad etish](#template-yuborishini-rad-etish)

---

## Authentifikatsiya

Barcha API so'rovlari uchun JWT token kerak (Admin amaliyotlari bundan mustasno ko'rsatiladi).

**Header:**
```
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## Template Submission - Yuborish

### Template yuborish

Foydalanuvchi o'z loyihasini template sifatida yuborish.

**Endpoint:**  
`POST /api/template/submission/`

**Authentifikatsiya:** Majburiy (Foydalanuvchi)

**Request Body:**
```json
{
  "project": 123,
  "name": "Telegram Bot Template",
  "short_description": "Online do'kon uchun Telegram bot",
  "description": "To'liq funksional online do'kon boti. Mahsulotlar katalogi, savat, to'lov tizimi va boshqalar.",
  "image": "file upload",
  "video": "file upload (optional)",
  "demo_url": "https://t.me/example_bot",
  "original_price": "150000.00",
  "categories": [1, 2],
  "features": [3, 4, 5]
}
```

**Request Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| project | integer | ✅ | Loyiha ID raqami |
| name | string | ✅ | Template nomi |
| short_description | string | ✅ | Qisqa tavsif |
| description | string | ✅ | To'liq tavsif |
| image | file | ❌ | Template rasmi |
| video | file | ❌ | Demo video |
| demo_url | string (URL) | ❌ | Demo bot havolasi |
| original_price | decimal | ✅ | Template narxi (so'm) |
| categories | array[integer] | ❌ | Kategoriyalar ID ro'yxati |
| features | array[integer] | ❌ | Xususiyatlar ID ro'yxati |

**Response (201 Created):**
```json
{
  "status": true,
  "message": "Created successfully",
  "data": {
    "id": 456,
    "project": 123,
    "name": "Telegram Bot Template",
    "short_description": "Online do'kon uchun Telegram bot",
    "description": "To'liq funksional online do'kon boti...",
    "image": "http://localhost:8081/media/template-submissions/image.jpg",
    "video": "http://localhost:8081/media/template-submission-videos/video.mp4",
    "demo_url": "https://t.me/example_bot",
    "original_price": "150000.00",
    "categories": [1, 2],
    "features": [3, 4, 5]
  }
}
```

**Errors:**
- `400 Bad Request` - Noto'g'ri ma'lumotlar
- `401 Unauthorized` - Token yo'q yoki noto'g'ri
- `404 Not Found` - Loyiha topilmadi

---

### Yuborishlar ro'yxati

Foydalanuvchi o'z yuborishlarini ko'rish.

**Endpoint:**  
`GET /api/template/submission/`

**Authentifikatsiya:** Majburiy

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| page | integer | Sahifa raqami (default: 1) |
| page_size | integer | Har sahifada nechta (default: 10) |

**Response (200 OK):**
```json
{
  "status": true,
  "message": "Retrieved successfully",
  "data": {
    "count": 5,
    "next": "http://localhost:8081/api/template/submission/?page=2",
    "previous": null,
    "results": [
      {
        "id": 456,
        "user_phone": "+998901234567",
        "project": 123,
        "project_name": "My Bot Project",
        "name": "Telegram Bot Template",
        "short_description": "Online do'kon uchun Telegram bot",
        "image": "http://localhost:8081/media/template-submissions/image.jpg",
        "original_price": "150000.00",
        "categories": [
          {
            "id": 1,
            "name": "E-commerce"
          }
        ],
        "status": "pending",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ]
  }
}
```

**Status qiymatlari:**
- `pending` - Ko'rib chiqilmoqda
- `approved` - Tasdiqlangan
- `rejected` - Rad etilgan

---

### Yuborish ma'lumotlari

Bitta yuborishning to'liq ma'lumotlarini ko'rish.

**Endpoint:**  
`GET /api/template/submission/{id}/`

**Authentifikatsiya:** Majburiy

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Yuborish ID raqami |

**Response (200 OK):**
```json
{
  "status": true,
  "message": "Retrieved successfully",
  "data": {
    "id": 456,
    "user_phone": "+998901234567",
    "project": 123,
    "project_name": "My Bot Project",
    "name": "Telegram Bot Template",
    "short_description": "Online do'kon uchun Telegram bot",
    "description": "To'liq funksional online do'kon boti. Mahsulotlar katalogi, savat, to'lov tizimi va boshqalar.",
    "image": "http://localhost:8081/media/template-submissions/image.jpg",
    "video": "http://localhost:8081/media/template-submission-videos/video.mp4",
    "demo_url": "https://t.me/example_bot",
    "original_price": "150000.00",
    "categories": [
      {
        "id": 1,
        "name": "E-commerce"
      }
    ],
    "features": [
      {
        "id": 3,
        "name": "Mahsulotlar katalogi",
        "value": "500+ mahsulotlarni boshqarish"
      }
    ],
    "status": "pending",
    "rejection_reason": null,
    "template": null,
    "reviewed_by_phone": null,
    "reviewed_at": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

**Errors:**
- `404 Not Found` - Yuborish topilmadi yoki ruxsat yo'q

---

### Yuborishni tahrirlash

Faqat "pending" statusdagi yuborishlarni tahrirlash mumkin.

**Endpoint:**  
`PATCH /api/template/submission/{id}/`

**Authentifikatsiya:** Majburiy (Foydalanuvchi - faqat o'z yuborishlari)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Yuborish ID raqami |

**Request Body (partial update):**
```json
{
  "name": "Yangilangan nom",
  "short_description": "Yangilangan tavsif",
  "original_price": "180000.00"
}
```

**Response (200 OK):**
```json
{
  "status": true,
  "message": "Updated successfully",
  "data": {
    "id": 456,
    "name": "Yangilangan nom",
    "short_description": "Yangilangan tavsif",
    "original_price": "180000.00",
    ...
  }
}
```

**Errors:**
- `400 Bad Request` - Pending bo'lmagan yuborishni tahrirlash
- `403 Forbidden` - Boshqa foydalanuvchining yuborishini tahrirlash
- `404 Not Found` - Yuborish topilmadi

---

### Yuborishni o'chirish

Faqat "pending" statusdagi yuborishlarni o'chirish mumkin.

**Endpoint:**  
`DELETE /api/template/submission/{id}/`

**Authentifikatsiya:** Majburiy (Foydalanuvchi yoki Admin)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Yuborish ID raqami |

**Response (204 No Content):**
```
Muvaffaqiyatli o'chirildi
```

**Errors:**
- `400 Bad Request` - Pending bo'lmagan yuborishni o'chirish
- `403 Forbidden` - Ruxsat yo'q
- `404 Not Found` - Yuborish topilmadi

---

## Admin - Tasdiqlash/Rad etish

### Template yuborishini tasdiqlash

Admin foydalanuvchi yuborishni tasdiqlaydi va template yaratadi.

**Endpoint:**  
`POST /api/template/submission/{id}/approve/`

**Authentifikatsiya:** Majburiy (faqat Admin)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Yuborish ID raqami |

**Request Body:**
```json
{
  "discount": "10.00",
  "discount_type": "percent"
}
```

**Request Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| discount | decimal | ❌ | Chegirma miqdori (default: 0) |
| discount_type | string | ❌ | Chegirma turi: "percent" yoki "amount" (default: "percent") |

**Response (200 OK):**
```json
{
  "status": true,
  "message": "Approved successfully",
  "data": {
    "id": 456,
    "status": "approved",
    "template": 789,
    "reviewed_by_phone": "+998901234568",
    "reviewed_at": "2024-01-16T14:20:00Z",
    ...
  }
}
```

**Natija:**
- Yangi template yaratiladi va `is_verify=true` bo'ladi
- Template umumiy ro'yxatda ko'rinadi
- Yuborish statusи "approved"ga o'zgaradi

**Errors:**
- `400 Bad Request` - Faqat "pending" yuborishlarni tasdiqlash mumkin
- `403 Forbidden` - Admin emas
- `404 Not Found` - Yuborish topilmadi

---

### Template yuborishini rad etish

Admin foydalanuvchi yuborishni rad etadi.

**Endpoint:**  
`POST /api/template/submission/{id}/reject/`

**Authentifikatsiya:** Majburiy (faqat Admin)

**Path Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| id | integer | Yuborish ID raqami |

**Request Body:**
```json
{
  "rejection_reason": "Template sifati yetarli emas. Iltimos, quyidagi masalalarni to'g'irlang: 1) UI/UX yaxshilash, 2) Kod sifati, 3) Dokumentatsiya qo'shish"
}
```

**Request Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| rejection_reason | string | ✅ | Rad etish sababi |

**Response (200 OK):**
```json
{
  "status": true,
  "message": "Rejected successfully",
  "data": {
    "id": 456,
    "status": "rejected",
    "rejection_reason": "Template sifati yetarli emas...",
    "template": null,
    "reviewed_by_phone": "+998901234568",
    "reviewed_at": "2024-01-16T14:25:00Z",
    ...
  }
}
```

**Errors:**
- `400 Bad Request` - Faqat "pending" yuborishlarni rad etish mumkin
- `403 Forbidden` - Admin emas
- `404 Not Found` - Yuborish topilmadi

---

## Ish jarayoni (Workflow)

### Foydalanuvchi uchun:

1. **Loyiha yaratish**: Avval biror loyiha yaratilishi kerak
2. **Template yuborish**: `POST /api/template/submission/` orqali yuboriladi
3. **Status tekshirish**: `GET /api/template/submission/` orqali holat tekshiriladi
4. **Agar "pending"**: Tahrirlash yoki o'chirish mumkin
5. **Agar "approved"**: Template umumiy ro'yxatda paydo bo'ladi
6. **Agar "rejected"**: `rejection_reason`ni o'qib, muammolarni hal qilish va qayta yuborish

### Admin uchun:

1. **Barcha yuborishlarni ko'rish**: `GET /api/template/submission/` (Admin barcha yuborishlarni ko'radi)
2. **Yuborishni ko'rib chiqish**: `GET /api/template/submission/{id}/`
3. **Qaror qabul qilish**:
   - Tasdiqlash: `POST /api/template/submission/{id}/approve/`
   - Rad etish: `POST /api/template/submission/{id}/reject/`

---

## Misollar

### Frontend uchun JavaScript misoli

#### Template yuborish:

```javascript
async function submitTemplate(projectId, templateData) {
  const formData = new FormData();
  formData.append('project', projectId);
  formData.append('name', templateData.name);
  formData.append('short_description', templateData.shortDescription);
  formData.append('description', templateData.description);
  formData.append('original_price', templateData.price);
  
  if (templateData.image) {
    formData.append('image', templateData.image);
  }
  
  if (templateData.video) {
    formData.append('video', templateData.video);
  }
  
  if (templateData.demoUrl) {
    formData.append('demo_url', templateData.demoUrl);
  }
  
  // Categories va features array
  templateData.categories.forEach(catId => {
    formData.append('categories', catId);
  });
  
  templateData.features.forEach(featId => {
    formData.append('features', featId);
  });

  const response = await fetch('http://localhost:8081/api/template/submission/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${localStorage.getItem('token')}`
    },
    body: formData
  });
  
  const result = await response.json();
  return result;
}
```

#### Yuborishlar ro'yxatini olish:

```javascript
async function getMySubmissions(page = 1) {
  const response = await fetch(
    `http://localhost:8081/api/template/submission/?page=${page}`,
    {
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`
      }
    }
  );
  
  const result = await response.json();
  return result.data;
}
```

#### Yuborishni tasdiqlash (Admin):

```javascript
async function approveSubmission(submissionId, discount = 0, discountType = 'percent') {
  const response = await fetch(
    `http://localhost:8081/api/template/submission/${submissionId}/approve/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        discount: discount,
        discount_type: discountType
      })
    }
  );
  
  const result = await response.json();
  return result;
}
```

#### Yuborishni rad etish (Admin):

```javascript
async function rejectSubmission(submissionId, reason) {
  const response = await fetch(
    `http://localhost:8081/api/template/submission/${submissionId}/reject/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${localStorage.getItem('token')}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        rejection_reason: reason
      })
    }
  );
  
  const result = await response.json();
  return result;
}
```

---

## Muhim eslatmalar

1. **Rasm va video yuklash**: Multipart/form-data formatida yuboriladi
2. **Faqat o'z yuborishlarini ko'rish**: Oddiy foydalanuvchilar faqat o'z yuborishlarini ko'radi
3. **Admin huquqlari**: Tasdiqlash/rad etish faqat admin uchun
4. **Tahrirlash**: Faqat "pending" statusdagi yuborishlar tahrirlanadi
5. **Status o'zgarishi**: Tasdiqlash/rad etishdan keyin status o'zgarmaydi

---

## Qo'shimcha ma'lumotlar

Kategoriyalar va xususiyatlarni olish uchun:
- `GET /api/template/category/` - Barcha kategoriyalar
- `GET /api/template/feature/` - Barcha xususiyatlar

Template'lar ro'yxatini ko'rish:
- `GET /api/template/template/` - Tasdiqlangan templatelar ro'yxati

---

## Savol va javoblar

**Q: Yuborishni qayta yuborish mumkinmi?**  
A: Ha, rad etilgan yuborishni o'chirib, yangi yuborish yaratish mumkin.

**Q: Bir loyihani bir necha marta yuborish mumkinmi?**  
A: Ha, mumkin. Har bir yuborish mustaqil ko'rib chiqiladi.

**Q: Tasdiqlangan templateni o'zgartirish mumkinmi?**  
A: Yo'q, tasdiqlangan template yaratilganidan keyin, yuborishni o'zgartirish mumkin emas. Lekin templateni o'zini admin panel orqali tahrirlash mumkin.

**Q: File upload limitlari?**  
A: Rasm - 10MB, Video - 100MB (server sozlamalariga bog'liq)
