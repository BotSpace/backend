from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from django.core.cache import cache

from core.apps.cms_legacy.services.mongo import MongoDBClient, MongoRepository

logger = logging.getLogger(__name__)

OVERVIEW_CACHE_TTL = 300  # 5 daqiqa


def _overview_cache_key(user_id: int) -> str:
    return f"dashboard_overview_user_{user_id}"


class OverviewService:
    """Dashboard overview aggregate service.

    Collects cross-project stats for a single user and returns a dict
    matching the /api/v1/dashboard/overview/ JSON contract.
    """

    def __init__(self, user) -> None:
        self.user = user

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get(self) -> dict[str, Any]:
        key = _overview_cache_key(self.user.pk)
        cached = cache.get(key)
        if cached is not None:
            return cached

        result = self._build()
        cache.set(key, result, OVERVIEW_CACHE_TTL)
        return result

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build(self) -> dict[str, Any]:
        from core.apps.api.models.project import ProjectModel, RelaseModel
        from core.apps.cms_legacy.models.cms import CollectionModel
        from core.apps.template.models.order import TemplateOrderModel

        projects = list(
            ProjectModel.objects.filter(owner=self.user, deleted_at__isnull=True).only("id", "name")
        )
        project_ids = [p.pk for p in projects]
        total_bots = len(project_ids)

        # active_bots — loyihalarda kamida bitta release bor
        active_bot_ids = set(
            RelaseModel.objects.filter(project_id__in=project_ids).values_list("project_id", flat=True).distinct()
        )
        active_bots = len(active_bot_ids)

        # templates — foydalanuvchining o'z shablonlari (sotib olgan / order qilgan)
        try:
            templates_count = TemplateOrderModel.objects.filter(user=self.user).count()
        except Exception:
            templates_count = 0

        # revenue field — foydalanuvchi balansi (UI'da "Balans" deb ko'rsatiladi)
        revenue = int(getattr(self.user, "balance", 0) or 0)

        # Agar loyihalar bo'lmasa, MongoDB ga bormaymiz
        if not project_ids:
            return self._empty_response(
                total_bots=total_bots,
                active_bots=active_bots,
                templates=templates_count,
                revenue=revenue,
            )

        # CollectionModel.objects — users va chat collectionlari
        users_collections = {
            col.project_id: col
            for col in CollectionModel.objects.filter(project_id__in=project_ids, name="users").select_related()
        }
        chat_collections = {
            col.project_id: col
            for col in CollectionModel.objects.filter(project_id__in=project_ids, name="chat").select_related()
        }

        mongo_client = MongoDBClient()
        try:
            result = self._aggregate_mongo(
                projects=projects,
                users_collections=users_collections,
                chat_collections=chat_collections,
                mongo_client=mongo_client,
                total_bots=total_bots,
                active_bots=active_bots,
                templates=templates_count,
                revenue=revenue,
            )
        except Exception:
            logger.exception("OverviewService: MongoDB aggregation failed, returning zeros")
            result = self._empty_response(
                total_bots=total_bots,
                active_bots=active_bots,
                templates=templates_count,
                revenue=revenue,
            )
        finally:
            try:
                mongo_client.close()
            except Exception:
                pass

        return result

    def _aggregate_mongo(
        self,
        *,
        projects,
        users_collections: dict,
        chat_collections: dict,
        mongo_client: MongoDBClient,
        total_bots: int,
        active_bots: int,
        templates: int,
        revenue: int,
    ) -> dict[str, Any]:
        # Oxirgi 30 kun oralig'i
        utc = timezone.utc
        now_utc = datetime.now(utc)
        thirty_days_ago = now_utc - timedelta(days=30)

        total_users = 0
        total_messages = 0

        # top_bots uchun: project_id -> {messages, users}
        project_stats: dict[int, dict] = {}

        # performance: date -> count
        daily_new_users: dict[str, int] = {}

        # distribution: type -> count
        distribution: dict[str, int] = {"private": 0, "group": 0, "channel": 0, "other": 0}

        for project in projects:
            pid = project.pk

            # --- users collection ---
            users_col = users_collections.get(pid)
            project_user_count = 0
            if users_col:
                try:
                    users_repo = MongoRepository(users_col, mongo_client)

                    # total users
                    project_user_count = users_repo.count({})
                    total_users += project_user_count

                    # performance: kunlik yangi foydalanuvchilar (oxirgi 30 kun)
                    daily_pipeline = [
                        {"$match": {"created_at": {"$gte": thirty_days_ago}}},
                        {
                            "$project": {
                                "day": {
                                    "$dateToString": {
                                        "format": "%Y-%m-%d",
                                        "date": "$created_at",
                                    }
                                }
                            }
                        },
                        {"$group": {"_id": "$day", "total": {"$sum": 1}}},
                    ]
                    for item in users_repo.aggregate(daily_pipeline):
                        day = item.get("_id")
                        if day:
                            daily_new_users[day] = daily_new_users.get(day, 0) + item.get("total", 0)

                    # distribution: type field bo'yicha
                    dist_pipeline = [
                        {"$group": {"_id": "$type", "count": {"$sum": 1}}},
                    ]
                    for item in users_repo.aggregate(dist_pipeline):
                        raw_type = item.get("_id")
                        count = item.get("count", 0)
                        if raw_type is None:
                            # type maydoni yo'q — private ga qo'shamiz
                            distribution["private"] += count
                        else:
                            norm = str(raw_type).lower()
                            if norm in distribution:
                                distribution[norm] += count
                            else:
                                distribution["other"] += count

                except Exception:
                    logger.exception("OverviewService: failed to query users collection for project %s", pid)

            # --- chat collection (messages) ---
            chat_col = chat_collections.get(pid)
            project_msg_count = 0
            if chat_col:
                try:
                    chat_repo = MongoRepository(chat_col, mongo_client)
                    project_msg_count = chat_repo.count({})
                    total_messages += project_msg_count
                except Exception:
                    logger.exception("OverviewService: failed to query chat collection for project %s", pid)

            project_stats[pid] = {
                "id": pid,
                "name": project.name,
                "messages": project_msg_count,
                "users": project_user_count,
            }

        # performance — tartiblangan
        performance = sorted(
            [{"date": d, "value": v} for d, v in daily_new_users.items()],
            key=lambda x: x["date"],
        )

        # top_bots — messages bo'yicha kamayuvchi, top 5
        sorted_projects = sorted(project_stats.values(), key=lambda x: x["messages"], reverse=True)
        top_bots = [
            {
                "id": p["id"],
                "name": p["name"],
                "messages": p["messages"],
                "delta": None,
            }
            for p in sorted_projects[:5]
        ]

        return {
            "totals": {
                "bots": total_bots,
                "active_bots": active_bots,
                "users": total_users,
                "messages": total_messages,
                "templates": templates,
                "revenue": revenue,
                "currency": "UZS",
            },
            "performance": performance,
            "top_bots": top_bots,
            "distribution": distribution,
        }

    @staticmethod
    def _empty_response(
        *,
        total_bots: int = 0,
        active_bots: int = 0,
        templates: int = 0,
        revenue: int = 0,
    ) -> dict[str, Any]:
        return {
            "totals": {
                "bots": total_bots,
                "active_bots": active_bots,
                "users": 0,
                "messages": 0,
                "templates": templates,
                "revenue": revenue,
                "currency": "UZS",
            },
            "performance": [],
            "top_bots": [],
            "distribution": {"private": 0, "group": 0, "channel": 0, "other": 0},
        }
