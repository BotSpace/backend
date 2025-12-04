# Chat API Documentation

Chat API MongoDB ma'lumotlar bilan ishlash uchun yaratilgan. Har bir project uchun `users` va `chat` collectionlari mavjud.

## API Endpoints

### 1. Userlarni va ularning xabarlarini olish

**Endpoint:** `GET /api/chat/users/{project_id}/`

**Tavsif:** Project uchun barcha userlarni olish, har bir user uchun oxirgi 50 ta xabar va o'qilmagan xabarlar sonini ko'rsatadi.

**Query Parameters:**
- `limit` (optional, default: 50) - Qaytariladigan userlar soni
- `skip` (optional, default: 0) - O'tkazib yuborilgan userlar soni (pagination)

**Response:**
```json
{
  "users": [
    {
      "user": {
        "_id": "507f1f77bcf86cd799439011",
        "chat_id": "123456789",
        "first_name": "John",
        "last_name": "Doe",
        "created_at": "2024-12-04T10:00:00Z"
      },
      "messages": [
        {
          "_id": "507f191e810c19729de860ea",
          "chat_id": "123456789",
          "text": "Salom",
          "read": false
        }
      ],
      "unread_count": 5,
      "total_messages": 50
    }
  ],
  "total": 100,
  "limit": 50,
  "skip": 0
}
```

**Misol:**
```bash
curl -X GET "http://localhost:8000/api/chat/users/1/?limit=20&skip=0" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 2. Bitta user uchun barcha xabarlarni olish

**Endpoint:** `GET /api/chat/messages/{project_id}/{chat_id}/`

**Tavsif:** Bitta user uchun barcha xabarlarni olish.

**Query Parameters:**
- `limit` (optional, default: 50) - Qaytariladigan xabarlar soni
- `skip` (optional, default: 0) - O'tkazib yuborilgan xabarlar soni

**Response:**
```json
{
  "messages": [
    {
      "_id": "507f191e810c19729de860ea",
      "chat_id": "123456789",
      "text": "Salom",
      "read": false
    }
  ],
  "total": 150,
  "limit": 50,
  "skip": 0
}
```

**Misol:**
```bash
curl -X GET "http://localhost:8000/api/chat/messages/1/123456789/?limit=100" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### 3. Xabarlarni o'qilgan deb belgilash

**Endpoint:** `POST /api/chat/mark-read/{project_id}/`

**Tavsif:** Xabarlarni o'qilgan deb belgilash.

**Request Body:**
```json
{
  "chat_id": "123456789",
  "message_ids": ["507f191e810c19729de860ea", "507f191e810c19729de860eb"]
}
```

**Agar `message_ids` berilmasa, barcha xabarlar o'qilgan deb belgilanadi.**

**Response:**
```json
{
  "success": true,
  "modified_count": 2
}
```

**Misol:**
```bash
# Faqat ma'lum xabarlarni o'qilgan qilish
curl -X POST "http://localhost:8000/api/chat/mark-read/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "123456789",
    "message_ids": ["507f191e810c19729de860ea"]
  }'

# Barcha xabarlarni o'qilgan qilish
curl -X POST "http://localhost:8000/api/chat/mark-read/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "123456789"
  }'
```

---

### 4. Chat statistikasini olish

**Endpoint:** `GET /api/chat/stats/{project_id}/`

**Tavsif:** Project uchun chat statistikasini ko'rish.

**Response:**
```json
{
  "total_users": 100,
  "total_messages": 5000,
  "unread_messages": 250,
  "read_messages": 4750
}
```

**Misol:**
```bash
curl -X GET "http://localhost:8000/api/chat/stats/1/" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## MongoDB Collections

### users collection
Signal ichida yaratiladi (core/apps/api/signals/project.py):

**Fields:**
- `chat_id` (TEXT, required) - Telegram chat ID
- `first_name` (TEXT, required) - User ismi
- `last_name` (TEXT, optional) - User familiyasi
- `created_at` (DATETIME, required) - Yaratilgan vaqt

### chat collection
Signal ichida yaratiladi (core/apps/api/signals/project.py):

**Fields:**
- `chat_id` (TEXT, required) - Telegram chat ID
- `text` (TEXT) - Xabar matni
- `read` (BOOLEAN, optional) - Xabar o'qilganmi (default: false)

---

## Xususiyatlar

1. **Avtomatik yaratilish**: Project yaratilganda `users` va `chat` collectionlari avtomatik yaratiladi
2. **MongoDB ulanish**: MongoDB ulanish ma'lumotlari kod ichida mavjud (MongoDBClient)
3. **O'qilmagan xabarlar**: Xabar o'qilmagan deb hisoblanadi agar `read` fieldi yo'q bo'lsa yoki `false` bo'lsa
4. **Pagination**: Barcha endpointlarda `limit` va `skip` parametrlari mavjud
5. **Xavfsizlik**: Faqat project egasi o'z projectining chatlariga kirishi mumkin

---

## Ishlatish misollari

### Frontend integration (JavaScript/TypeScript)

```javascript
// Userlarni olish
async function getUsers(projectId, limit = 50, skip = 0) {
  const response = await fetch(
    `/api/chat/users/${projectId}/?limit=${limit}&skip=${skip}`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  return await response.json();
}

// Xabarlarni o'qilgan qilish
async function markAsRead(projectId, chatId, messageIds = null) {
  const response = await fetch(
    `/api/chat/mark-read/${projectId}/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        chat_id: chatId,
        message_ids: messageIds
      })
    }
  );
  return await response.json();
}

// Statistikani olish
async function getChatStats(projectId) {
  const response = await fetch(
    `/api/chat/stats/${projectId}/`,
    {
      headers: {
        'Authorization': `Bearer ${token}`
      }
    }
  );
  return await response.json();
}
```

### Python integration

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}"
}

# Userlarni olish
def get_users(project_id, limit=50, skip=0):
    url = f"{BASE_URL}/api/chat/users/{project_id}/"
    params = {"limit": limit, "skip": skip}
    response = requests.get(url, headers=headers, params=params)
    return response.json()

# Xabarlarni o'qilgan qilish
def mark_as_read(project_id, chat_id, message_ids=None):
    url = f"{BASE_URL}/api/chat/mark-read/{project_id}/"
    data = {"chat_id": chat_id}
    if message_ids:
        data["message_ids"] = message_ids
    response = requests.post(url, headers=headers, json=data)
    return response.json()
```

---

## Xatolarni qaytarish

API quyidagi HTTP status kodlarini qaytaradi:

- `200 OK` - Muvaffaqiyatli
- `400 BAD REQUEST` - Noto'g'ri so'rov (masalan, chat_id yo'q)
- `404 NOT FOUND` - Project yoki collection topilmadi
- `401 UNAUTHORIZED` - Autentifikatsiya talab qilinadi
- `403 FORBIDDEN` - Ruxsat yo'q

**Xato misoli:**
```json
{
  "error": "Collections not found for this project"
}
```
