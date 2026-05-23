# type: ignore
import pymongo
from typing import Optional, List, Dict, Any, Tuple
from config.env import env


class MongoDBClient:
    """MongoDB client wrapper with dependency injection support"""

    def __init__(self, connection_string: Optional[str] = None):
        """Initialize MongoDB client

        Args:
            connection_string: MongoDB connection string. If None, uses env variable.
        """
        self.connection_string = connection_string or env.str("MONGO_URL")
        self._client = None
        self._admin_client = None

    @property
    def client(self) -> pymongo.MongoClient:
        """Get MongoDB client instance (lazy loading)"""
        if self._client is None:
            self._client = pymongo.MongoClient(self.connection_string, maxPoolSize=20, minPoolSize=2)
        return self._client

    @property
    def admin_client(self) -> pymongo.MongoClient:
        """Get admin MongoDB client for user management"""
        if self._admin_client is None:
            self._admin_client = pymongo.MongoClient(self.connection_string, maxPoolSize=5)
        return self._admin_client

    def get_project_database(self, project_id: int):
        """Get MongoDB database for specific project

        Args:
            project_id: ProjectModel ID

        Returns:
            MongoDB database instance
        """
        db_name = f"project_{project_id}"
        return self.client[db_name]

    def create_project_user(self, project_id: int, password: Optional[str] = None) -> Dict[str, str]:
        """Create MongoDB user for project with restricted access

        Args:
            project_id: ProjectModel ID
            password: User password. If None, generates random password.

        Returns:
            Dict with username, password, and database name
        """
        import secrets
        import string

        db_name = f"project_{project_id}"
        username = f"project_{project_id}_user"

        # Generate secure password if not provided
        if password is None:
            alphabet = string.ascii_letters + string.digits
            password = "".join(secrets.choice(alphabet) for _ in range(32))

        # Get admin database
        admin_db = self.admin_client.admin

        # Check if user already exists
        existing_users = admin_db.command("usersInfo", username)
        if existing_users.get("users"):
            # Update existing user password
            admin_db.command("updateUser", username, pwd=password, roles=[{"role": "readWrite", "db": db_name}])
        else:
            # Create new user with access only to specific database
            admin_db.command("createUser", username, pwd=password, roles=[{"role": "readWrite", "db": db_name}])

        return {
            "username": username,
            "password": password,
            "database": db_name,
            "connection_string": self._build_connection_string(username, password, db_name),
        }

    def _build_connection_string(self, username: str, password: str, database: str) -> str:
        """Build MongoDB connection string for project user

        Args:
            username: MongoDB username
            password: MongoDB password
            database: Database name

        Returns:
            Connection string
        """
        # Parse original connection string
        from urllib.parse import quote_plus, urlparse

        parsed = urlparse(self.connection_string)
        host = parsed.hostname or "localhost"
        port = parsed.port or 27017

        # Build new connection string with project user credentials
        return f"mongodb://{quote_plus(username)}:{quote_plus(password)}@{host}:{port}/{database}?authSource=admin"

    def delete_project_user(self, project_id: int):
        """Delete MongoDB user for project

        Args:
            project_id: ProjectModel ID
        """
        username = f"project_{project_id}_user"
        admin_db = self.admin_client.admin

        try:
            admin_db.command("dropUser", username)
        except Exception as e:
            import logging

            logging.warning(f"Failed to delete MongoDB user {username}: {e}")

    def close(self):
        """Close MongoDB connection"""
        if self._client:
            self._client.close()
            self._client = None
        if self._admin_client:
            self._admin_client.close()
            self._admin_client = None


