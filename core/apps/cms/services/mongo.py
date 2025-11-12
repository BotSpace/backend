# type: ignore
import pymongo
from config.env import env
from core.apps.cms.models.cms import CollectionModel


client = pymongo.MongoClient(env.str("MONGO_URL"))
db = client["botmother"]


def insert_one(collection, data: dict):
    collection = db[collection]
    return collection.insert_one(data).inserted_id


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
    return "collection_%s_%s_%s" % (collection.user.pk, collection.project.pk, collection.name)
