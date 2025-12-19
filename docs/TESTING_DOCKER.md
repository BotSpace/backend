# Docker ichida testlarni ishga tushirish

## 1. Docker container ichiga kirish

```bash
docker-compose exec web bash
```

## 2. Testlarni ishga tushirish

### Barcha testlarni ishga tushirish
```bash
python -m pytest
```

### Faqat chat testlarni ishga tushirish
```bash
python -m pytest core/apps/api/tests/test_chat_api.py -v
```

### Bitta testni ishga tushirish
```bash
python -m pytest core/apps/api/tests/test_chat_api.py::TestChatAPI::test_send_message -v
```

### Coverage bilan testlarni ishga tushirish
```bash
python -m pytest --cov=core/apps/api/views/chat --cov-report=html
```

## 3. Testlar natijasini ko'rish

### HTML coverage reportni ko'rish
```bash
# Container ichida
cd htmlcov
python -m http.server 8080

# Browserda: http://localhost:8080
```

## 4. Debugging

### Interaktiv debugging (pdb)
```bash
python -m pytest core/apps/api/tests/test_chat_api.py -v -s
```

Test ichida breakpoint qo'shish:
```python
import pdb; pdb.set_trace()
```

## 5. Docker-compose bilan testlarni ishga tushirish (containerga kirmasdan)

### Barcha testlar
```bash
docker-compose exec web python -m pytest
```

### Faqat chat testlar
```bash
docker-compose exec web python -m pytest core/apps/api/tests/test_chat_api.py -v
```

### Bitta test
```bash
docker-compose exec web python -m pytest core/apps/api/tests/test_chat_api.py::TestChatAPI::test_send_message -v
```

## 6. Test database tozalash

Agar testlar database bilan muammoga duch kelsa:

```bash
# Container ichida
python manage.py flush --no-input
python manage.py migrate
```

## 7. Test environment variables

Test uchun maxsus environment variablelar `.env` faylida:

```env
# Test settings
DJANGO_SETTINGS_MODULE=config.settings.local
DEBUG=True

# Test database (optional - Django avtomatik test DB yaratadi)
# TEST_DB_NAME=test_django

# MongoDB test
MONGO_URL=mongodb://admin:admin123@mongo:27017/

# Redis test
REDIS_URL=redis://redis:6379/0
```

## 8. Continuous Integration (CI) uchun

GitHub Actions yoki GitLab CI da ishlatish uchun:

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v2
    
    - name: Run tests
      run: |
        docker-compose up -d
        docker-compose exec -T web python -m pytest -v
        docker-compose down
```

## 9. Xotira va performance monitoring

### Xotira ishlatishini monitoring qilish
```bash
docker stats
```

### Slow testlarni topish
```bash
python -m pytest --durations=10
```

## 10. Test fixtures va factories

Test uchun fake data yaratish:

```python
# Test ichida
from core.apps.api.models import ProjectModel

# Factory method ishlatish
project = ProjectModel._create_fake()
```

## 11. Parallel testlar

Tezroq testlar uchun parallel ishga tushirish:

```bash
# pytest-xdist o'rnatish
pip install pytest-xdist

# Parallel ishga tushirish (4 worker)
python -m pytest -n 4
```

## 12. Specific test markers

```bash
# Faqat integration testlarni ishga tushirish
python -m pytest -m integration

# Integration testlarni o'tkazib yuborish
python -m pytest -m "not integration"

# Slow testlarni skip qilish
python -m pytest -m "not slow"
```

## 13. Logging va output

### Verbose output
```bash
python -m pytest -v -s
```

### Logging ko'rish
```bash
python -m pytest --log-cli-level=DEBUG
```

## 14. Failed testlarni qayta ishga tushirish

```bash
# Failed testlarni birinchi marta ishga tushirish
python -m pytest

# Faqat failed testlarni qayta ishga tushirish
python -m pytest --lf

# Failed testlarni birinchi navbatda ishga tushirish
python -m pytest --ff
```

## 15. Test cache tozalash

```bash
# Pytest cache tozalash
python -m pytest --cache-clear

# Python cache tozalash
find . -type d -name __pycache__ -exec rm -rf {} +
find . -type f -name "*.pyc" -delete
```
