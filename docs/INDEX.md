# 📚 BotMother API Documentation Index

BotMother backend API uchun to'liq dokumentatsiya kolleksiyasi.

---

## 📖 Dokumentatsiya fayllari

### 1. [README.md](./README.md) - Asosiy dokumentatsiya
**482 qator | 22KB**

To'liq API dokumentatsiyasi, barcha endpoint'lar, request/response formatlar va mundareja.

**Qamrab oladi:**
- ✅ Barcha API endpoint'lar
- ✅ Request va Response formatlar  
- ✅ Autentifikatsiya (register, login, confirm)
- ✅ Loyiha boshqaruvi (CRUD)
- ✅ Debug va Release
- ✅ Environment o'zgaruvchilari
- ✅ CMS Collections (MongoDB)
- ✅ Server-Sent Events (SSE)
- ✅ Xatoliklar ro'yxati
- ✅ Postman collection namunasi

**Kimga mo'ljallangan:** Frontend dasturchilar, Backend dasturchilar, QA muhandislar

---

### 2. [QUICK_START.md](./QUICK_START.md) - Tezkor boshlash
**481 qator | 10KB**

5 daqiqada API bilan ishlashni boshlash uchun qisqacha qo'llanma.

**Qamrab oladi:**
- 🚀 5 daqiqada ishga tushirish
- 📱 Minimal React integration
- 🎯 Eng ko'p ishlatiladigan endpoint'lar
- 🔧 Common issues va yechimlar
- 📦 To'liq flow misoli
- 🎨 Frontend libraries (Axios, React Query)
- 💡 Tips va FAQ

**Kimga mo'ljallangan:** Yangi boshlovchilar, Frontend dasturchilar

---

### 3. [AUTHENTICATION.md](./AUTHENTICATION.md) - Autentifikatsiya qo'llanmasi
**430 qator | 9KB**

JWT autentifikatsiya va avtorizatsiya bo'yicha batafsil qo'llanma.

**Qamrab oladi:**
- 🔐 JWT (Access & Refresh tokens)
- 🔄 Autentifikatsiya oqimlari (register, login, reset password)
- 🔑 Token bilan ishlash
- 📱 Telegram autentifikatsiya
- ✅ Best practices
- 🛡️ Security considerations
- 🚫 Rate limiting
- 🧪 Testing (Postman)

**Kimga mo'ljallangan:** Frontend dasturchilar, Security engineers

---

### 4. [EXAMPLES.md](./EXAMPLES.md) - Kod misollar
**756 qator | 18KB**

Turli dasturlash tillari va framework'larda kod misollar.

**Qamrab oladi:**
- 💻 JavaScript/TypeScript (Fetch API)
  - API client class
  - Authentication
  - Project management
  - Environment variables
  - CMS Collections
  - SSE (Server-Sent Events)
- ⚛️ React integration
  - Custom hooks
  - Component misollar
- 🐍 Python misollar
- 🔨 cURL misollar
- ❌ Error handling patterns

**Kimga mo'ljallangan:** Frontend dasturchilar (React, Vue, Angular), Backend dasturchilar (Python)

---

### 5. [POSTMAN.md](./POSTMAN.md) - Postman Collection
**882 qator | 15KB**

Postman orqali API bilan ishlash uchun to'liq qo'llanma.

**Qamrab oladi:**
- ⚙️ Environment o'rnatish
- 📁 Collection yaratish
- 📨 Barcha endpoint'lar uchun request'lar
  - Authentication (6 request)
  - Projects (7 request)
  - Environments (5 request)
  - Releases (4 request)
  - CMS Collections (8 request)
- 🧪 Tests va assertions
- 📝 Pre-request scripts
- 🔄 Automatic token refresh
- 📤 Export/Import qo'llanmasi
- 🖥️ Newman (CLI) bilan ishlash
- 💡 Tips & Tricks

**Kimga mo'ljallangan:** QA muhandislar, Backend dasturchilar, API testing

---

## 🎯 Qaysi fayldan boshlash kerak?

### Siz Frontend dasturchisiz va yangi boshlayapsiz?
👉 Boshlang: [QUICK_START.md](./QUICK_START.md)  
👉 Keyin: [README.md](./README.md)  
👉 Kod misollari: [EXAMPLES.md](./EXAMPLES.md)

### Siz Backend dasturchisiz?
👉 Boshlang: [README.md](./README.md)  
👉 Postman: [POSTMAN.md](./POSTMAN.md)

### API'ni test qilish kerak?
👉 Boshlang: [POSTMAN.md](./POSTMAN.md)  
👉 Keyin: [README.md](./README.md)

### Authentication bilan muammo?
👉 O'qing: [AUTHENTICATION.md](./AUTHENTICATION.md)

