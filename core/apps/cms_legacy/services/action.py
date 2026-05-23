import json
from typing import Tuple, Optional

from bson import json_util
from core.apps.cms_legacy.services.collection import collection_validate_data
from core.apps.cms_legacy.services.mongo import MongoRepository, MongoService


class ActionService:
    """Service for CMS collection CRUD actions with dependency injection"""

    def __init__(self, collection_model, validated_data: dict, mongo_service: Optional[MongoService] = None):
        """Initialize action service
        
        Args:
            collection_model: CollectionModel instance
            validated_data: Request data
            mongo_service: MongoService instance (optional, for DI)
        """
        self.collection_model = collection_model
        self.data = validated_data
        self.mongo_service = mongo_service or MongoService()
        self._repository: Optional[MongoRepository] = None

    @property
    def repository(self) -> MongoRepository:
        """Get MongoDB repository (lazy loading)"""
        if self._repository is None:
            self._repository = self.mongo_service.get_repository(self.collection_model)
        return self._repository

    def insert(self) -> Tuple[dict, int]:
        """Insert document into collection
        
        Returns:
            Tuple of (response_data, status_code)
        """
        errors, success = collection_validate_data(self.collection_model, self.data)
        if not success:
            return errors, 400
        inserted_id = self.repository.insert_one(self.data)
        return {"inserted_id": str(inserted_id)}, 200

    def find(self) -> Tuple[dict, int]:
        """Find documents in collection
        
        Returns:
            Tuple of (response_data, status_code)
        """
        data = self.repository.find(
            where=self.data.get("where", {}),
            limit=self.data.get("limit", None),
            sort=self.data.get("sort", None),
            skip=self.data.get("skip", None),
        )
        return json.loads(json_util.dumps(data)), 200

    def find_one(self) -> Tuple[dict, int]:
        """Find one document in collection
        
        Returns:
            Tuple of (response_data, status_code)
        """
        data = self.repository.find_one(where=self.data.get("where", {}))
        if data is None:
            return {"detail": "Not found"}, 404
        return json.loads(json_util.dumps(data)), 200

    def delete(self) -> Tuple[dict, int]:
        """Delete documents from collection
        
        Returns:
            Tuple of (response_data, status_code)
        """
        res = self.repository.delete(self.data.get("where", {}))
        return {"deleted_count": res.deleted_count}, 200

    def update(self) -> Tuple[dict, int]:
        """Update documents in collection
        
        Returns:
            Tuple of (response_data, status_code)
        """
        res = self.repository.update(self.data.get("where", {}), self.data.get("data"))
        return {"modified_count": res.modified_count}, 200

    def count(self) -> Tuple[dict, int]:
        """Count documents in collection
        
        Returns:
            Tuple of (response_data, status_code)
        """
        count = self.repository.count(self.data.get("where", {}))
        return {"count": count}, 200

    def insert_if_not_exists(self) -> Tuple[dict, int]:
        """Insert document if it doesn't exist
        
        Returns:
            Tuple of (response_data, status_code)
        """
        errors, success = collection_validate_data(self.collection_model, self.data.get("data"))
        if not success:
            return errors, 400
        inserted_id, created = self.repository.insert_if_not_exists(
            self.data.get("data"),
            self.data.get("where")
        )
        return {
            "inserted_id": str(inserted_id) if inserted_id else None,
            "created": created,
        }, 200
