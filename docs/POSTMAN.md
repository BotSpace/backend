# Postman Collection

BotMother API uchun Postman collection va environment o'rnatish qo'llanmasi.

---

## Environment O'rnatish

### 1. Postman'da yangi Environment yarating

`Environments` → `Add` → Environment nomi: `BotMother Local`

### 2. Quyidagi o'zgaruvchilarni qo'shing:

| Variable | Initial Value | Current Value | Type |
|----------|--------------|---------------|------|
| `base_url` | `http://localhost:8081` | `http://localhost:8081` | default |
| `access_token` | | | secret |
| `refresh_token` | | | secret |
| `project_id` | `1` | `1` | default |
| `phone` | `+998901234567` | `+998901234567` | default |

---

## Collection yaratish

### 1. Yangi Collection yarating

`Collections` → `New Collection` → Nom: `BotMother API`

### 2. Collection Settings

`Variables` tabida:
- `baseUrl` = `{{base_url}}`

`Authorization` tabida:
- Type: `Bearer Token`
- Token: `{{access_token}}`

---

## Request'lar

### 📁 Authentication

#### 1. Register (POST)

```
POST {{base_url}}/auth/register/
```

**Body (JSON):**
```json
{
  "phone": "{{phone}}",
  "first_name": "Test",
  "last_name": "User",
  "password": "qwerty123"
}
```

**Tests:**
```javascript
pm.test("Status code is 202", function () {
    pm.response.to.have.status(202);
});

pm.test("SMS sent message", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.detail).to.include("yuborildi");
});
```

---

#### 2. Confirm (POST)

```
POST {{base_url}}/auth/confirm/
```

**Body (JSON):**
```json
{
  "phone": "{{phone}}",
  "code": "1234"
}
```

**Tests:**
```javascript
pm.test("Status code is 202", function () {
    pm.response.to.have.status(202);
});

pm.test("Token received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.token).to.have.property('access');
    pm.expect(jsonData.token).to.have.property('refresh');
    
    // Save tokens to environment
    pm.environment.set("access_token", jsonData.token.access);
    pm.environment.set("refresh_token", jsonData.token.refresh);
});
```

---

#### 3. Login (POST)

```
POST {{base_url}}/auth/token/
```

**Body (JSON):**
```json
{
  "phone": "{{phone}}",
  "password": "qwerty123"
}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Tokens received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('access');
    pm.expect(jsonData).to.have.property('refresh');
    
    // Save tokens
    pm.environment.set("access_token", jsonData.access);
    pm.environment.set("refresh_token", jsonData.refresh);
});
```

---

#### 4. Refresh Token (POST)

```
POST {{base_url}}/auth/token/refresh/
```

**Body (JSON):**
```json
{
  "refresh": "{{refresh_token}}"
}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Access token refreshed", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('access');
    pm.environment.set("access_token", jsonData.access);
});
```

---

#### 5. Get Me (GET)

```
GET {{base_url}}/auth/me/
```

**Authorization:** Bearer Token (automatically from collection)

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("User data received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('id');
    pm.expect(jsonData).to.have.property('phone');
});
```

---

### 📁 Projects

#### 1. List Projects (GET)

```
GET {{base_url}}/api/project/
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Projects array received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an('array');
    
    if (jsonData.length > 0) {
        pm.environment.set("project_id", jsonData[0].id);
    }
});
```

---

#### 2. Create Project (POST)

```
POST {{base_url}}/api/project/
```

**Body (JSON):**
```json
{
  "name": "Test Bot Project",
  "flow": {
    "nodes": [],
    "edges": []
  }
}
```

**Tests:**
```javascript
pm.test("Status code is 201", function () {
    pm.response.to.have.status(201);
});