### Kod misollar kerak?
👉 O'qing: [EXAMPLES.md](./EXAMPLES.md)

---

## 📊 Statistika

| Fayl | Qatorlar | Hajmi | Mavzu |
|------|----------|-------|-------|
| README.md | 482 | 22KB | To'liq API dokumentatsiya |
| QUICK_START.md | 481 | 10KB | Tezkor qo'llanma |
| AUTHENTICATION.md | 430 | 9KB | Auth qo'llanmasi |
| EXAMPLES.md | 756 | 18KB | Kod misollar |
| POSTMAN.md | 882 | 15KB | Postman collection |
| **JAMI** | **3,984** | **84KB** | **5 fayl** |

---

## 🗂️ Tuzilma

```
docs/
├── INDEX.md              # Ushbu fayl - dokumentatsiya indexi
├── README.md             # Asosiy API dokumentatsiya
├── QUICK_START.md        # Tezkor boshlash qo'llanmasi
├── AUTHENTICATION.md     # Autentifikatsiya va security
├── EXAMPLES.md           # Kod misollar (JS, TS, Python, cURL)
└── POSTMAN.md           # Postman collection va testing
```

---

## 🔍 Qidirish bo'yicha indeks

### API Endpoint'lar

| Endpoint | Fayl | Bo'lim |
|----------|------|--------|
| `POST /auth/register/` | README.md | Authentication → Ro'yxatdan o'tish |
| `POST /auth/confirm/` | README.md | Authentication → Confirm |
| `POST /auth/token/` | README.md | Authentication → Login |
| `POST /auth/token/refresh/` | README.md | Authentication → Token yangilash |
| `GET /auth/me/` | README.md | Foydalanuvchi → Profil |
| `GET /api/project/` | README.md | Loyiha → Ro'yxat |
| `POST /api/project/` | README.md | Loyiha → Yaratish |
| `GET /api/project/{id}/` | README.md | Loyiha → Ma'lumotlar |
| `GET /api/project/{id}/debug/` | README.md | Loyiha → Debug |
| `GET /api/enviroment/` | README.md | Environment → Ro'yxat |
| `POST /api/enviroment/` | README.md | Environment → Yaratish |
| `GET /api/relase/` | README.md | Release → Ro'yxat |
| `POST /api/relase/` | README.md | Release → Yaratish |
| `GET /api/collection/` | README.md | CMS → Collection ro'yxat |
| `POST /api/collection/` | README.md | CMS → Collection yaratish |
| `POST /api/collection/{name}/query/` | README.md | CMS → Query operatsiyalar |
| `GET /sse/api/project/{id}/logs/` | README.md | SSE → Real-time logs |

### Kod misollar

| Texnologiya | Fayl | Misol |
|-------------|------|-------|
| JavaScript/TypeScript | EXAMPLES.md | API client class |
| React | EXAMPLES.md | Hooks, Components |
| Python | EXAMPLES.md | Requests library |
| cURL | EXAMPLES.md | Command line |
| Axios | QUICK_START.md | Interceptors |
| React Query | QUICK_START.md | useQuery, useMutation |
| SSE/EventSource | EXAMPLES.md | Real-time logs |

### Mavzular

| Mavzu | Fayl |
|-------|------|
| JWT Authentication | AUTHENTICATION.md |
| Token refresh | AUTHENTICATION.md |
| Password reset | README.md, AUTHENTICATION.md |
| Project CRUD | README.md, EXAMPLES.md |
| Debug mode | README.md, QUICK_START.md |
| Environment variables | README.md, EXAMPLES.md |
| CMS Collections | README.md, EXAMPLES.md |
| MongoDB queries | README.md |
| Server-Sent Events | README.md, EXAMPLES.md |
| Error handling | README.md, EXAMPLES.md |
| Rate limiting | AUTHENTICATION.md |
| Security | AUTHENTICATION.md |
| Postman setup | POSTMAN.md |
| Testing | POSTMAN.md |

---

## 🔄 Yangilanish tarixi

| Sana | Versiya | O'zgarishlar |
|------|---------|--------------|
| 2024-11-03 | 1.0.0 | Dastlabki versiya yaratildi |

---

## 📝 Hissa qo'shish

Dokumentatsiyada xato topsangiz yoki qo'shimcha taklif bo'lsa:

1. Issue oching GitHub'da
2. Pull request yuboring
3. Telegram guruhda yozing

---

## 📞 Aloqa

- **Email:** support@botmother.com
- **Telegram:** @botmother_support
- **GitHub:** github.com/botmother/backend

---

## 📄 Litsenziya

© 2024 BotMother Team. Barcha huquqlar himoyalangan.

---

**Yaxshi kodlash! 🚀**
