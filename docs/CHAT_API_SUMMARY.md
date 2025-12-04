# Chat API - Yangi funksiyalar

## Qo'shilgan yangi funksiyalar

### 1. Xabar yuborish (Send Message)

**Endpoint:** `POST /api/chat/send-message/{project_id}/`

Foydalanuvchiga xabar yuborish (text va media):
- Text xabar yuborish
- Photo yuborish (max 10MB)
- Video yuborish (max 50MB)
- Audio yuborish (max 50MB)
- Document yuborish (max 50MB)

**Xususiyatlar:**
- MongoDB ga avtomatik saqlash
- Real-time stream orqali boshqa clientlarga yuborish
- Telegram Bot API orqali yuborish (optional)
- Rate limiting (30 msg/sec per bot, 1 msg/sec per chat)
- Celery task orqali background yuborish

---

### 2. Real-time Stream (SSE)

**Endpoint:** `GET /api/chat/stream/{project_id}/`

Server-Sent Events orqali real-time xabarlarni olish:
- MongoDB Change Streams qo'llab-quvvatlansa, real-time
- Aks holda polling (1 soniya interval)
- Heartbeat har 30 soniyada
- Connection status monitoring

**Ishlatish:**
```javascript
const eventSource = new EventSource('/api/chat/stream/1/?chat_id=123456789');

eventSource.addEventListener('new_message', (event) => {
  const data = JSON.parse(event.data);
  console.log('New message:', data.message);
});
```

---

## Fayllar tuzilishi

```
core/apps/api/
├── views/
│   └── chat.py                    # ChatViewSet (yangilangan)
│       ├── get_users_with_messages
│       ├── get_user_messages
│       ├── mark_messages_as_read
│       ├── get_chat_stats
│       └── send_message           # ⭐ YANGI
│
├── serializers/
│   └── chat.py                    # Serializers (yangilangan)
│       ├── MessageSerializer      # File fieldlar qo'shildi
│       ├── SendMessageRequestSerializer   # ⭐ YANGI
│       └── SendMessageResponseSerializer  # ⭐ YANGI
│
├── tasks/
│   └── chat.py                    # ⭐ YANGI Celery tasks
│       ├── send_telegram_message  # Rate limiting bilan
│       ├── check_rate_limit       # Rate limit checker
│       ├── send_text_message      # Text yuborish
│       └── send_media_message     # Media yuborish
│
└── tests/
    └── test_chat_api.py           # Tests (yangilangan)
        ├── test_send_message      # ⭐ YANGI
        └── test_send_message_missing_params  # ⭐ YANGI
```

---

## Telegram Bot API Rate Limiting

### Limitlar:
- **Bot uchun:** 30 xabar/soniya (global)
- **Chat uchun:** 1 xabar/soniya (per user)

### Implementatsiya:
- Redis cache orqali rate limit tracking
- Celery task retry mechanism
- Automatic queuing va delay

### Kod misoli:
```python
# Rate limit checker
def check_rate_limit(bot_token, chat_id):
    # Check per-bot rate limit (30 msg/sec)
    # Check per-chat rate limit (1 msg/sec)
    # Update counters in Redis cache
    return True/False

# Celery task
@shared_task(bind=True, max_retries=3)
def send_telegram_message(self, bot_token, chat_id, text, file_path, file_type):
    if not check_rate_limit(bot_token, chat_id):
        raise self.retry(countdown=1)  # Retry after 1 second
    # Send message
```

---

## Media File Handling

### File storage:
- Django default storage (local yoki S3)
- Path: `media/chat/{project_id}/{chat_id}/{timestamp}.{ext}`
- URL: `/media/chat/...` yoki S3 URL

### File validation:
- File type check
- File size check
- Telegram API limits

### MongoDB document:
```json
{
  "_id": "507f191e810c19729de860ea",
  "chat_id": "123456789",
  "text": "Caption",
  "from_admin": true,
  "file_type": "photo",
  "file_path": "chat/1/123456789/1701684900.123.jpg",
  "file_url": "/media/chat/1/123456789/1701684900.123.jpg",
  "file_name": "photo.jpg",
  "file_size": 1048576,
  "created_at": "2024-12-04T10:35:00Z"
}
```

