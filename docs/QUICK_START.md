# Tezkor Boshlash

BotMother API bilan ishlashni boshlash uchun eng muhim endpoint'lar va misollar.

---

## 🚀 5 daqiqada ishga tushiring

### 1. Register va Login (2 minut)

```bash
# 1. Ro'yxatdan o'tish - SMS yuborish
curl -X POST http://localhost:8081/auth/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+998901234567",
    "first_name": "Ism",
    "last_name": "Familiya",
    "password": "qwerty123"
  }'

# 2. SMS kodni tasdiqlash
curl -X POST http://localhost:8081/auth/confirm/ \
  -H "Content-Type: application/json" \
  -d '{
    "phone": "+998901234567",
    "code": "1234"
  }'

# Response:
# {
#   "detail": "Tasdiqlash ko'di qabul qilindi",
#   "token": {
#     "access": "your-access-token",
#     "refresh": "your-refresh-token"
#   }
# }
```

**Eslatma:** `access_token`ni saqlang, keyingi so'rovlar uchun kerak bo'ladi!

---

### 2. Birinchi botni yaratish (1 minut)

```bash
# Loyiha yaratish
curl -X POST http://localhost:8081/api/project/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Mening birinchi botim",
    "flow": {
      "nodes": [],
      "edges": []
    }
  }'

# Response:
# {
#   "id": 1,
#   "name": "Mening birinchi botim",
#   "flow": {...}
# }
```

Project ID'ni saqlang! (masalan: `1`)

---

### 3. Bot token qo'shish (1 minut)

```bash
# BOT_TOKEN environment o'zgaruvchisini yaratish
curl -X POST "http://localhost:8081/api/enviroment/?project=1" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "project": 1,
    "key": "BOT_TOKEN",
    "value": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
  }'
```

Bot tokenni [@BotFather](https://t.me/botfather) dan oling.

---

### 4. Debug mode (1 minut)

```bash
# Debug rejimini ishga tushirish
curl -X GET http://localhost:8081/api/project/1/debug/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Debug holati
curl -X GET http://localhost:8081/api/project/1/info/ \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"

# Response:
# {
#   "id": 1,
#   "status": "running",
#   "service_id": "bot_1_debug"
# }
```

---

## 📱 Frontend Integration (React)

### Minimal misol

```typescript
import { useState } from 'react';

const API_URL = 'http://localhost:8081';

function App() {
  const [token, setToken] = useState('');
  const [projects, setProjects] = useState([]);

  // Login
  async function login(phone: string, password: string) {
    const response = await fetch(`${API_URL}/auth/token/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ phone, password }),
    });
    const data = await response.json();
    setToken(data.access);
    localStorage.setItem('token', data.access);
  }

  // Get projects
  async function getProjects() {
    const response = await fetch(`${API_URL}/api/project/`, {
      headers: { 
        'Authorization': `Bearer ${token}` 
      },
    });
    const data = await response.json();
    setProjects(data);
  }

  return <div>Your app...</div>;
}
```

---

## 🎯 Eng ko'p ishlatiladigan endpoint'lar

### Authentication

```bash
# Login
POST /auth/token/
Body: {"phone": "+998...", "password": "..."}

# Get user info
GET /auth/me/
Header: Authorization: Bearer {token}

# Refresh token
POST /auth/token/refresh/
Body: {"refresh": "..."}
```

---

### Projects

```bash
# List projects
GET /api/project/

# Create project
POST /api/project/
Body: {"name": "...", "flow": {...}}

# Get project
GET /api/project/{id}/

# Update flow
PATCH /api/project/{id}/
Body: {"flow": {...}}

# Start debug
GET /api/project/{id}/debug/

# Stop debug
GET /api/project/{id}/stop/
```

---

### Environment Variables

```bash
# List
GET /api/enviroment/?project={id}

# Create
POST /api/enviroment/?project={id}
Body: {"project": 1, "key": "...", "value": "..."}

# Delete
DELETE /api/enviroment/{key}/?project={id}
```

---

### CMS Collections

```bash
# Create collection
POST /api/collection/?project={id}
Body: {
  "name": "users",
  "project": 1,
  "fields": [...]
}

# Insert data
POST /api/collection/{name}/query/?action=insert&project={id}
Body: {"field1": "value1", ...}

# Find data
POST /api/collection/{name}/query/?action=find&project={id}
Body: {"where": {...}, "limit": 10}

# Update data
POST /api/collection/{name}/query/?action=update&project={id}
Body: {"where": {...}, "data": {"$set": {...}}}

