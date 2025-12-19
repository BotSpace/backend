# API Misollar

Bu faylda BotMother API bilan ishlashning amaliy misollari keltirilgan.

---

## JavaScript/TypeScript (Fetch API)

### 1. Ro'yxatdan o'tish va login

```typescript
// API client yaratish
class BotMotherAPI {
  private baseURL: string;
  private accessToken: string | null = null;

  constructor(baseURL: string = 'http://localhost:8081') {
    this.baseURL = baseURL;
  }

  // Register
  async register(phone: string, firstName: string, lastName: string, password: string) {
    const response = await fetch(`${this.baseURL}/auth/register/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        phone,
        first_name: firstName,
        last_name: lastName,
        password,
      }),
    });

    if (!response.ok) {
      throw new Error('Registration failed');
    }

    return await response.json();
  }

  // Confirm
  async confirm(phone: string, code: string) {
    const response = await fetch(`${this.baseURL}/auth/confirm/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ phone, code }),
    });

    if (!response.ok) {
      throw new Error('Confirmation failed');
    }

    const data = await response.json();
    this.accessToken = data.token.access;
    localStorage.setItem('access_token', data.token.access);
    localStorage.setItem('refresh_token', data.token.refresh);

    return data;
  }

  // Login
  async login(phone: string, password: string) {
    const response = await fetch(`${this.baseURL}/auth/token/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ phone, password }),
    });

    if (!response.ok) {
      throw new Error('Login failed');
    }

    const data = await response.json();
    this.accessToken = data.access;
    localStorage.setItem('access_token', data.access);
    localStorage.setItem('refresh_token', data.refresh);

    return data;
  }

  // Get headers with auth
  private getHeaders() {
    const token = this.accessToken || localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  }

  // Get current user
  async getMe() {
    const response = await fetch(`${this.baseURL}/auth/me/`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to get user info');
    }

    return await response.json();
  }
}

// Ishlatish
const api = new BotMotherAPI();

async function registerUser() {
  try {
    // 1. Register
    await api.register('+998901234567', 'John', 'Doe', 'password123');
    console.log('SMS sent!');

    // 2. Confirm (SMS kodni kiritgandan keyin)
    const result = await api.confirm('+998901234567', '1234');
    console.log('Logged in!', result);

    // 3. Get user info
    const user = await api.getMe();
    console.log('User:', user);
  } catch (error) {
    console.error('Error:', error);
  }
}
```

---

### 2. Loyiha bilan ishlash

```typescript
class ProjectAPI extends BotMotherAPI {
  // Loyihalar ro'yxati
  async getProjects() {
    const response = await fetch(`${this.baseURL}/api/project/`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to get projects');
    }

    return await response.json();
  }

  // Loyiha yaratish
  async createProject(name: string) {
    const response = await fetch(`${this.baseURL}/api/project/`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        name,
        flow: { nodes: [], edges: [] },
      }),
    });

    if (!response.ok) {
      throw new Error('Failed to create project');
    }

    return await response.json();
  }

  // Loyiha ma'lumotlari
  async getProject(id: number) {
    const response = await fetch(`${this.baseURL}/api/project/${id}/`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to get project');
    }

    return await response.json();
  }

  // Flow yangilash
  async updateProjectFlow(id: number, flow: any) {
    const response = await fetch(`${this.baseURL}/api/project/${id}/`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify({ flow }),
    });

    if (!response.ok) {
      throw new Error('Failed to update project');
    }

    return await response.json();
  }

  // Debug boshlash
  async startDebug(id: number) {
    const response = await fetch(`${this.baseURL}/api/project/${id}/debug/`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to start debug');
    }

    return await response.json();
  }

  // Debug to'xtatish
  async stopDebug(id: number) {
    const response = await fetch(`${this.baseURL}/api/project/${id}/stop/`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to stop debug');
    }

    return await response.json();
  }

  // Debug ma'lumotlari
  async getDebugInfo(id: number) {
    const response = await fetch(`${this.baseURL}/api/project/${id}/info/`, {
      headers: this.getHeaders(),
    });

    if (!response.ok) {
      throw new Error('Failed to get debug info');
    }

    return await response.json();
  }
}

// Ishlatish
const projectAPI = new ProjectAPI();