pm.test("Project created", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('id');
    pm.environment.set("project_id", jsonData.id);
});
```

---

#### 3. Get Project (GET)

```
GET {{base_url}}/api/project/{{project_id}}/
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Project details received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('debug');
    pm.expect(jsonData).to.have.property('flow');
});
```

---

#### 4. Update Project (PATCH)

```
PATCH {{base_url}}/api/project/{{project_id}}/
```

**Body (JSON):**
```json
{
  "name": "Updated Bot Name",
  "flow": {
    "nodes": [
      {
        "id": "1",
        "type": "start",
        "data": {"label": "Start"}
      }
    ],
    "edges": []
  }
}
```

---

#### 5. Start Debug (GET)

```
GET {{base_url}}/api/project/{{project_id}}/debug/
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Debug started", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData.detail).to.include("Updated");
});
```

---

#### 6. Get Debug Info (GET)

```
GET {{base_url}}/api/project/{{project_id}}/info/
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Debug info received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('status');
    pm.expect(jsonData).to.have.property('service_id');
});
```

---

#### 7. Stop Debug (GET)

```
GET {{base_url}}/api/project/{{project_id}}/stop/
```

---

### 📁 Environment Variables

#### 1. List Environments (GET)

```
GET {{base_url}}/api/enviroment/?project={{project_id}}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Environments array received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an('array');
});
```

---

#### 2. Create Environment (POST)

```
POST {{base_url}}/api/enviroment/?project={{project_id}}
```

**Body (JSON):**
```json
{
  "project": {{project_id}},
  "key": "BOT_TOKEN",
  "value": "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
}
```

**Tests:**
```javascript
pm.test("Status code is 201", function () {
    pm.response.to.have.status(201);
});

pm.test("Environment created", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('key');
    pm.expect(jsonData).to.have.property('value');
});
```

---

#### 3. Get Environment (GET)

```
GET {{base_url}}/api/enviroment/BOT_TOKEN/?project={{project_id}}
```

---

#### 4. Update Environment (PATCH)

```
PATCH {{base_url}}/api/enviroment/BOT_TOKEN/?project={{project_id}}
```

**Body (JSON):**
```json
{
  "value": "new-token-value"
}
```

---

#### 5. Delete Environment (DELETE)

```
DELETE {{base_url}}/api/enviroment/BOT_TOKEN/?project={{project_id}}
```

---

### 📁 Releases

#### 1. List Releases (GET)

```
GET {{base_url}}/api/relase/?project={{project_id}}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Releases array received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an('array');
    
    if (jsonData.length > 0) {
        pm.environment.set("release_id", jsonData[0].id);
    }
});
```

---

#### 2. Create Release (POST)

```
POST {{base_url}}/api/relase/
```

**Body (JSON):**
```json
{
  "project": {{project_id}}
}
```

**Tests:**
```javascript
pm.test("Status code is 201", function () {
    pm.response.to.have.status(201);
});

pm.test("Release created", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('version');
    pm.environment.set("release_id", jsonData.id);
});
```

---

#### 3. Get Release (GET)

```
GET {{base_url}}/api/relase/{{release_id}}/
```

---

#### 4. Stop Release (GET)

```
GET {{base_url}}/api/relase/{{release_id}}/stop/
```

---

### 📁 CMS Collections

#### 1. List Collections (GET)

```
GET {{base_url}}/api/collection/?project={{project_id}}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Collections array received", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an('array');
    
    if (jsonData.length > 0) {
        pm.environment.set("collection_name", jsonData[0].name);
    }
});
```

---

#### 2. Create Collection (POST)

```
POST {{base_url}}/api/collection/?project={{project_id}}
```

**Body (JSON):**
```json
{
  "name": "users",
  "project": {{project_id}},
  "fields": [
    {
      "name": "telegram_id",
      "type": "NUMBER",
      "required": true
    },
    {
      "name": "username",
      "type": "TEXT",
      "required": false
    },
    {
      "name": "balance",
      "type": "NUMBER",
      "required": true,
      "default": "0"
    }
  ]
}
```

**Tests:**
```javascript
pm.test("Status code is 201", function () {
    pm.response.to.have.status(201);
});

pm.test("Collection created", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('name');
    pm.environment.set("collection_name", jsonData.name);
});
```

---

#### 3. Get Collection (GET)

```
GET {{base_url}}/api/collection/{{collection_name}}/?project={{project_id}}
```

---

#### 4. Insert Data (POST)

```
POST {{base_url}}/api/collection/{{collection_name}}/query/?action=insert&project={{project_id}}
```

**Body (JSON):**
```json
{
  "telegram_id": 123456789,
  "username": "john_doe",
  "balance": 100
}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Data inserted", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('inserted_id');
    pm.environment.set("inserted_id", jsonData.inserted_id);
});
```

---

#### 5. Find Data (POST)

```
POST {{base_url}}/api/collection/{{collection_name}}/query/?action=find&project={{project_id}}
```

**Body (JSON):**
```json
{
  "where": {
    "balance": {
      "$gte": 50
    }
  },
  "limit": 10,
  "sort": {
    "balance": -1
  }
}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Data found", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.be.an('array');
});
```

---

#### 6. Find One (POST)

```
POST {{base_url}}/api/collection/{{collection_name}}/query/?action=find_one&project={{project_id}}
```

**Body (JSON):**
```json
{
  "where": {
    "telegram_id": 123456789
  }
}
```

---

#### 7. Update Data (POST)

```
POST {{base_url}}/api/collection/{{collection_name}}/query/?action=update&project={{project_id}}
```

**Body (JSON):**
```json
{
  "where": {
    "telegram_id": 123456789
  },
  "data": {
    "$set": {
      "balance": 200
    }
  }
}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Data updated", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('modified_count');
    pm.expect(jsonData.modified_count).to.be.above(0);
});
```

---

#### 8. Delete Data (POST)

```
POST {{base_url}}/api/collection/{{collection_name}}/query/?action=delete&project={{project_id}}
```

**Body (JSON):**
```json
{
  "where": {
    "telegram_id": 123456789
  }
}
```

**Tests:**
```javascript
pm.test("Status code is 200", function () {
    pm.response.to.have.status(200);
});

