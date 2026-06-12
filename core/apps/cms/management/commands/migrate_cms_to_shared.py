"""Per-project MongoDB database'larini bitta umumiy database'ga ko'chiradi.

ESKI:  project_<id>  database, har collection alohida namespace (257 DB → portlash).
YANGI: CMS_SHARED_DB (default botspace_cms) bitta DB; har hujjatga `_project_id`
       qo'shiladi; collection nomi saqlanadi (orders, doctors, ...).

Bu komanda FAQAT ma'lumotni ko'chiradi — jonli o'qish hali ham eski DB'lardan
ketadi (CMS_SHARED_TENANCY flag OFF bo'lguncha). Shuning uchun migratsiyani
flag'ni yoqishdan OLDIN, xavfsiz ishga tushirsa bo'ladi. Idempotent: takror
ishga tushsa, allaqachon ko'chirilgan (_id bo'yicha dublikat) hujjatlar o'tkazib
yuboriladi.

    python manage.py migrate_cms_to_shared --dry-run
    python manage.py migrate_cms_to_shared --project 1285
    python manage.py migrate_cms_to_shared            # hammasi
"""

from __future__ import annotations

import re

from django.core.management.base import BaseCommand
from pymongo.errors import BulkWriteError
from rich.console import Console

from core.apps.cms.services.mongo import SHARED_DB_NAME, TENANT_FIELD, get_mongo_client

console = Console()

_PROJECT_DB_RE = re.compile(r"^project_(\d+)$")
_BATCH = 1000


class Command(BaseCommand):
    help = "Migrate per-project Mongo databases into one shared database (_project_id tagged)."

    def add_arguments(self, parser):
        parser.add_argument("--project", type=int, help="Only this project id.")
        parser.add_argument("--dry-run", action="store_true", help="Show plan, change nothing.")

    def handle(self, *args, **options):
        only = options.get("project")
        dry = options.get("dry_run", False)

        client = get_mongo_client().client
        shared = client[SHARED_DB_NAME]

        db_names = client.list_database_names()
        targets: list[tuple[str, int]] = []
        for name in db_names:
            m = _PROJECT_DB_RE.match(name)
            if not m:
                continue
            pid = int(m.group(1))
            if only is not None and pid != only:
                continue
            targets.append((name, pid))

        targets.sort(key=lambda t: t[1])
        console.print(f"\n[cyan]Migratsiya:[/cyan] {len(targets)} ta loyiha DB → '{SHARED_DB_NAME}'"
                      f"{' [yellow](DRY RUN)[/yellow]' if dry else ''}\n")

        total_copied = total_dup = 0
        touched_collections: set[str] = set()

        for db_name, pid in targets:
            src = client[db_name]
            for coll_name in src.list_collection_names():
                if coll_name.startswith("system."):
                    continue
                docs = list(src[coll_name].find({}))
                if not docs:
                    continue
                touched_collections.add(coll_name)
                if dry:
                    console.print(f"  [dim]proj {pid:<6} {coll_name:<18} {len(docs):>5} hujjat[/dim]")
                    total_copied += len(docs)
                    continue

                for d in docs:
                    d[TENANT_FIELD] = pid  # tenant tegi
                copied, dup = self._insert_batch(shared[coll_name], docs)
                total_copied += copied
                total_dup += dup
                console.print(f"  proj {pid:<6} {coll_name:<18} +{copied} (dup {dup})")

        # Umumiy collection'larga tenant index'larini qo'yamiz.
        if not dry:
            for coll_name in sorted(touched_collections):
                try:
                    shared[coll_name].create_index([(TENANT_FIELD, 1), ("_deleted_at", 1)])
                except Exception as exc:  # noqa: BLE001
                    console.print(f"  [red]index xato {coll_name}: {exc}[/red]")

        console.print(f"\n[bold]Jami:[/bold] ko'chirildi={total_copied} dublikat={total_dup} "
                      f"collection={len(touched_collections)}")
        if dry:
            console.print("[yellow]DRY RUN — hech narsa o'zgartirilmadi.[/yellow]")
        else:
            console.print("[green]✓ Tayyor. Endi CMS_SHARED_TENANCY=true qilib tekshiring.[/green]\n")

    @staticmethod
    def _insert_batch(dest, docs: list[dict]) -> tuple[int, int]:
        """insert_many(ordered=False) — mavjud _id'lar (idempotent qayta ishga tushish)
        dublikat sifatida o'tkazib yuboriladi."""
        copied = dup = 0
        for i in range(0, len(docs), _BATCH):
            chunk = docs[i : i + _BATCH]
            try:
                res = dest.insert_many(chunk, ordered=False)
                copied += len(res.inserted_ids)
            except BulkWriteError as bwe:
                we = bwe.details.get("writeErrors", [])
                dups = sum(1 for e in we if e.get("code") == 11000)
                dup += dups
                copied += len(chunk) - len(we)
        return copied, dup
