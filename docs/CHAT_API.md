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

### 3. Foydalanuvchiga xabar yuborish (YANGI ⭐)

**Endpoint:** `POST /api/chat/send-message/{project_id}/`

**Tavsif:** Bitta foydalanuvchiga xabar yuborish. Yuborilgan xabar avtomatik ravishda chatga qo'shiladi va real-time stream orqali boshqa clientlarga yuboriladi.

**Media yuborish qo'llab-quvvatlanadi:**
- Photo: max 10MB
- Video: max 50MB  
- Audio: max 50MB
- Document: max 50MB

**Telegram API rate limits:**
- 1 bot uchun 30 xabar/soniya
- 1 chat uchun 1 xabar/soniya
- Rate limitlar avtomatik kuzatiladi va Celery task orqali boshqariladi

**Request Body (JSON yoki multipart/form-data):**

Text xabar yuborish:
```json
{
  "chat_id": "123456789",
  "text": "Assalomu alaykum! Sizga qanday yordam bera olaman?"
}
```

Photo yuborish:
```bash
# cURL multipart/form-data
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "chat_id=123456789" \
  -F "text=Bu rasm caption" \
  -F "file_type=photo" \
  -F "file=@/path/to/photo.jpg"
```

Video yuborish:
```bash
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "chat_id=123456789" \
  -F "text=Bu video caption" \
  -F "file_type=video" \
  -F "file=@/path/to/video.mp4"
```

**Response:**
```json
{
  "success": true,
  "message_id": "507f191e810c19729de860ea",
  "telegram_sent": true,
  "message": {
    "_id": "507f191e810c19729de860ea",
    "chat_id": "123456789",
    "text": "Assalomu alaykum! Sizga qanday yordam bera olaman?",
    "read": false,
    "from_admin": true,
    "created_at": "2024-12-04T10:35:00Z",
    "file_type": "photo",
    "file_url": "/media/chat/1/123456789/1701684900.123.jpg",
    "file_name": "photo.jpg",
    "file_size": 1048576
  }
}
```

**Misol:**

Text xabar:
```bash
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "123456789",
    "text": "Salom! Qanday yordam kerak?"
  }'
```

Photo yuborish:
```bash
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "chat_id=123456789" \
  -F "text=Rasmni ko'ring" \
  -F "file_type=photo" \
  -F "file=@image.jpg"
```

Video yuborish:
```bash
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "chat_id=123456789" \
  -F "text=Video caption" \
  -F "file_type=video" \
  -F "file=@video.mp4"
```

Document yuborish:
```bash
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "chat_id=123456789" \
  -F "text=Document" \
  -F "file_type=document" \
  -F "file=@document.pdf"
```

**Errors:**
- `400` - chat_id berilmagan yoki text va file ikkalasi ham yo'q
- `413` - File hajmi limitdan oshgan
- `404` - Chat collection topilmadi
- `500` - Server xatosi

---

### 4. Xabarlarni o'qilgan deb belgilash

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

### 5. Chat statistikasini olish

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
- `from_admin` (BOOLEAN, optional) - Admin tomonidan yuborilganmi (default: false)
- `created_at` (DATETIME, optional) - Xabar yuborilgan vaqt

---

## Real-time Chat Implementatsiyasi

Frontend dan yangi xabarlarni olish uchun polling yoki WebSocket ishlatish mumkin.

### Polling misol (React)