---

## Docker Testing

### Container ichiga kirish:
```bash
docker-compose exec web bash
```

### Testlarni ishga tushirish:
```bash
# Barcha testlar
python -m pytest

# Faqat chat testlar
python -m pytest core/apps/api/tests/test_chat_api.py -v

# Bitta test
python -m pytest core/apps/api/tests/test_chat_api.py::TestChatAPI::test_send_message -v

# Coverage bilan
python -m pytest --cov=core/apps/api/views/chat --cov-report=html
```

### Containerdan tashqarida:
```bash
docker-compose exec web python -m pytest core/apps/api/tests/test_chat_api.py -v
```

---

## API Usage Examples

### 1. Text xabar yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "chat_id": "123456789",
    "text": "Salom!"
  }'
```

### 2. Photo yuborish

```bash
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "chat_id=123456789" \
  -F "text=Rasm" \
  -F "file_type=photo" \
  -F "file=@image.jpg"
```

### 3. Real-time stream

```bash
curl -N -H "Authorization: Bearer YOUR_TOKEN" \
  "http://localhost:8000/api/chat/stream/1/?chat_id=123456789"
```

### 4. JavaScript (React)

```jsx
// Xabar yuborish
const sendMessage = async (text) => {
  const response = await fetch('/api/chat/send-message/1/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`
    },
    body: JSON.stringify({ chat_id: '123456789', text })
  });
  return await response.json();
};

// File yuborish
const sendFile = async (file, fileType) => {
  const formData = new FormData();
  formData.append('chat_id', '123456789');
  formData.append('file', file);
  formData.append('file_type', fileType);
  
  const response = await fetch('/api/chat/send-message/1/', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
  });
  return await response.json();
};

// Polling yangi xabarlar
setInterval(async () => {
  const response = await fetch('/api/chat/messages/1/123456789/', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await response.json();
  console.log('Messages:', data.messages);
}, 2000);
```

---

## Environment Variables

```env
# Telegram Bot (optional - agar bot orqali yuborish kerak bo'lsa)
# TELEGRAM_BOT_TOKEN=your_bot_token_here

# Celery (required for background tasks)
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# File storage (optional - default local storage)
# AWS_ACCESS_KEY_ID=your_key
# AWS_SECRET_ACCESS_KEY=your_secret
# AWS_STORAGE_BUCKET_NAME=your_bucket
```

---

## Xavfsizlik

1. **Authentication:** IsAuthenticated permission
2. **Authorization:** Faqat project egasi kirishi mumkin
3. **File validation:** File type va size check
4. **Rate limiting:** Telegram API limitlari
5. **MongoDB injection:** PyMongo avtomatik sanitize qiladi

---

## Performance

### Real-time stream:
- MongoDB Change Streams: instant delivery
- Polling fallback: 1 second delay
- Heartbeat: 30 seconds

### Rate limiting:
- Redis cache: <1ms lookup
- Celery retry: automatic
- Queue depth monitoring

### File storage:
- Local: instant
- S3: background upload (optional)
- CDN: optional

---

## Monitoring

### Logs:
```python
logger.info(f"Message sent to chat {chat_id}")
logger.warning(f"Rate limit reached: {len(messages)} msg/sec")
logger.error(f"Failed to send: {error}")
```

### Metrics:
- Messages sent per minute
- Rate limit hits
- Failed deliveries
- Average response time

---

## Kelajakdagi yaxshilashlar

1. **Typing indicator:** User yozayotganini ko'rsatish
2. **Read receipts:** Xabar o'qilganini ko'rsatish
3. **Message reactions:** Emoji reactions
4. **Message editing:** Xabarni tahrirlash
5. **Message deletion:** Xabarni o'chirish
6. **Voice messages:** Ovozli xabar
7. **Location sharing:** Joylashuv yuborish
8. **Contact sharing:** Kontakt yuborish

---

## Support

Muammolar yoki savollar bo'lsa:
- Documentation: `/docs/CHAT_API.md`
- Testing: `/docs/TESTING_DOCKER.md`
- GitHub Issues: [Link to repo]