async function workWithProject() {
  try {
    // 1. Loyiha yaratish
    const project = await projectAPI.createProject('My Bot');
    console.log('Project created:', project);

    // 2. Flow yangilash
    const flow = {
      nodes: [
        { id: '1', type: 'start', data: { label: 'Start' } },
        { id: '2', type: 'message', data: { text: 'Hello!' } },
      ],
      edges: [
        { id: 'e1-2', source: '1', target: '2' },
      ],
    };
    await projectAPI.updateProjectFlow(project.id, flow);

    // 3. Debug boshlash
    await projectAPI.startDebug(project.id);
    console.log('Debug started!');

    // 4. Debug ma'lumotlarini kuzatish
    setInterval(async () => {
      const info = await projectAPI.getDebugInfo(project.id);
      console.log('Debug status:', info.status);
    }, 5000);
  } catch (error) {
    console.error('Error:', error);
  }
}
```

---

### 3. Environment bilan ishlash

```typescript
class EnvironmentAPI extends BotMotherAPI {
  // Environment ro'yxati
  async getEnvironments(projectId: number) {
    const response = await fetch(
      `${this.baseURL}/api/enviroment/?project=${projectId}`,
      {
        headers: this.getHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to get environments');
    }

    return await response.json();
  }

  // Environment yaratish
  async createEnvironment(projectId: number, key: string, value: string) {
    const response = await fetch(
      `${this.baseURL}/api/enviroment/?project=${projectId}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ project: projectId, key, value }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to create environment');
    }

    return await response.json();
  }

  // Environment o'chirish
  async deleteEnvironment(projectId: number, key: string) {
    const response = await fetch(
      `${this.baseURL}/api/enviroment/${key}/?project=${projectId}`,
      {
        method: 'DELETE',
        headers: this.getHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to delete environment');
    }
  }
}

// Ishlatish
const envAPI = new EnvironmentAPI();

async function setupEnvironment(projectId: number) {
  try {
    // Bot token qo'shish
    await envAPI.createEnvironment(
      projectId,
      'BOT_TOKEN',
      '123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11'
    );

    // API key qo'shish
    await envAPI.createEnvironment(projectId, 'API_KEY', 'my-secret-key');

    // Ro'yxatni olish
    const envs = await envAPI.getEnvironments(projectId);
    console.log('Environments:', envs);
  } catch (error) {
    console.error('Error:', error);
  }
}
```

---

### 4. CMS Collection bilan ishlash

```typescript
class CollectionAPI extends BotMotherAPI {
  // Collection yaratish
  async createCollection(projectId: number, name: string, fields: any[]) {
    const response = await fetch(
      `${this.baseURL}/api/collection/?project=${projectId}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ name, project: projectId, fields }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to create collection');
    }

    return await response.json();
  }

  // Ma'lumot qo'shish
  async insertData(projectId: number, collectionName: string, data: any) {
    const response = await fetch(
      `${this.baseURL}/api/collection/${collectionName}/query/?action=insert&project=${projectId}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(data),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to insert data');
    }

    return await response.json();
  }

  // Ma'lumotlarni qidirish
  async findData(projectId: number, collectionName: string, query: any = {}) {
    const response = await fetch(
      `${this.baseURL}/api/collection/${collectionName}/query/?action=find&project=${projectId}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify(query),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to find data');
    }

    return await response.json();
  }

