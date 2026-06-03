"""Eski keyboard formatini yangi keyboard_kind + rows formatiga o'tkazadi.

Eski format (node.data):
    "keyboard": {
        "active": "inline" | "reply",
        "inline": [[btn, ...], ...],
        "reply":  [[btn, ...], ...],
        "replyOptions": {...}
    }

Yangi format (constructor panel + engine normalize qo'llaydi):
    "keyboard_kind": "inline" | "reply",
    "rows": [{"columns": [btn, ...]}, ...]

Reply button: {request_contact: true} → {type: "request_contact"}
            {request_location: true} → {type: "request_location"}

Engine `normalizeKeyboardData` yangi `rows`ni avtomatik legacy shaklga
aylantirib o'qiydi — shuning uchun deploy qilingan botlar BUZILMAYDI.

Idempotent: `keyboard_kind` allaqachon bor node skip qilinadi.

Foydalanish:
    python manage.py migrate_keyboard_format --dry-run        # faqat ko'rsatadi
    python manage.py migrate_keyboard_format                  # ProjectModel.flow
    python manage.py migrate_keyboard_format --project-id 1194 --dry-run
"""

from __future__ import annotations

import copy

from django.core.management.base import BaseCommand

from core.apps.api.models.project import ProjectModel


def _convert_button(btn: dict) -> dict:
    """Reply button'ning request_contact/location bool field'ini type'ga ko'chiradi."""
    if not isinstance(btn, dict):
        return btn
    b = dict(btn)
    if b.get("request_contact") is True and not b.get("type"):
        b["type"] = "request_contact"
    if b.get("request_location") is True and not b.get("type"):
        b["type"] = "request_location"
    return b


def _migrate_node_data(data: dict) -> bool:
    """Bitta node.data'ni joyida (in-place) yangilaydi. O'zgardimi — qaytaradi."""
    if not isinstance(data, dict):
        return False
    # Allaqachon yangi format → skip (idempotent)
    if "keyboard_kind" in data or "rows" in data:
        return False
    kb = data.get("keyboard")
    if not isinstance(kb, dict) or "active" not in kb:
        return False

    active = kb.get("active") or "inline"
    if active not in ("inline", "reply"):
        active = "inline"
    button_rows = kb.get(active) or []

    rows = []
    for row in button_rows:
        if not isinstance(row, list) or not row:
            continue
        rows.append({"columns": [_convert_button(b) for b in row]})

    data["keyboard_kind"] = active
    data["rows"] = rows
    del data["keyboard"]
    return True


def _migrate_flow(flow) -> tuple[object, int]:
    """Flow (dict yoki list) ichidagi barcha node'larni migratsiya qiladi.

    Returns (yangi_flow, o'zgargan_node_soni).
    """
    new_flow = copy.deepcopy(flow)
    if isinstance(new_flow, dict):
        nodes = new_flow.get("nodes", [])
    elif isinstance(new_flow, list):
        nodes = new_flow
    else:
        return flow, 0

    changed = 0
    for node in nodes:
        if isinstance(node, dict) and _migrate_node_data(node.get("data") or {}):
            changed += 1
    return new_flow, changed


class Command(BaseCommand):
    help = "Eski keyboard formatini keyboard_kind + rows formatiga o'tkazadi"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Faqat ko'rsatadi, saqlamaydi")
        parser.add_argument("--project-id", type=int, default=None, help="Faqat shu loyiha")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        pid = opts["project_id"]

        qs = ProjectModel.objects.all()
        if pid is not None:
            qs = qs.filter(id=pid)

        total_projects = 0
        changed_projects = 0
        total_nodes = 0
        sample_shown = False

        for project in qs.iterator():
            flow = project.flow
            if not flow:
                continue
            total_projects += 1
            new_flow, changed = _migrate_flow(flow)
            if changed == 0:
                continue
            changed_projects += 1
            total_nodes += changed

            # Birinchi o'zgargan loyiha uchun before/after namuna
            if not sample_shown and dry:
                self.stdout.write(self.style.WARNING(
                    f"\n=== NAMUNA: project_id={project.id} ({changed} node o'zgaradi) ==="
                ))
                old_nodes = (flow.get("nodes") if isinstance(flow, dict) else flow) or []
                new_nodes = (new_flow.get("nodes") if isinstance(new_flow, dict) else new_flow) or []
                for o, n in zip(old_nodes, new_nodes):
                    if (o.get("data") or {}).get("keyboard") and (n.get("data") or {}).get("rows") is not None:
                        import json
                        self.stdout.write("BEFORE keyboard: " + json.dumps((o["data"]).get("keyboard"), ensure_ascii=False)[:300])
                        self.stdout.write("AFTER  kind:     " + json.dumps((n["data"]).get("keyboard_kind"), ensure_ascii=False))
                        self.stdout.write("AFTER  rows:     " + json.dumps((n["data"]).get("rows"), ensure_ascii=False)[:300])
                        sample_shown = True
                        break

            if not dry:
                project.flow = new_flow
                project.save(update_fields=["flow"])

        mode = "DRY-RUN (saqlanmadi)" if dry else "SAQLANDI"
        self.stdout.write(self.style.SUCCESS(
            f"\n[{mode}] {changed_projects}/{total_projects} loyiha, {total_nodes} ta node migratsiya qilindi."
        ))
