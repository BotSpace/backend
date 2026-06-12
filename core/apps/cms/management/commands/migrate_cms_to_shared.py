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
from pymongo.errors import DuplicateKeyError
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

        total_copied = total_dup = total_regen = 0
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
                copied, dup, regen = self._insert_batch(shared[coll_name], docs)
                total_copied += copied
                total_dup += dup
                total_regen += regen
                console.print(f"  proj {pid:<6} {coll_name:<18} +{copied} (dup {dup}, regen {regen})")

        # Umumiy collection'larga tenant index'larini qo'yamiz.
        if not dry:
            for coll_name in sorted(touched_collections):
                try:
                    shared[coll_name].create_index([(TENANT_FIELD, 1), ("_deleted_at", 1)])
                except Exception as exc:  # noqa: BLE001
                    console.print(f"  [red]index xato {coll_name}: {exc}[/red]")

        console.print(f"\n[bold]Jami:[/bold] ko'chirildi={total_copied} dublikat={total_dup} "
                      f"yangi_id={total_regen} collection={len(touched_collections)}")
        if dry:
            console.print("[yellow]DRY RUN — hech narsa o'zgartirilmadi.[/yellow]")
        else:
            console.print("[green]✓ Tayyor. Endi CMS_SHARED_TENANCY=true qilib tekshiring.[/green]\n")

    @staticmethod
    def _insert_batch(dest, docs: list[dict]) -> tuple[int, int, int]:
        """Per-document insert (correctness over speed — one-time migration).

        Shared collection'da `_id` ikki xil sababdan to'qnashishi mumkin:
          1. Idempotent qayta ishga tushish — SHU loyihaning hujjati allaqachon
             ko'chirilgan (aynan o'sha `_project_id` + `_id`) → dublikat, o'tkazib
             yuboramiz.
          2. Boshqa loyiha bilan `_id` to'qnashuvi — template-copy `_id` ni
             saqlab qolgani uchun ikki loyiha bir xil `_id` ga ega bo'lishi mumkin.
             Bu holda `_id` ni tashlab, Mongo'ga YANGI `_id` berdiramiz.

        Returns: (copied, dup, regenerated).
        """
        copied = dup = regen = 0
        for doc in docs:
            try:
                dest.insert_one(doc)
                copied += 1
                continue
            except DuplicateKeyError:
                pass

            # `_id` to'qnashdi. Ikki holat bor:
            #   (a) idempotent qayta ishga tushish — AYNAN shu tenant'ning hujjati
            #       (bir xil `_id` + `_project_id`) allaqachon bor → o'tkazib yuboramiz.
            #   (b) boshqa tenant bilan `_id` to'qnashuvi (template-copy `_id` ni
            #       saqlagan) → yangi `_id` bilan qayta kiritamiz.
            doc_id = doc.get("_id")
            tenant = doc.get(TENANT_FIELD)
            already = doc_id is not None and dest.count_documents(
                {"_id": doc_id, TENANT_FIELD: tenant}, limit=1
            )
            if already:
                dup += 1
                continue

            doc.pop("_id", None)  # Mongo yangi `_id` beradi
            try:
                dest.insert_one(doc)
                copied += 1
                regen += 1
            except DuplicateKeyError:
                # Yangi `_id` ham to'qnashsa (deyarli imkonsiz) — o'tkazib yuboramiz.
                dup += 1
        return copied, dup, regen