pm.test("Data deleted", function () {
    var jsonData = pm.response.json();
    pm.expect(jsonData).to.have.property('deleted_count');
});
```

---

## Pre-request Scripts

### Collection-level (barcha request'lar uchun)

```javascript
// Token borligini tekshirish
const token = pm.environment.get("access_token");
if (!token && pm.request.url.path.join('/').indexOf('auth') === -1) {
    console.log("Warning: No access token found!");
}

// Base URL o'rnatish
pm.variables.set("base_url", pm.environment.get("base_url") || "http://localhost:8081");
```

---

## Common Tests

### Global Tests (Collection-level)

```javascript
// Response time tekshirish
pm.test("Response time is less than 2000ms", function () {
    pm.expect(pm.response.responseTime).to.be.below(2000);
});

// Content-Type tekshirish
pm.test("Content-Type is JSON", function () {
    pm.expect(pm.response.headers.get("Content-Type")).to.include("application/json");
});

// Status code 5xx bo'lmasligi kerak
pm.test("No server errors", function () {
    pm.expect(pm.response.code).to.be.below(500);
});
```

---

## Export/Import

### Collection export qilish:

1. Collection ustiga o'ng tugma → Export
2. Collection v2.1 formatini tanlang
3. File saqlang

### Import qilish:

1. Postman → Import
2. File tanlang yoki drag & drop qiling
3. Import tugmasini bosing

---

## Newman (CLI) bilan ishlatish

Newman - Postman collection'larni command line'da ishlatish uchun tool.

### Install:
```bash
npm install -g newman
```

### Run collection:
```bash
newman run BotMother_API.postman_collection.json \
  -e BotMother_Local.postman_environment.json
```

### HTML report yaratish:
```bash
newman run BotMother_API.postman_collection.json \
  -e BotMother_Local.postman_environment.json \
  -r html,cli \
  --reporter-html-export report.html
```

---

## Tips & Tricks

### 1. Dynamic variables

Postman'ning built-in dynamic variables:
- `{{$guid}}` - UUID
- `{{$timestamp}}` - Unix timestamp
- `{{$randomInt}}` - Random integer

### 2. Variables hierarchy

1. Global
2. Collection
3. Environment
4. Data
5. Local

### 3. Snippets

Postman'da tayyor test snippet'lar mavjud:
- Tests → Snippets (o'ng taraf)
- Status code checks
- Response body assertions
- Response time checks

### 4. Keyboard shortcuts

- `Ctrl/Cmd + Enter` - Send request
- `Ctrl/Cmd + S` - Save request
- `Ctrl/Cmd + K` - Search

---

## Troubleshooting

### Token expired xatoligi

1. Refresh token endpoint'idan foydalaning
2. Yoki qayta login qiling

### 401 Unauthorized

1. `access_token` environment variable to'g'ri o'rnatilganini tekshiring
2. Token muddati tugagan bo'lishi mumkin

### CORS xatolari

Backend'da CORS sozlamalari to'g'ri ekanini tekshiring. Postman'da odatda CORS muammolari bo'lmaydi.

---

## Qo'shimcha

### Folder Structure tavsiyasi:

```
BotMother API/
├── 📁 Authentication
│   ├── Register
│   ├── Confirm
│   ├── Login
│   ├── Refresh Token
│   └── Get Me
├── 📁 Projects
│   ├── List
│   ├── Create
│   ├── Get
│   ├── Update
│   ├── Delete
│   ├── Start Debug
│   ├── Stop Debug
│   └── Debug Info
├── 📁 Environments
├── 📁 Releases
└── 📁 CMS Collections
```
