# Chat API - Yangilanishlar

## ⭐ Yangi funksiyalar qo'shildi

### 1. Xabar yuborish (Send Message)
- **Endpoint:** `POST /api/chat/send-message/{project_id}/`
- Text xabar yuborish
- Media yuborish (photo, video, audio, document)
- Telegram Bot API rate limiting
- Celery background tasks

---

## 📋 Qisqa ko'rsatma

### Xabar yuborish:
```bash
# Text
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"chat_id": "123456789", "message": "Salom!"}'

# Photo
curl -X POST "http://localhost:8000/api/chat/send-message/1/" \
  -H "Authorization: Bearer TOKEN" \
  -F "chat_id=123456789" \
  -F "file_type=photo" \
  -F "file=@image.jpg"
```

### Polling yangi xabarlar:
```bash
# Har 2 soniyada chaqirish
curl "http://localhost:8000/api/chat/messages/1/123456789/?limit=50" \
  -H "Authorization: Bearer TOKEN"
```

---

## 🐳 Docker Testing

```bash
# Container ichiga kirish
docker-compose exec web bash

# Testlar
python -m pytest core/apps/api/tests/test_chat_api.py -v

# Coverage
python -m pytest --cov=core/apps/api/views/chat
```

---

## 📚 Dokumentatsiya

- [Chat API to'liq](./CHAT_API.md)
- [Summary](./CHAT_API_SUMMARY.md)
- [Docker Testing](./TESTING_DOCKER.md)

---

## 🚀 Asosiy xususiyatlar

✅ Text va media xabar yuborish  
✅ Telegram Bot API integration  
✅ Rate limiting (30/sec bot, 1/sec chat)  
✅ File size validation  
✅ Celery background tasks  
✅ Polling API endpoints  
✅ Tests va documentation  

---

## 📊 Telegram API Limitlar

| Type | Limit |
|------|-------|
| Photo | 10MB |
| Video | 50MB |
| Audio | 50MB |
| Document | 50MB |
| Messages/sec (bot) | 30 |
| Messages/sec (chat) | 1 |

---

## 📁 Yangi fayllar

```
core/apps/api/
├── tasks/chat.py              # ⭐ YANGI - Celery tasks
├── views/chat.py              # Yangilangan - send_message, stream
├── serializers/chat.py        # Yangilangan - media support
└── tests/test_chat_api.py     # Yangilangan - media tests

docs/
├── CHAT_API.md                # Yangilangan
├── CHAT_API_SUMMARY.md        # ⭐ YANGI
└── TESTING_DOCKER.md          # ⭐ YANGI
```