class MongoRepository:
    """MongoDB repository for CRUD operations on collections

    This class provides database operations with dependency injection support.
    Each instance works with a specific CollectionModel.
    """

    def __init__(self, collection_model, mongo_client: Optional[MongoDBClient] = None):
        """Initialize repository

        Args:
            collection_model: CollectionModel instance
            mongo_client: MongoDBClient instance. If None, creates default.
        """
        self.collection_model = collection_model
        self.mongo_client = mongo_client or MongoDBClient()

    @property
    def collection(self):
        """Get MongoDB collection instance

        Returns:
            MongoDB collection
        """
        db = self.mongo_client.get_project_database(self.collection_model.project_id)
        return db[self.collection_model.name]

    def insert_one(self, data: dict) -> str:
        """Insert one document

        Args:
            data: Document data

        Returns:
            Inserted document ID
        """
        result = self.collection.insert_one(data)
        return result.inserted_id

    def insert_if_not_exists(self, data: dict, where: dict) -> Tuple[Optional[str], bool]:
        """Insert document if it doesn't exist

        Args:
            data: Document data
            where: Query filter to check existence

        Returns:
            Tuple of (inserted_id, created_flag)
        """
        if self.collection.count_documents(where) != 0:
            return None, False
        result = self.collection.insert_one(data)
        return result.inserted_id, True

    def find_one(self, where: dict) -> Optional[dict]:
        """Find one document

        Args:
            where: Query filter

        Returns:
            Document or None
        """
        return self.collection.find_one(where)

    def find(
        self,
        where: Optional[dict] = None,
        limit: Optional[int] = None,
        skip: Optional[int] = None,
        sort: Optional[List] = None,
    ) -> List[dict]:
        """Find documents with pagination and sorting

        Args:
            where: Query filter
            limit: Limit results
            skip: Skip documents
            sort: Sort specification

        Returns:
            List of documents
        """
        where = where or {}
        cursor = self.collection.find(where)

        if skip is not None and skip > 0:
            cursor = cursor.skip(skip)
        if limit is not None and limit > 0:
            cursor = cursor.limit(limit)
        if sort is not None:
            cursor = cursor.sort(sort)

        return list(cursor)

    def update(self, where: dict, data: dict):
        """Update documents

        Args:
            where: Query filter
            data: Update data

        Returns:
            Update result
        """
        return self.collection.update_many(where, data)

    def delete(self, where: dict):
        """Delete documents

        Args:
            where: Query filter

        Returns:
            Delete result
        """
        return self.collection.delete_many(where)

    def count(self, where: dict) -> int:
        """Count documents

        Args:
            where: Query filter

        Returns:
            Document count
        """
        return self.collection.count_documents(where)

    def aggregate(self, pipeline: List[dict]) -> List[dict]:
        """Run aggregation pipeline

        Args:
            pipeline: Aggregation pipeline

        Returns:
            Aggregation result
        """
        return list(self.collection.aggregate(pipeline))

    def drop(self):
        """Drop collection

        Returns:
            Drop result
        """
        return self.collection.drop()


class MongoService:
    """High-level MongoDB service for project and collection management"""

    def __init__(self, mongo_client: Optional[MongoDBClient] = None):
        """Initialize service

        Args:
            mongo_client: MongoDBClient instance. If None, creates default.
        """
        self.mongo_client = mongo_client or MongoDBClient()

    def get_repository(self, collection_model) -> MongoRepository:
        """Get repository for a collection

        Args:
            collection_model: CollectionModel instance

        Returns:
            MongoRepository instance
        """
        return MongoRepository(collection_model, self.mongo_client)

    def delete_project_database(self, project_id: int):
        """Delete entire database for a project

        Args:
            project_id: ProjectModel ID
        """
        db_name = f"project_{project_id}"
        self.mongo_client.client.drop_database(db_name)

    def get_project_collection(self, project):
        """Get 'users' collection for a project

        Args:
            project: ProjectModel instance

        Returns:
            CollectionModel or None
        """
        from core.apps.cms_legacy.models.cms import CollectionModel

        try:
            return CollectionModel.objects.get(project=project, name="users")
        except CollectionModel.DoesNotExist:
            return None


# Singleton instance for backward compatibility
_default_client = MongoDBClient()
_default_service = MongoService(_default_client)


# Legacy function wrappers for backward compatibility
# These delegate to the class-based implementation


def get_repository(collection_model) -> MongoRepository:
    """Get repository for a collection (legacy wrapper)

    Args:
        collection_model: CollectionModel instance

    Returns:
        MongoRepository instance
    """
    return _default_service.get_repository(collection_model)


def insert_one(collection_model, data: dict) -> str:
    """Insert one document (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.insert_one(data)


def insert_if_not_exists(collection_model, validated_data: dict) -> Tuple[Optional[str], bool]:
    """Insert if not exists (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.insert_if_not_exists(validated_data.get("data"), validated_data.get("where"))


def find_one(collection_model, where: dict) -> Optional[dict]:
    """Find one document (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.find_one(where)


def find(collection_model, where=None, limit=None, _sort=None, skip: int = None) -> List[dict]:
    """Find documents (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.find(where=where, limit=limit, sort=_sort, skip=skip)


def update(collection_model, where: dict = {}, data: dict = {}):
    """Update documents (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.update(where, data)


def delete(collection_model, where: dict = {}):
    """Delete documents (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.delete(where)


def count_document(collection_model, query: dict) -> int:
    """Count documents (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.count(query)


def aggregate(collection_model, query: List[dict]) -> List[dict]:
    """Aggregate (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.aggregate(query)


def delete_collection(collection_model):
    """Delete collection (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.drop()


def delete_project_database(project_id: int):
    """Delete project database (legacy wrapper)"""
    return _default_service.delete_project_database(project_id)


def get_project_collection(project):
    """Get project collection (legacy wrapper)"""
    return _default_service.get_project_collection(project)


def get_collection_name(collection):
    """Get collection name (legacy wrapper)

    Args:
        collection: CollectionModel instance

    Returns:
        Collection name
    """
    return collection.name


def get_project_database(project_id: int):
    """Get project database (legacy wrapper)"""
    return _default_client.get_project_database(project_id)


def get_db_collection(collection_model):
    """Get database collection (legacy wrapper)"""
    repo = get_repository(collection_model)
    return repo.collection