  // Ma'lumotni yangilash
  async updateData(
    projectId: number,
    collectionName: string,
    where: any,
    data: any
  ) {
    const response = await fetch(
      `${this.baseURL}/api/collection/${collectionName}/query/?action=update&project=${projectId}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ where, data }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to update data');
    }

    return await response.json();
  }

  // Ma'lumotni o'chirish
  async deleteData(projectId: number, collectionName: string, where: any) {
    const response = await fetch(
      `${this.baseURL}/api/collection/${collectionName}/query/?action=delete&project=${projectId}`,
      {
        method: 'POST',
        headers: this.getHeaders(),
        body: JSON.stringify({ where }),
      }
    );

    if (!response.ok) {
      throw new Error('Failed to delete data');
    }

    return await response.json();
  }
}

// Ishlatish
const cmsAPI = new CollectionAPI();

async function workWithCMS(projectId: number) {
  try {
    // 1. Collection yaratish
    await cmsAPI.createCollection(projectId, 'users', [
      { name: 'telegram_id', type: 'NUMBER', required: true },
      { name: 'username', type: 'TEXT', required: false },
      { name: 'balance', type: 'NUMBER', required: true, default: '0' },
    ]);

    // 2. Ma'lumot qo'shish
    const result = await cmsAPI.insertData(projectId, 'users', {
      telegram_id: 123456789,
      username: 'john_doe',
      balance: 100,
    });
    console.log('Inserted:', result);

    // 3. Qidirish
    const users = await cmsAPI.findData(projectId, 'users', {
      where: { balance: { $gte: 50 } },
      limit: 10,
      sort: { balance: -1 },
    });
    console.log('Users:', users);

    // 4. Yangilash
    await cmsAPI.updateData(
      projectId,
      'users',
      { telegram_id: 123456789 },
      { $set: { balance: 200 } }
    );

    // 5. O'chirish
    await cmsAPI.deleteData(projectId, 'users', {
      telegram_id: 123456789,
    });
  } catch (error) {
    console.error('Error:', error);
  }
}
```

---

### 5. SSE (Server-Sent Events) - Real-time loglar

```typescript
class LogsAPI {
  private baseURL: string;

  constructor(baseURL: string = 'http://localhost:8081') {
    this.baseURL = baseURL;
  }

  // Loglarni kuzatish
  watchLogs(serviceId: string, onLog: (log: string) => void) {
    const eventSource = new EventSource(
      `${this.baseURL}/sse/api/project/${serviceId}/logs/`
    );

    eventSource.onmessage = (event) => {
      onLog(event.data);

      // Konteyner to'xtasa, connectionni yoping
      if (event.data === 'Container is not running') {
        eventSource.close();
      }
    };

    eventSource.onerror = (error) => {
      console.error('SSE Error:', error);
      eventSource.close();
    };

    // Connectionni to'xtatish funksiyasi
    return () => eventSource.close();
  }
}

// Ishlatish
const logsAPI = new LogsAPI();

// React component misoli
function LogsViewer({ serviceId }) {
  const [logs, setLogs] = React.useState<string[]>([]);

  React.useEffect(() => {
    const unsubscribe = logsAPI.watchLogs(serviceId, (log) => {
      setLogs((prev) => [...prev, log]);
    });

    return unsubscribe;
  }, [serviceId]);

  return (
    <div>
      {logs.map((log, index) => (
        <div key={index}>{log}</div>
      ))}
    </div>
  );
}
```

---

## React Hook misoli

```typescript
// hooks/useBotMotherAPI.ts
import { useState, useEffect } from 'react';

export function useBotMotherAPI() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState(null);

  useEffect(() => {
    const token = localStorage.getItem('access_token');
    if (token) {
      setIsAuthenticated(true);
      fetchUser();
    }
  }, []);

  async function fetchUser() {
    try {
      const response = await fetch('http://localhost:8081/auth/me/', {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('access_token')}`,
        },
      });
      const data = await response.json();
      setUser(data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
    }
  }

  async function login(phone: string, password: string) {
    try {
      const response = await fetch('http://localhost:8081/auth/token/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone, password }),
      });

      const data = await response.json();
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);
      setIsAuthenticated(true);
      await fetchUser();
    } catch (error) {
      console.error('Login failed:', error);
      throw error;
    }
  }

  function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    setIsAuthenticated(false);
    setUser(null);
  }

  return { isAuthenticated, user, login, logout };
}
```

---

## Python misollar

```python
import requests
from typing import Optional

class BotMotherAPI:
    def __init__(self, base_url: str = "http://localhost:8081"):
        self.base_url = base_url
        self.access_token: Optional[str] = None
    
    def _get_headers(self):
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"
        return headers
    
    def login(self, phone: str, password: str):
        response = requests.post(
            f"{self.base_url}/auth/token/",
            json={"phone": phone, "password": password}
        )
        response.raise_for_status()
        data = response.json()
        self.access_token = data["access"]
        return data
    
    def get_projects(self):
        response = requests.get(
            f"{self.base_url}/api/project/",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def create_project(self, name: str):
        response = requests.post(
            f"{self.base_url}/api/project/",
            headers=self._get_headers(),
            json={"name": name, "flow": {"nodes": [], "edges": []}}
        )
        response.raise_for_status()
        return response.json()

# Ishlatish
api = BotMotherAPI()
api.login("+998901234567", "password123")
projects = api.get_projects()
print(projects)
```

---

## cURL misollar

```bash
# Login
curl -X POST http://localhost:8081/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"phone": "+998901234567", "password": "qwerty123"}'

# Get projects
curl -X GET http://localhost:8081/api/project/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create project
curl -X POST http://localhost:8081/api/project/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "My Bot", "flow": {"nodes": [], "edges": []}}'

# Start debug
curl -X GET http://localhost:8081/api/project/1/debug/ \
  -H "Authorization: Bearer YOUR_TOKEN"

# Create environment
curl -X POST "http://localhost:8081/api/enviroment/?project=1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"project": 1, "key": "BOT_TOKEN", "value": "123456:ABC..."}'

# CMS - Insert data
curl -X POST "http://localhost:8081/api/collection/users/query/?action=insert&project=1" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"telegram_id": 123456789, "username": "john_doe"}'
```

---

## Xatoliklarni boshqarish

```typescript
class APIError extends Error {
  constructor(
    public status: number,
    public message: string,
    public errors?: any
  ) {
    super(message);
  }
}

async function handleResponse(response: Response) {
  if (!response.ok) {
    const data = await response.json();
    throw new APIError(response.status, data.detail || 'API Error', data);
  }
  return response.json();
}

// Ishlatish
try {
  const projects = await api.getProjects();
} catch (error) {
  if (error instanceof APIError) {
    if (error.status === 401) {
      // Token muddati tugagan
      await refreshToken();
    } else if (error.status === 400) {
      // Validation xatolik
      console.error('Validation errors:', error.errors);
    } else {
      console.error('API error:', error.message);
    }
  }
}
```
