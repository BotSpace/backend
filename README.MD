# JST-Django Template Documentation

**Language:** [O'zbek](README.MD) | English

Welcome! This is a comprehensive Django project template designed to streamline Django application development with pre-configured architecture, best practices, and powerful CLI tools.

## Overview

This template consists of two main components:

1. **CLI Tool** - Command-line interface for generating Django apps and modules
2. **Architecture Template** - Production-ready Django project structure with Docker, pre-configured packages, and best practices

> **Note:** While these components can be used independently, using them together provides the best development experience.

## Key Features

- 🚀 Production-ready Django project structure
- 🐳 Docker & Docker Compose configuration
- 📦 Pre-configured popular packages (DRF, Celery, Redis, etc.)
- 🔧 CLI tool for rapid app/module generation
- 🌐 Multi-language support (modeltranslation/parler)
- 🔒 Security best practices included
- 📝 API documentation with Swagger/ReDoc
- ✅ Testing setup with pytest

## Installation

Install the CLI tool via pip:

```bash
pip install -U jst-django
```

> **Important:** Always use the latest version of the CLI tool for compatibility with the template.

## Quick Start

### 1. Create a New Project

```bash
jst create
```

You will be prompted for:

- **Template**: Choose "django" (default)
- **Project Name**: Your project name (used throughout the project)
- **Settings File**: Keep default
- **Packages**: Select additional packages you need:
  - modeltranslation or parler (choose one for translations)
  - silk (performance profiling)
  - channels (WebSocket support)
  - ckeditor (rich text editor)
  - and more...
- **Runner**: wsgi or asgi (choose asgi for WebSocket/async features)
- **Django Secret Key**: Change in production!
- **Port**: Default 8081
- **Admin Password**: Set a strong password
- **Flake8**: Code style enforcement (recommended)

### 2. Start the Project

**Requirements:** Docker must be installed on your system.

Navigate to your project directory:

```bash
cd your_project_name
```

Start the project using Make:

```bash
make up
```

Or manually:

```bash
docker compose up -d
docker compose exec web python manage.py seed
```

The project will be available at `http://localhost:8081`

### 3. Run Tests

```bash
make test
```

## Creating Applications

### Create a New App

```bash
jst make:app <app_name>
```

Choose a module type:
- **default**: Empty app structure
- **bot**: Telegram bot integration
- **authbot**: Telegram authentication
- **authv2**: New authentication system
- **websocket**: WebSocket support

The app will be automatically created and registered.

## Generating Modules

The most powerful feature of JST-Django is module generation:

```bash
jst make:module
```

You will be prompted for:

1. **File Name**: Basename for generated files (e.g., "post")
2. **Module Names**: List of models to generate (e.g., "post, tag, category")
3. **App**: Target application
4. **Components**: Select what to generate:
   - Model
   - Serializer
   - View (ViewSet)
   - Admin
   - Permissions
   - Filters
   - Tests
   - URLs

This generates complete CRUD APIs with all selected components!

## Project Structure

```
├── config/                 # Configuration files
│   ├── settings/          # Environment-specific settings
│   │   ├── common.py      # Shared settings
│   │   ├── local.py       # Development settings
│   │   ├── production.py  # Production settings
│   │   └── test.py        # Test settings
│   ├── conf/              # Package configurations
│   ├── urls.py
│   └── wsgi.py / asgi.py
├── core/
│   ├── apps/              # Django applications
│   │   ├── accounts/      # Pre-configured auth system
│   │   └── shared/        # Shared utilities
│   ├── services/          # Business logic services
│   └── utils/             # Utility functions
├── docker/                # Docker configurations
├── resources/             # Static resources, scripts
├── Makefile              # Convenience commands
├── docker-compose.yml    # Docker Compose config
├── requirements.txt      # Python dependencies
└── manage.py
```

## Available Make Commands

```bash
make up              # Start containers
make down            # Stop containers
make build           # Build containers
make rebuild         # Rebuild and restart
make logs            # View logs
make makemigrations  # Create migrations
make migrate         # Apply migrations
make migrations      # Make and apply migrations
make seed            # Seed database with initial data
make fresh           # Reset DB, migrate, and seed
make test            # Run tests
make deploy          # Deploy (local)
make deploy-prod     # Deploy (production)
```

## Security Considerations

⚠️ **Important:** See [SECURITY.md](SECURITY.md) for detailed security guidelines.

**Quick checklist:**
- ✅ Change `DJANGO_SECRET_KEY` in production
- ✅ Change default admin password
- ✅ Set `DEBUG=False` in production
- ✅ Configure proper `ALLOWED_HOSTS`
- ✅ Use HTTPS (`PROTOCOL_HTTPS=True`)
- ✅ Change database password
- ✅ Never commit `.env` file

## Environment Variables

Key environment variables in `.env`:

- `DJANGO_SECRET_KEY`: Django secret key (change in production!)
- `DEBUG`: Debug mode (False in production)
- `DB_PASSWORD`: Database password (change in production!)
- `DJANGO_SETTINGS_MODULE`: Settings module to use
- `PROJECT_ENV`: debug | prod
- `SILK_ENABLED`: Enable Silk profiling (optional)

See `.env.example` for all available options.

## Additional Packages

The template supports optional packages:

- **modeltranslation**: Model field translation
- **parler**: Alternative translation solution
- **silk**: Performance profiling
- **channels**: WebSocket/async support
- **ckeditor**: Rich text editor
- **rosetta**: Translation management
- **cacheops**: Advanced caching

## Testing

Tests are written using pytest-django:

```bash
# Run all tests
make test

# Run specific tests
docker compose exec web pytest path/to/test.py -v
```

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

## License

See [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue on GitHub
- Check existing documentation

---

## Kubernetes Deployment

This project supports Kubernetes deployment with **external PostgreSQL and Redis** for better scalability and high availability.

### Quick Start

See [k8s/QUICK-START.md](k8s/QUICK-START.md) for a quick guide (available in O'zbek/Uzbek).

For detailed documentation, see [k8s/README.md](k8s/README.md).

### Architecture

- **Web Service**: Django backend application
- **Nginx Service**: Reverse proxy and static file server
- **External PostgreSQL**: Database on dedicated host
- **External Redis**: Cache server on dedicated host

### Deploy to Kubernetes

```bash
# 1. Setup external PostgreSQL and Redis servers
# See k8s/QUICK-START.md for instructions

# 2. Update configuration with your external service IPs
# Edit k8s/overlays/production/configmap-patch.yaml

# 3. Create secrets
kubectl create secret generic botmother-secret \
  --namespace=botmother \
  --from-literal=DJANGO_SECRET_KEY='your-secret-key' \
  --from-literal=DB_PASSWORD='your-db-password'

# 4. Deploy
kubectl apply -k k8s/overlays/production

# 5. Run migrations
kubectl exec -n botmother -it deployment/botmother-web -- python manage.py migrate
```

### Helper Script

Use the deployment helper script for common tasks:

```bash
cd k8s
./deploy.sh
# Interactive menu for deploy, update, logs, migrations, etc.
```

### Migration from Docker Swarm

If migrating from Docker Swarm, see [k8s/MIGRATION.md](k8s/MIGRATION.md) for a comprehensive guide.

### Kubernetes Event Watching

Kubernetes automatically aggregates pod events from ALL nodes in the cluster. To watch these events:

```bash
# Start the Kubernetes event watcher
python manage.py watch_k8s_events

# With verbose logging
python manage.py watch_k8s_events --verbose

# Custom namespace
python manage.py watch_k8s_events --namespace=botmother
```

**Note:** Only ONE instance of the watcher should run across the cluster to avoid duplicate event processing.

### Useful Commands

```bash
# Check deployment status
kubectl get all -n botmother

# View logs
kubectl logs -n botmother -l component=web --tail=100
kubectl logs -n botmother -l component=nginx --tail=100

# Scale deployment
kubectl scale deployment botmother-web --replicas=3 -n botmother

# Update image
kubectl set image deployment/botmother-web web=registry.jscorp.uz/botmother:v1.0.1 -n botmother

# Rollback
kubectl rollout undo deployment/botmother-web -n botmother
```

---

**Happy Coding! 🚀**


