# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Development
make up              # Start all Docker containers
make down            # Stop containers
make rebuild         # down + build + up
make logs            # View container logs

# Database
make migrate         # Apply migrations
make makemigrations  # Create new migrations
make migrations      # makemigrations + migrate
make seed            # Load initial data
make fresh           # Reset DB, migrate, and seed

# Testing
make test            # Run all tests via Docker
docker compose exec web pytest path/to/test.py -v           # Single test file
docker compose exec web pytest path/to/test.py::Class::method -v  # Single test

# Linting / Formatting (run inside container or with venv active)
flake8 core config
black core config
isort core config
```

## Architecture

### Services
The project runs 5 Docker services: **nginx** (reverse proxy, port 8081), **web** (Django ASGI app), **db** (PostgreSQL 16), **redis** (cache/broker), **mongo** (MongoDB 7 for CMS document storage).

### Settings
Settings are split by environment under `config/settings/`: `local.py`, `production.py`, `test.py` all import from `common.py`. Package-specific configs (DRF, JWT, Celery, storage, etc.) live in `config/conf/` as separate modules imported by `common.py`. Environment variables are managed via `config/env.py`.

### Apps (`core/apps/`)
| App | Responsibility |
|-----|---------------|
| `accounts` | Custom User model (phone-based auth), JWT, registration, balance |
| `api` | Projects, resources, webhooks, file uploads, chat integration |
| `authbot` | Telegram bot authentication flow |
| `cms` | Content management backed by MongoDB |
| `payment` | Payme, Click, PayTech payment gateway integrations |
| `template` | Email/message templates |
| `websocket` | WebSocket + SSE real-time communication |
| `shared` | Base serializers, permissions, filters shared across apps |

Each app follows the same internal structure: `models/`, `serializers/`, `views/`, `admin/`, `permissions/`, `filters/`, `services/`, `tasks/`, `signals/`, `migrations/`, `tests/`, `urls.py`.

### Cross-cutting concerns
- **Auth:** JWT via `djangorestframework-simplejwt`; custom permission classes in `core/permissions/`; custom throttles in `core/throttle/`
- **Caching:** Redis via `django-redis` + `django-cacheops`; toggled by `CACHE_ENABLED` env var
- **Background tasks:** Celery 5 with Redis broker/backend; beat scheduler for periodic tasks
- **i18n:** `django-modeltranslation` + `jst-parler`; languages uz/ru/en (default: uz)
- **Admin:** `django-unfold` (modern UI); navigation configured in `config/conf/navigation.py`
- **API docs:** drf-spectacular; Swagger at `/swagger/`, ReDoc at `/redoc/`
- **Monitoring:** Prometheus metrics at `/metrics/`; optional Silk profiling (`SILK_ENABLED=True`)

### Code style
- Line length: **120** (Black, isort, Flake8)
- Python: **3.12**
- Tests use `pytest-django` with `model_bakery` for fixtures; test DB is PostgreSQL (not SQLite), settings module `config.settings.test`