```jsx
import { useEffect, useState, useRef } from 'react';

function ChatComponent({ projectId, chatId, token }) {
  const [messages, setMessages] = useState([]);
  const [messageText, setMessageText] = useState('');
  const pollIntervalRef = useRef(null);

  // Polling - har 2 soniyada yangi xabarlarni tekshirish
  useEffect(() => {
    const fetchMessages = async () => {
      try {
        const response = await fetch(
          `/api/chat/messages/${projectId}/${chatId}/?limit=50`,
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        );
        
        if (response.ok) {
          const data = await response.json();
          setMessages(data.messages || []);
        }
      } catch (error) {
        console.error('Fetch error:', error);
      }
    };

    // Initial fetch
    fetchMessages();

    // Poll every 2 seconds
    pollIntervalRef.current = setInterval(fetchMessages, 2000);

    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, [projectId, chatId, token]);

  // Xabar yuborish
  const sendMessage = async () => {
    if (!messageText.trim()) return;

    try {
      const response = await fetch(`/api/chat/send-message/${projectId}/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          chat_id: chatId,
          text: messageText
        })
      });

      if (response.ok) {
        setMessageText('');
      }
    } catch (error) {
      console.error('Send error:', error);
    }
  };

  // File yuborish
  const sendFile = async (file, fileType, caption = '') => {
    const formData = new FormData();
    formData.append('chat_id', chatId);
    formData.append('file', file);
    formData.append('file_type', fileType);
    if (caption) {
      formData.append('text', caption);
    }

    try {
      const response = await fetch(`/api/chat/send-message/${projectId}/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`
          // Content-Type ni set qilmang, browser avtomatik multipart/form-data qo'yadi
        },
        body: formData
      });

      if (response.ok) {
        console.log('File sent successfully');
      }
    } catch (error) {
      console.error('File send error:', error);
    }
  };

  // File input handler
  const handleFileSelect = (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // File turini aniqlash
    let fileType = 'document';
    if (file.type.startsWith('image/')) {
      fileType = 'photo';
    } else if (file.type.startsWith('video/')) {
      fileType = 'video';
    } else if (file.type.startsWith('audio/')) {
      fileType = 'audio';
    }

    // File hajmini tekshirish
    const maxSize = fileType === 'photo' ? 10 : 50; // MB
    if (file.size > maxSize * 1024 * 1024) {
      alert(`File hajmi ${maxSize}MB dan kichik bo'lishi kerak`);
      return;
    }

    sendFile(file, fileType);
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map(msg => (
          <div 
            key={msg._id} 
            className={msg.from_admin ? 'message admin' : 'message user'}
          >
            <div className="message-text">{msg.text}</div>
            <div className="message-time">
              {new Date(msg.created_at).toLocaleTimeString()}
            </div>
          </div>
        ))}
      </div>
      
      <div className="input-area">
        <input 
          value={messageText}
          onChange={(e) => setMessageText(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && sendMessage()}
          placeholder="Xabar yozish..."
        />
        <button onClick={sendMessage}>Yuborish</button>
        
        <input
          type="file"
          accept="image/*,video/*,audio/*,.pdf,.doc,.docx"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
          id="file-input"
        />
        <label htmlFor="file-input">
          <button onClick={() => document.getElementById('file-input').click()}>
            📎 File
          </button>
        </label>
      </div>
    </div>
  );
}
```

### Vue.js misol (Polling)

```vue
<template>
  <div class="chat-container">
    <div class="messages">
      <div 
        v-for="msg in messages" 
        :key="msg._id"
        :class="['message', msg.from_admin ? 'admin' : 'user']"
      >
        <div class="message-text">{{ msg.text }}</div>
        <div class="message-time">
          {{ formatTime(msg.created_at) }}
        </div>
      </div>
    </div>
    
    <div class="input-area">
      <input 
        v-model="messageText"
        @keypress.enter="sendMessage"
        placeholder="Xabar yozish..."
      />
      <button @click="sendMessage">Yuborish</button>
    </div>
  </div>
</template>

<script>
export default {
  props: ['projectId', 'chatId', 'token'],
  data() {
    return {
      messages: [],
      messageText: '',
      pollInterval: null
    };
  },
  mounted() {
    this.startPolling();
  },
  beforeUnmount() {
    this.stopPolling();
  },
  methods: {
    startPolling() {
      // Initial fetch
      this.fetchMessages();
      
      // Poll every 2 seconds
      this.pollInterval = setInterval(() => {
        this.fetchMessages();
      }, 2000);
    },
    stopPolling() {
      if (this.pollInterval) {
        clearInterval(this.pollInterval);
      }
    },
    async fetchMessages() {
      try {
        const response = await fetch(
          `/api/chat/messages/${this.projectId}/${this.chatId}/?limit=50`,
          {
            headers: {
              'Authorization': `Bearer ${this.token}`
            }
          }
        );
        
        if (response.ok) {
          const data = await response.json();
          this.messages = data.messages || [];
        }
      } catch (error) {
        console.error('Fetch error:', error);
      }
    },
    async sendMessage() {
      if (!this.messageText.trim()) return;

      try {
        const response = await fetch(`/api/chat/send-message/${this.projectId}/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${this.token}`
          },
          body: JSON.stringify({
            chat_id: this.chatId,
            text: this.messageText
          })
        });

        if (response.ok) {
          this.messageText = '';
        }
      } catch (error) {
        console.error('Send error:', error);
      }
    },
    formatTime(timestamp) {
      return new Date(timestamp).toLocaleTimeString();
    }
  }
};
</script>
```

---

## Xususiyatlar

1. **Avtomatik yaratilish**: Project yaratilganda `users` va `chat` collectionlari avtomatik yaratiladi
2. **MongoDB ulanish**: MongoDB ulanish ma'lumotlari kod ichida mavjud (MongoDBClient)
3. **O'qilmagan xabarlar**: Xabar o'qilmagan deb hisoblanadi agar `read` fieldi yo'q bo'lsa yoki `false` bo'lsa
4. **Pagination**: Barcha endpointlarda `limit` va `skip` parametrlari mavjud
5. **Xavfsizlik**: Faqat project egasi o'z projectining chatlariga kirishi mumkin
6. **Admin vs User**: `from_admin` field orqali xabar admin yoki user tomonidan yuborilganmi farqlanadi ⭐
7. **Media support**: Photo, video, audio, document yuborish qo'llab-quvvatlanadi ⭐
8. **Rate limiting**: Telegram API limitlari avtomatik boshqariladi ⭐
9. **Polling**: Yangi xabarlarni olish uchun polling ishlatish tavsiya etiladi (2 soniya interval)

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
