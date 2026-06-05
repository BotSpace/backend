"""Running-bot limit check.

"Running bot" — loyiha is_template=False, unda:
  - debug containeri RUNNING yoki INIT (initializing) statusda, YOKI
  - biror release INIT yoki RUNNING statusda.

Bir loyiha bir marta sanaladi.

Tekshirish: target loyihani chiqarib tashlagan holda (u allaqachon running bo'lsa
bloklanmaydi — qayta deploy o'z containerini almashtiradi).
"""

from __future__ import annotations

from django.contrib.auth import get_user_model

from core.apps.api.enums.container import ContainerStatusEnum

User = get_user_model()

# Debug statuslari — running hisobinatadi
_DEBUG_ACTIVE = {ContainerStatusEnum.RUNNING.value, ContainerStatusEnum.INIT.value}
# Release statuslari — running hisoblanadi
_RELEASE_ACTIVE = {ContainerStatusEnum.INIT.value, ContainerStatusEnum.RUNNING.value}


def get_running_bots(user: User, exclude_project_id: int | None = None) -> list[dict]:
    """Foydalanuvchining hozir faol botlari ro'yxatini qaytaradi.

    Har bir yozuv::

        {"project_id": int, "name": str, "kind": "debug" | "release", "release_id": int | None}

    ``release_id`` faqat ``kind="release"`` da bo'ladi.
    """
    from core.apps.api.models.project import DebugModel, ProjectModel, RelaseModel

    # Faqat user'ning is_template=False loyihalari
    qs = ProjectModel.objects.filter(owner=user, is_template=False)
    if exclude_project_id is not None:
        qs = qs.exclude(pk=exclude_project_id)

    project_ids = list(qs.values_list("pk", flat=True))
    if not project_ids:
        return []

    # Loyiha nomi bilan xarita
    name_map: dict[int, str] = dict(
        ProjectModel.objects.filter(pk__in=project_ids).values_list("pk", "name")
    )

    running: list[dict] = []
    seen_project_ids: set[int] = set()

    # Debug containerlari
    for debug in DebugModel.objects.filter(project_id__in=project_ids, status__in=_DEBUG_ACTIVE):
        pid = debug.project_id
        seen_project_ids.add(pid)
        running.append(
            {
                "project_id": pid,
                "name": name_map.get(pid, ""),
                "kind": "debug",
            }
        )

    # Release containerlari (faqat debug'da ko'rinmagan loyihalar uchun ham alohida release yozuvi)
    for release in RelaseModel.objects.filter(project_id__in=project_ids, status__in=_RELEASE_ACTIVE).order_by("id"):
        pid = release.project_id
        # Release ham alohida entry — bir loyihada debug+release bo'lsa 2 ta entry bo'lishi mumkin,
        # lekin distinct loyiha soni limitga kiradi. Shuning uchun biz running ro'yxatiga har birini
        # qo'shamiz (frontend uchun ma'lumot), distinct count esa seen_project_ids orqali hisoblanadi.
        seen_project_ids.add(pid)
        running.append(
            {
                "project_id": pid,
                "name": name_map.get(pid, ""),
                "kind": "release",
                "release_id": release.pk,
            }
        )

    return running


def count_running_projects(user: User, exclude_project_id: int | None = None) -> int:
    """Faol bot loyihalar sonini qaytaradi (distinct project_id)."""
    from core.apps.api.models.project import DebugModel, ProjectModel, RelaseModel

    qs = ProjectModel.objects.filter(owner=user, is_template=False)
    if exclude_project_id is not None:
        qs = qs.exclude(pk=exclude_project_id)

    project_ids = list(qs.values_list("pk", flat=True))
    if not project_ids:
        return 0

    debug_pids = set(
        DebugModel.objects.filter(project_id__in=project_ids, status__in=_DEBUG_ACTIVE).values_list(
            "project_id", flat=True
        )
    )
    release_pids = set(
        RelaseModel.objects.filter(project_id__in=project_ids, status__in=_RELEASE_ACTIVE).values_list(
            "project_id", flat=True
        )
    )
    return len(debug_pids | release_pids)


def check_running_bot_limit(user: User, exclude_project_id: int | None = None) -> None:
    """Limit oshgan bo'lsa ``RunningBotLimitExceeded`` raise qiladi.

    ``exclude_project_id`` — target loyiha ID si (allaqachon running bo'lsa bloklanmasin).
    """
    from django.conf import settings

    from core.apps.api.exceptions.running_bot_limit import RunningBotLimitExceeded

    limit: int = getattr(settings, "RUNNING_BOT_LIMIT", 10)
    running = get_running_bots(user, exclude_project_id=exclude_project_id)

    # Distinct loyiha soni
    distinct_count = len({r["project_id"] for r in running})

    if distinct_count >= limit:
        raise RunningBotLimitExceeded(limit=limit, running=running)
