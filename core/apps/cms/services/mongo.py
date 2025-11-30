# type: ignore
from django.db.models.expressions import Col
import pymongo
from config.env import env
from core.apps.api.models.project import ProjectModel
from core.apps.cms.models.cms import CollectionModel


client = pymongo.MongoClient(env.str("MONGO_URL"))
db = client["botmother"]


def insert_one(collection, data: dict):
    collection = db[collection]
    return collection.insert_one(data).inserted_id


def insert_if_not_exists(collection, validated_data: dict) -> (str, bool):
    data = validated_data.get("data")
    where = validated_data.get("where")
    collection = db[collection]
    if collection.count_documents(where) != 0:
        return None, False
    return collection.insert_one(data).inserted_id, True


def find_one(collection, where: dict):
    collection = db[collection]
    return collection.find_one(where)


def update(collection, where: dict = {}, data: dict = {}):
    collection = db[collection]
    return collection.update_many(where, data)


def delete(collection, where: dict = {}):
    collection = db[collection]
    return collection.delete_many(where)


def find(collection, where=None, limit=None, _sort=None, skip: int = None):
    if where is None:
        where = dict()
    collection = db[collection]
    cursor = collection.find(where)
    if limit is not None and limit > 0:
        cursor = cursor.limit(limit)
    if skip is not None and skip > 0:
        cursor = cursor.skip(skip)
    if _sort is not None:
        cursor = cursor.sort(_sort)
    return list(cursor)


def aggregate(collection, query: list):
    return db[collection].aggregate(query)


def get_collection_name(collection: CollectionModel) -> str:
    return "collection_%s_%s_%s" % (collection.user_id, collection.project_id, collection.name)


def get_project_collection(project: ProjectModel):
    try:
        return CollectionModel.objects.get(project=project, name="users")
    except CollectionModel.DoesNotExist:
        return None


def delete_collection(collection):
    return db[collection].drop()


def count_document(collection, query) -> int:
    """count data count

    Args:
        collection (collection name): [TODO:description]
        query (where query): [TODO:description]

    Returns:
        int
    """
    return db[collection].count_documents(query)
