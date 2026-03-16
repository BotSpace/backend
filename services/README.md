# Go Microservices

This directory contains three independent Go microservices extracted from the main Django backend.
Each service has its own dedicated database and communicates with the others via **Redis Streams**.

---

## Services

| Service | Port | Database | Description |
|---|---|---|---|
| `cms-service` | 8081 | MongoDB (`cms_mongo`) | CMS collections, fields, and data querying |
| `template-service` | 8082 | PostgreSQL (`template_db`) | Template marketplace, orders, submissions, withdrawals |
| `payment-service` | 8083 | PostgreSQL (`payment_db`) | Transactions, balance history, Click/Payme webhooks |

---

## Architecture

```
┌──────────────────┐     Redis Streams      ┌────────────────────┐
│  payment-service │ ──payment:events──────► │ template-service   │
│  (PostgreSQL)    │                         │ (PostgreSQL)       │
└──────────────────┘                         └────────────────────┘
         │                                            │
         │                                    template:events
         │                                            │
         │                                            ▼
         │                                   ┌────────────────────┐
         └──payment:events──────────────────►│   cms-service      │
                                             │   (MongoDB)        │
                                             └────────────────────┘
```

### Redis Stream Events

| Stream | Event | Published by | Consumed by |
|---|---|---|---|
| `payment:events` | `payment_success` | payment-service | template-service, cms-service |
| `payment:events` | `payment_failed` | payment-service | template-service, cms-service |
| `template:events` | `order_created` | template-service | payment-service |
| `template:events` | `order_confirmed` | template-service | payment-service |
| `cms:events` | `collection_created` | cms-service | — |
| `cms:events` | `collection_deleted` | cms-service | — |

---

## Running locally

All services are included in the root `docker-compose.yml`:

```bash
# Start all services (including Go microservices and their databases)
docker-compose up --build

# Start only Go microservices
docker-compose up --build cms-service template-service payment-service
```

### Environment variables

Copy `.env.example` to `.env` and populate the following variables:

```env
# CMS service
CMS_MONGO_USER=admin
CMS_MONGO_PASSWORD=admin123

# Template service
TEMPLATE_DB_USER=postgres
TEMPLATE_DB_PASSWORD=2309

# Payment service
PAYMENT_DB_USER=postgres
PAYMENT_DB_PASSWORD=2309
CLICK_SERVICE_ID=
CLICK_MERCHANT_ID=
PAYME_ID=
PAYTECH_API_KEY=

# Shared
JWT_SECRET=your-jwt-secret
```

---

## API Endpoints

### CMS Service (`http://localhost:8081`)

All endpoints require `Authorization: Bearer <token>`.

| Method | Path | Description |
|---|---|---|
| GET | `/health` | Health check |
| GET | `/api/v1/collection?project_id=<id>` | List collections |
| POST | `/api/v1/collection` | Create collection |
| GET | `/api/v1/collection/:id` | Get collection |
| PATCH | `/api/v1/collection/:id` | Update collection |
| DELETE | `/api/v1/collection/:id` | Delete collection |
| GET | `/api/v1/collection/:id/fields` | List fields |
| POST | `/api/v1/collection/:id/fields` | Add field |
| POST | `/api/v1/collection/:id/query` | Query data (find/insert/update/delete/count) |
| POST | `/api/v1/collection/:id/export-excel` | Start async Excel export |
| GET | `/api/v1/collection/export-status/:task_id` | Get export task status |

### Template Service (`http://localhost:8082`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| GET | `/api/v1/template/list` | — | List verified templates |
| GET | `/api/v1/template/list/:slug` | — | Get template detail |
| GET | `/api/v1/template/category` | — | List categories |
| GET | `/api/v1/template/feature` | — | List features |
| GET | `/api/v1/template/my-template` | ✓ | My purchased templates |
| GET | `/api/v1/template/order` | ✓ | List orders |
| POST | `/api/v1/template/order` | ✓ | Create order |
| GET | `/api/v1/template/order/:id` | ✓ | Get order |
| GET | `/api/v1/template/submission` | ✓ | List submissions |
| POST | `/api/v1/template/submission` | ✓ | Create submission |
| GET | `/api/v1/template/submission/:id` | ✓ | Get submission |
| PATCH | `/api/v1/template/submission/:id` | ✓ | Update submission (pending only) |
| DELETE | `/api/v1/template/submission/:id` | ✓ | Delete submission (pending only) |
| GET | `/api/v1/template/withdrawal` | ✓ | List withdrawals |
| POST | `/api/v1/template/withdrawal` | ✓ | Create withdrawal |
| GET | `/api/v1/template/withdrawal/:id` | ✓ | Get withdrawal |
| DELETE | `/api/v1/template/withdrawal/:id` | ✓ | Delete withdrawal (pending only) |

### Payment Service (`http://localhost:8083`)

| Method | Path | Auth | Description |
|---|---|---|---|
| GET | `/health` | — | Health check |
| GET | `/api/v1/transaction` | ✓ | List transactions |
| GET | `/api/v1/transaction/:id` | ✓ | Get transaction |
| GET | `/api/v1/history` | ✓ | List balance history |
| GET | `/api/v1/history/:id` | ✓ | Get history entry |
| POST | `/api/v1/payment/create-transaction` | ✓ | Create payment link (click/payme) |
| POST | `/api/v1/payment/click/update` | — | Click payment webhook |
| POST | `/api/v1/payment/payme/update` | — | Payme payment webhook |