# Delete data
POST /api/collection/{name}/query/?action=delete&project={id}
Body: {"where": {...}}
```

---

## 🔧 Common Issues

### 1. Token expired (401)

```javascript
// Refresh token
const response = await fetch('/auth/token/refresh/', {
  method: 'POST',
  body: JSON.stringify({ 
    refresh: localStorage.getItem('refresh_token') 
  })
});
const data = await response.json();
localStorage.setItem('token', data.access);
```

---

### 2. CORS xatolari

Backend `.env` faylida:
```env
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

---

### 3. Debug ishlamayapti

Environment variables tekshiring:
```bash
# BOT_TOKEN borligini tekshirish
curl -X GET "http://localhost:8081/api/enviroment/?project=1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## 📦 To'liq flow misoli

```typescript
// 1. Login
const loginRes = await fetch('/auth/token/', {
  method: 'POST',
  body: JSON.stringify({
    phone: '+998901234567',
    password: 'qwerty123'
  })
});
const { access, refresh } = await loginRes.json();

// 2. Create project
const projectRes = await fetch('/api/project/', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    name: 'My Bot',
    flow: { nodes: [], edges: [] }
  })
});
const project = await projectRes.json();

// 3. Add bot token
await fetch(`/api/enviroment/?project=${project.id}`, {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${access}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    project: project.id,
    key: 'BOT_TOKEN',
    value: 'YOUR_BOT_TOKEN'
  })
});

// 4. Start debug
await fetch(`/api/project/${project.id}/debug/`, {
  headers: {
    'Authorization': `Bearer ${access}`
  }
});

// 5. Watch logs (SSE)
const eventSource = new EventSource(
  `/sse/api/project/bot_${project.id}_debug/logs/`
);
eventSource.onmessage = (e) => console.log('Log:', e.data);
```

---

## 🎨 Frontend Libraries

### Axios bilan

```bash
npm install axios
```

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8081',
});

// Interceptor - token qo'shish
api.interceptors.request.use(config => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Ishlatish
const projects = await api.get('/api/project/');
const newProject = await api.post('/api/project/', {
  name: 'My Bot',
  flow: { nodes: [], edges: [] }
});
```

---

### React Query bilan

```bash
npm install @tanstack/react-query
```

```typescript
import { useQuery, useMutation } from '@tanstack/react-query';

function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: async () => {
      const response = await fetch('/api/project/', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });
      return response.json();
    }
  });
}

function useCreateProject() {
  return useMutation({
    mutationFn: async (data) => {
      const response = await fetch('/api/project/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(data)
      });
      return response.json();
    }
  });
}

// Component
function Projects() {
  const { data: projects } = useProjects();
  const createProject = useCreateProject();

  return (
    <div>
      {projects?.map(p => <div key={p.id}>{p.name}</div>)}
      <button onClick={() => createProject.mutate({ 
        name: 'New Bot',
        flow: { nodes: [], edges: [] }
      })}>
        Create
      </button>
    </div>
  );
}
```

---

## 📚 Keyingi qadamlar

1. [To'liq dokumentatsiya](./README.md) - barcha endpoint'lar
2. [Authentication guide](./AUTHENTICATION.md) - autentifikatsiya to'liq qo'llanmasi
3. [Code examples](./EXAMPLES.md) - ko'proq misollar
4. [Postman collection](./POSTMAN.md) - Postman setup

---

## 💡 Tips

1. **Token'ni doim saqlang:** `localStorage` yoki `sessionStorage`da
2. **Environment variables:** Debug uchun kamida `BOT_TOKEN` kerak
3. **Error handling:** Har doim 401 va 403 xatoliklarni handle qiling
4. **SSE:** Real-time loglar uchun EventSource API ishlatiladi
5. **Rate limiting:** Auth endpoint'larga limit bor, ko'p marta urinmang

---

## ❓ FAQ

**Q: Token muddati qancha?**  
A: Access token - 1 soat, Refresh token - 7 kun

**Q: Debug uchun nima kerak?**  
A: Kamida `BOT_TOKEN` environment variable

**Q: CMS nima uchun?**  
A: Bot uchun ma'lumotlar bazasi (foydalanuvchilar, mahsulotlar va h.k.)

**Q: Release va Debug farqi?**  
A: Debug - test uchun, Release - production uchun

**Q: Bir nechta bot bo'lishi mumkinmi?**  
A: Ha, har bir loyiha alohida bot

---

## 🆘 Yordam

Muammo bo'lsa:
1. Console'dagi xatolarni tekshiring
2. Network tab'da request/response ko'ring
3. Token to'g'ri yuborilayotganini tekshiring
4. Backend logs'ni ko'ring: `docker compose logs -f web`

---

**Ready to build? Let's go! 🚀**
