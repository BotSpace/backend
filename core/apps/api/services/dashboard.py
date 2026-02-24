from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict

from django.core.cache import cache

from core.apps.cms.services.mongo import MongoRepository, MongoService

DASHBOARD_CACHE_TTL = 300  # 5 daqiqa


class DashboardService:
    """Dashboard analytics service with dependency injection"""

    def __init__(self, mongo_service: Optional[MongoService] = None):
        """Initialize dashboard service
        
        Args:
            mongo_service: MongoService instance (optional, for DI)
        """
        self.mongo_service = mongo_service or MongoService()
        self._collection_model = None
        self._repository: Optional[MongoRepository] = None

    def set_collection(self, collection_model):
        """Set collection model for dashboard
        
        Args:
            collection_model: CollectionModel instance
        """
        self._collection_model = collection_model
        self._repository = None  # Reset repository when collection changes

    @property
    def repository(self) -> MongoRepository:
        """Get MongoDB repository (lazy loading)
        
        Returns:
            MongoRepository instance
            
        Raises:
            ValueError: If collection not set
        """
        if self._collection_model is None:
            raise ValueError("Collection not set. Call set_collection() first.")
        
        if self._repository is None:
            self._repository = self.mongo_service.get_repository(self._collection_model)
        
        return self._repository

    def _cache_key(self, metric: str) -> str:
        return f"dashboard_{self._collection_model.pk}_{metric}"

    def users_count(self) -> int:
        """Get total users count

        Returns:
            int: Total users count
        """
        key = self._cache_key("users_count")
        cached = cache.get(key)
        if cached is not None:
            return cached

        users = self.repository.aggregate([
            {"$group": {"_id": None, "total": {"$sum": 1}}}
        ])
        result = 0 if len(users) <= 0 else users[0].get("total", 0)
        cache.set(key, result, DASHBOARD_CACHE_TTL)
        return result

    def daily_users(self) -> int:
        """Get today's new users count
        
        Returns:
            int: Today's users count
        """
        key = self._cache_key("daily_users")
        cached = cache.get(key)
        if cached is not None:
            return cached

        utc5 = timezone(timedelta(hours=5))
        today_local = datetime.now(utc5).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_local = today_local + timedelta(days=1)
        today = today_local.astimezone(timezone.utc)
        tomorrow = tomorrow_local.astimezone(timezone.utc)
        
        result = self.repository.count({
            "created_at": {
                "$gte": today,
                "$lt": tomorrow,
            }
        })
        cache.set(key, result, DASHBOARD_CACHE_TTL)
        return result

    def get_user_chart(self) -> List[Dict[str, any]]:
        """Get new users chart data grouped by date

        Returns:
            List of dicts with 'date' and 'value' keys
        """
        key = self._cache_key("user_chart")
        cached = cache.get(key)
        if cached is not None:
            return cached

        data = self.repository.aggregate([
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
            {
                "$group": {
                    "_id": "$day",
                    "total": {"$sum": 1},
                },
            },
            {
                "$sort": {"_id": 1},
            },
        ])

        result = [
            {"date": item.get("_id"), "value": item.get("total")}
            for item in data
        ]
        cache.set(key, result, DASHBOARD_CACHE_TTL)
        return result
