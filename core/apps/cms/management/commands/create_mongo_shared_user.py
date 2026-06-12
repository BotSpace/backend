"""Umumiy (shared) MongoDB foydalanuvchisini yaratadi/yangilaydi.

Shared-tenancy rejimida botlar per-project user o'rniga BITTA shared user bilan
`CMS_SHARED_DB` (botspace_cms) ga ulanadi (readWrite). Tenant izolyatsiya engine/
backend ichida `_project_id` bilan ta'minlanadi. Bu komanda user'ni idempotent
yaratadi va ulanish satrini chiqaradi — uni `mongo-secret`'dagi `MONGO_SHARED_URL`
kalitiga joylashtiring (deploy_engine shu env'ni botlarga uzatadi).

    python manage.py create_mongo_shared_user            # parol generatsiya qiladi
    python manage.py create_mongo_shared_user --password <pw>
"""

from __future__ import annotations

import secrets
import string
from urllib.parse import quote_plus, urlparse

from django.core.management.base import BaseCommand

from config.env import env
from core.apps.cms.services.mongo import SHARED_DB_NAME, get_mongo_client

SHARED_USER = "cms_shared_user"


class Command(BaseCommand):
    help = "Create/update the shared MongoDB user with readWrite on the shared CMS database."

    def add_arguments(self, parser):
        parser.add_argument("--password", help="Explicit password (else random).")

    def handle(self, *args, **options):
        pw = options.get("password") or "".join(
            secrets.choice(string.ascii_letters + string.digits) for _ in range(32)
        )
        admin = get_mongo_client().admin_client.admin
        roles = [{"role": "readWrite", "db": SHARED_DB_NAME}]
        if admin.command("usersInfo", SHARED_USER).get("users"):
            admin.command("updateUser", SHARED_USER, pwd=pw, roles=roles)
            self.stdout.write(self.style.WARNING(f"updated user {SHARED_USER}"))
        else:
            admin.command("createUser", SHARED_USER, pwd=pw, roles=roles)
            self.stdout.write(self.style.SUCCESS(f"created user {SHARED_USER}"))

        p = urlparse(env.str("MONGO_URL"))
        host, port = p.hostname or "localhost", p.port or 27017
        conn = f"mongodb://{quote_plus(SHARED_USER)}:{quote_plus(pw)}@{host}:{port}/{SHARED_DB_NAME}?authSource=admin"
        self.stdout.write("\nMONGO_SHARED_URL (mongo-secret'ga qo'ying):")
        self.stdout.write(conn)
