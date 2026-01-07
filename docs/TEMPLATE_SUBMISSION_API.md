# Template Submission API - Templatelar yuborish API'si

> **Versiya:** 1.0.0  
> **Base URL:** `http://localhost:8081`  
> **Authentifikatsiya:** JWT Token (Bearer)

---

## Kirish

Ushbu API foydalanuvchilarga o'z loyihalarini template sifatida yuborishga imkon beradi. Administratorlar yuborilgan templatelarni Django Admin panel orqali tasdiqlashi yoki rad etishi mumkin. Tasdiqlangan templatelar umumiy templatelar ro'yxatida ko'rinadi.

---

## 📋 Mundaraja

1. [Authentifikatsiya](#authentifikatsiya)
2. [Template Submission - Yuborish](#template-submission-yuborish)
   - [Template yuborish](#template-yuborish)
   - [Yuborishlar ro'yxati](#yuborishlar-royxati)
   - [Yuborish ma'lumotlari](#yuborish-malumotlari)
   - [Yuborishni tahrirlash](#yuborishni-tahrirlash)
   - [Yuborishni o'chirish](#yuborishni-ochirish)
3. [Admin Panel - Tasdiqlash/Rad etish](#admin-panel-tasdiqlashrad-etish)

---

## Authentifikatsiya

Barcha API so'rovlari uchun JWT token kerak.

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

## Admin Panel - Tasdiqlash/Rad etish

Administratorlar template yuborishlarini Django Admin panel orqali ko'rib chiqadi va tasdiqlaydi/rad etadi.

### Admin panelga kirish

Admin panel URL: `http://localhost:8081/admin/`

Django Admin panel orqali:
1. **Template Submission Request** modeliga kirish
2. Yuborilgan templatelar ro'yxatini ko'rish
3. Har bir yuborishni ko'rib chiqish
4. Tasdiqlash yoki rad etish

### Tasdiqlash jarayoni

Admin panel orqali yuborishni tasdiqlash:

1. Django Admin panelga kirish
2. **Template → Template Submission Requests** bo'limiga o'tish
3. Kerakli yuborishni tanlash
4. **Actions** dropdown dan "Approve selected submissions" tanlash
5. "Go" tugmasini bosish

**Natija:**
- Yangi template avtomatik yaratiladi (`is_verify=true`)
- Template umumiy ro'yxatda ko'rinadi
- Yuborish statusi "approved"ga o'zgaradi
- Foydalanuvchi o'z yuborishlari ro'yxatida tasdiqlangan holatni ko'radi

### Rad etish jarayoni

Admin panel orqali yuborishni rad etish:

1. Django Admin panelga kirish
2. **Template → Template Submission Requests** bo'limiga o'tish
3. Kerakli yuborishni tanlash
4. **Actions** dropdown dan "Reject selected submissions" tanlash
5. "Go" tugmasini bosish

**Natija:**
- Yuborish statusi "rejected"ga o'zgaradi
- Rejection reason avtomatik qo'yiladi: "Rejected by admin via bulk action"
- Foydalanuvchi rad etilgan yuborishni ko'radi va sababni o'qiydi

### Individual tasdiqlash/rad etish

Har bir yuborishni alohida ko'rib chiqish uchun:

1. Yuborishni ochish (ID yoki nom orqali)
2. Barcha ma'lumotlarni tekshirish:
   - Template nomi va tavsifi
   - Rasm va video
   - Narx
   - Kategoriyalar va xususiyatlar
3. Yuborish formasi pastida:
   - **Tasdiqlash uchun**: "Approve selected submissions" actionni ishlatish
   - **Rad etish uchun**: "Reject selected submissions" actionni ishlatish yoki `rejection_reason` maydoniga sabab yozib, statusni "rejected"ga o'zgartirish

### Admin panel funksiyalari

**Filtrlash:**
- Status bo'yicha (pending, approved, rejected)
- Yaratilgan sana
- Ko'rib chiqilgan sana

**Qidirish:**
- Template nomi
- Foydalanuvchi telefon raqami
- Loyiha nomi

**Ko'rish:**
- Ro'yxat ko'rinishi: ID, nom, foydalanuvchi, loyiha, narx, status, sanalar
- Batafsil ko'rinish: Barcha ma'lumotlar, rasim, video, kategoriyalar va xususiyatlar

---

## Ish jarayoni (Workflow)

### Foydalanuvchi uchun:

1. **Loyiha yaratish**: Avval biror loyiha yaratilishi kerak
2. **Template yuborish**: `POST /api/template/submission/` orqali yuboriladi
3. **Status tekshirish**: `GET /api/template/submission/` orqali holat tekshiriladi
4. **Agar "pending"**: Tahrirlash yoki o'chirish mumkin
5. **Agar "approved"**: Template umumiy ro'yxatda paydo bo'ladi
6. **Agar "rejected"**: `rejection_reason`ni o'qib, muammolarni hal qilish va qayta yuborish

### Admin uchun (Django Admin Panel):

1. **Admin panelga kirish**: `http://localhost:8081/admin/`
2. **Yuborishlar ro'yxati**: Template Submission Requests bo'limiga o'tish
3. **Filtrlash**: Faqat "pending" statusdagi yuborishlarni ko'rish
4. **Ko'rib chiqish**: Har bir yuborishning ma'lumotlarini tekshirish
5. **Qaror qabul qilish**:
   - Tasdiqlash: Bulk action "Approve selected submissions"
   - Rad etish: Bulk action "Reject selected submissions" yoki individual ravishda rejection_reason yozish

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

---

## Muhim eslatmalar

1. **Rasm va video yuklash**: Multipart/form-data formatida yuboriladi
2. **Faqat o'z yuborishlarini ko'rish**: Oddiy foydalanuvchilar faqat o'z yuborishlarini ko'radi
3. **Admin panel**: Tasdiqlash/rad etish Django Admin panel orqali amalga oshiriladi
4. **Tahrirlash**: Faqat "pending" statusdagi yuborishlar tahrirlanadi
5. **Status o'zgarishi**: Tasdiqlash/rad etishdan keyin status o'zgarmaydi

---

## Qo'shimcha ma'lumotlar

Kategoriyalar va xususiyatlarni olish uchun:
- `GET /api/template/category/` - Barcha kategoriyalar
- `GET /api/template/feature/` - Barcha xususiyatlar

Template'lar ro'yxatini ko'rish:
- `GET /api/template/template/` - Tasdiqlangan templatelar ro'yxati

Django Admin Panel:
- `http://localhost:8081/admin/` - Admin panel URL
- Template → Template Submission Requests - Yuborishlar ro'yxati

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
