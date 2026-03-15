import json
import logging
from typing import Tuple, Optional

from bson import ObjectId, json_util
from core.apps.cms.enums.cms import FieldType
from core.apps.cms.services.collection import collection_validate_data
from core.apps.cms.services.mongo import MongoRepository, MongoService

logger = logging.getLogger(__name__)


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

    def _resolve_relations(self, doc: dict) -> dict:
        """Resolve relation field values to include the primary field from the related collection.

        For each RELATION field in the collection schema, replaces a bare ObjectId string
        (or an existing ``{_id, ...}`` dict) with ``{_id: <id>, primary: <primary_field_value>}``.
        If the related collection has no primary field, or the related document is not found,
        the original value is left unchanged.

        Args:
            doc: A MongoDB document dict (may be mutated in place).

        Returns:
            The same dict with relation fields resolved.
        """
        relation_fields = (
            self.collection_model.fields
            .filter(type=FieldType.RELATION.value)
            .select_related("relation_collection")
        )

        for field in relation_fields:
            raw_value = doc.get(field.name)
            if raw_value is None or field.relation_collection is None:
                continue

            # Determine the ObjectId string from the stored value
            if isinstance(raw_value, str):
                related_id_str = raw_value
            elif isinstance(raw_value, dict) and "_id" in raw_value:
                related_id_str = str(raw_value["_id"])
            elif isinstance(raw_value, ObjectId):
                related_id_str = str(raw_value)
            else:
                continue

            # Find the primary field of the related collection
            primary_field = field.relation_collection.fields.filter(is_primary=True).first()
            if primary_field is None:
                continue

            # Fetch the related document from MongoDB
            try:
                related_repo = self.mongo_service.get_repository(field.relation_collection)
                related_doc = related_repo.find_one({"_id": ObjectId(related_id_str)})
                if related_doc is not None:
                    doc[field.name] = {
                        "_id": related_id_str,
                        "primary": related_doc.get(primary_field.name),
                    }
            except Exception as exc:
                logger.warning(
                    "Failed to resolve relation field '%s' with id '%s': %s",
                    field.name,
                    related_id_str,
                    exc,
                )

        return doc

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
        resolved = [self._resolve_relations(doc) for doc in data]
        return json.loads(json_util.dumps(resolved)), 200

    def find_one(self) -> Tuple[dict, int]:
        """Find one document in collection

        Returns:
            Tuple of (response_data, status_code)
        """
        data = self.repository.find_one(where=self.data.get("where", {}))
        if data is None:
            return {"detail": "Not found"}, 404
        data = self._resolve_relations(data)
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
