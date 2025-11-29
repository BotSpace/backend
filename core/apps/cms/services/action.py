import json

from bson import json_util
from core.apps.cms.services.collection import collection_validate_data
from core.apps.cms.services.mongo import (
    count_document,
    delete,
    find,
    find_one,
    get_collection_name,
    insert_if_not_exists,
    insert_one,
    update,
)
from typing import Tuple
from django.core.files.uploadedfile import UploadedFile
from django.core.files.storage import default_storage


class ActionService:

    def __init__(self, instance, validated_data) -> None:
        self.instance = instance
        self.data = validated_data
        self.collection_name = get_collection_name(instance)

    def insert(self) -> Tuple[dict, int]:
        errors, success = collection_validate_data(self.instance, self.data)
        if not success:
            return errors, 400
        self._upload_file()
        inserted_id = insert_one(self.collection_name, self.data)
        return {"inserted_id": str(inserted_id)}, 200

    def find(self) -> Tuple[dict, int]:
        data = find(
            self.collection_name,
            where=self.data.get("where", {}),
            limit=self.data.get("limit", None),
            _sort=self.data.get("sort", None),
            skip=self.data.get("skip", None),
        )
        return json.loads(json_util.dumps(data)), 200

    def find_one(self) -> Tuple[dict, int]:
        data = find_one(self.collection_name, where=self.data.get("where", {}))
        if data is None:
            return {"detail": "Not found"}, 404
        return json.loads(json_util.dumps(data)), 200

    def delete(self):
        res = delete(self.collection_name, self.data.get("where", {}))
        return {"deleted_count": res.deleted_count}, 200

    def update(self) -> Tuple[dict, int]:
        res = update(self.collection_name, self.data.get("where", {}), self.data.get("data"))
        return {"modified_count": res.modified_count}, 200

    def count(self) -> Tuple[dict, int]:
        count = count_document(self.collection_name, self.data.get("where", {}))
        return {"count": count}, 200

    def insert_if_not_exists(self) -> Tuple[dict, int]:
        errors, success = collection_validate_data(self.instance, self.data.get("data"))
        if not success:
            return errors, 400
        inserted_id, created = insert_if_not_exists(self.collection_name, self.data)
        return {
            "inserted_id": str(inserted_id),
            "created": created,
        }, 200

    def _upload_file(self):
        for field, value in self.data.items():
            if isinstance(value, UploadedFile):
                file_path = default_storage.save(value.name, value)
                self.data[field] = file_path
