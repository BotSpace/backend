# Chat API Swagger Documentation

## drf-spectacular bilan Swagger yaratildi

### Qo'shilgan fayllar:

1. **core/apps/api/serializers/chat.py** - Swagger uchun serializers
2. **core/apps/api/views/chat.py** - `@extend_schema` decorator qo'shildi

### Serializers:

- `UserSerializer` - User ma'lumotlari
- `MessageSerializer` - Chat xabari
- `UserWithMessagesSerializer` - User va xabarlari
- `UsersListResponseSerializer` - Userlar ro'yxati response
- `MessagesListResponseSerializer` - Xabarlar ro'yxati response
- `MarkAsReadRequestSerializer` - O'qilgan qilish request
- `MarkAsReadResponseSerializer` - O'qilgan qilish response
- `ChatStatsResponseSerializer` - Statistika response
- `ErrorResponseSerializer` - Xato response

### Swagger Examples:

#### 1. GET /api/chat/users/{project_id}/

**Query Parameters:**
- `limit` (integer, optional) - default: 50
- `skip` (integer, optional) - default: 0

**Response 200:**
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
          "text": "Salom! Qanday yordam bera olaman?",
          "read": false
        },
        {
          "_id": "507f191e810c19729de860eb",
          "chat_id": "123456789",
          "text": "Botingiz juda zo'r!",
          "read": true
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

#### 2. GET /api/chat/messages/{project_id}/{chat_id}/

**Path Parameters:**
- `project_id` (integer, required)
- `chat_id` (string, required)

**Query Parameters:**
- `limit` (integer, optional) - default: 50
- `skip` (integer, optional) - default: 0

**Response 200:**
```json
{
  "messages": [
    {
      "_id": "507f191e810c19729de860ea",
      "chat_id": "123456789",
      "text": "Salom!",
      "read": false
    },
    {
      "_id": "507f191e810c19729de860eb",
      "chat_id": "123456789",
      "text": "Yordam kerakmi?",
      "read": true
    }
  ],
  "total": 150,
  "limit": 50,
  "skip": 0
}
```

#### 3. POST /api/chat/mark-read/{project_id}/

**Path Parameters:**
- `project_id` (integer, required)

**Request Body Example 1** (Ma'lum xabarlarni o'qilgan qilish):
```json
{
  "chat_id": "123456789",
  "message_ids": ["507f191e810c19729de860ea", "507f191e810c19729de860eb"]
}
```

**Request Body Example 2** (Barcha xabarlarni o'qilgan qilish):
```json
{
  "chat_id": "123456789"
}
```

**Response 200:**
```json
{
  "success": true,
  "modified_count": 2
}
```

**Response 400** (Xato):
```json
{
  "error": "chat_id is required"
}
```

#### 4. GET /api/chat/stats/{project_id}/

**Path Parameters:**
- `project_id` (integer, required)

**Response 200:**
```json
{
  "total_users": 100,
  "total_messages": 5000,
  "unread_messages": 250,
  "read_messages": 4750
}
```

**Response 404** (Xato):
```json
{
  "error": "Collections not found"
}
```

## Swagger UI ga kirish:

Swagger UI endpointlari (odatiy sozlamalar):

1. **Swagger UI**: `http://localhost:8000/api/schema/swagger-ui/`
2. **ReDoc**: `http://localhost:8000/api/schema/redoc/`
3. **OpenAPI Schema (JSON)**: `http://localhost:8000/api/schema/`
4. **OpenAPI Schema (YAML)**: `http://localhost:8000/api/schema/?format=openapi`

## Postman/Insomnia Collection:

OpenAPI schema ni export qilib, Postman yoki Insomnia ga import qilish mumkin:

```bash
# OpenAPI schema yuklab olish
curl http://localhost:8000/api/schema/ -o openapi.json

# Yoki YAML formatda
curl http://localhost:8000/api/schema/?format=openapi -o openapi.yaml
```

## cURL Misollar:

### 1. Userlarni olish
```bash
curl -X GET "http://localhost:8000/api/chat/users/1/?limit=20&skip=0" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json"
```

### 2. User xabarlarini olish
```bash
curl -X GET "http://localhost:8000/api/chat/messages/1/123456789/?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json"
```

### 3. Xabarlarni o'qilgan qilish
```bash
curl -X POST "http://localhost:8000/api/chat/mark-read/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "123456789",
    "message_ids": ["507f191e810c19729de860ea"]
  }'
```

### 4. Statistika olish
```bash
curl -X GET "http://localhost:8000/api/chat/stats/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Accept: application/json"
```

## Python Requests Misollar:

```python
import requests

BASE_URL = "http://localhost:8000"
TOKEN = "your_token_here"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

# 1. Userlarni olish
response = requests.get(
    f"{BASE_URL}/api/chat/users/1/",
    params={"limit": 20, "skip": 0},
    headers=headers
)
print(response.json())

# 2. Xabarlarni o'qilgan qilish
response = requests.post(
    f"{BASE_URL}/api/chat/mark-read/1/",
    json={
        "chat_id": "123456789",
        "message_ids": ["507f191e810c19729de860ea"]
    },
    headers=headers
)
print(response.json())
```

## JavaScript/TypeScript Misollar:

```typescript
const BASE_URL = 'http://localhost:8000';
const TOKEN = 'your_token_here';

// 1. Userlarni olish
async function getUsers(projectId: number, limit = 50, skip = 0) {
  const response = await fetch(
    `${BASE_URL}/api/chat/users/${projectId}/?limit=${limit}&skip=${skip}`,
    {
      headers: {
        'Authorization': `Bearer ${TOKEN}`,
        'Accept': 'application/json'
      }
    }
  );
  return await response.json();
}

// 2. Xabarlarni o'qilgan qilish
async function markAsRead(projectId: number, chatId: string, messageIds?: string[]) {
  const response = await fetch(
    `${BASE_URL}/api/chat/mark-read/${projectId}/`,
    {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${TOKEN}`,
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
```

## Swagger Tags:

Barcha chat endpointlari `chat` tag ichida:

```python
@extend_schema(tags=["chat"])
class ChatViewSet(ViewSet):
    ...
```

Bu Swagger UI da endpointlarni guruhlab ko'rsatadi.

## Schema Features:

✅ **Summary va Description** - Har bir endpoint uchun
✅ **Parameters** - Path, Query, Body parametrlar
✅ **Request Examples** - Turli xil request misollari
✅ **Response Examples** - Success va error responslar
✅ **Response Codes** - 200, 400, 404 va boshqalar
✅ **Field Descriptions** - Har bir field uchun izoh
✅ **Required/Optional** - Qaysi fieldlar majburiy
✅ **Default Values** - Default qiymatlar
✅ **Help Text** - Qo'shimcha tushuntirishlar

## Test qilish:

Swagger UI ochib, "Try it out" tugmasini bosib, to'g'ridan-to'g'ri brauzerda test qilish mumkin!
