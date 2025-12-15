"""
Test for MongoDB class-based implementation with dependency injection
"""

import pytest
from unittest.mock import patch, MagicMock
from core.apps.api.services.project import create_default_collections
from core.apps.cms.models import CollectionModel
from core.apps.cms.services.mongo import (
    MongoDBClient,
    MongoRepository,
    MongoService,
)
from core.apps.api.models import ProjectModel
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestMongoDBClient:
    """Test MongoDBClient class"""

    @patch("core.apps.cms.services.mongo.pymongo.MongoClient")
    def test_client_lazy_loading(self, mock_mongo_client):
        """Test that client is created lazily"""
        client = MongoDBClient("mongodb://test:27017")

        # Client should not be created yet
        mock_mongo_client.assert_not_called()

        # Access client property
        _ = client.client

        # Now client should be created
        mock_mongo_client.assert_called_once_with("mongodb://test:27017")

    @patch("core.apps.cms.services.mongo.pymongo.MongoClient")
    def test_get_project_database(self, mock_mongo_client):
        """Test getting project database"""
        mock_db = MagicMock()
        mock_mongo_instance = MagicMock()
        mock_mongo_instance.__getitem__.return_value = mock_db
        mock_mongo_client.return_value = mock_mongo_instance

        client = MongoDBClient()
        db = client.get_project_database(5)

        mock_mongo_instance.__getitem__.assert_called_with("project_5")
        assert db == mock_db


@pytest.mark.django_db
class TestMongoRepository:
    """Test MongoRepository class"""

    def test_repository_initialization(self):
        """Test repository initialization with CollectionModel"""
        user = User._create_fake()
        project = ProjectModel._create_fake(owner=user)
        create_default_collections(project)

        # Get the auto-created "users" collection from signal
        collection_model = CollectionModel.objects.get(project=project, name="users")

        repo = MongoRepository(collection_model)

        assert repo.collection_model == collection_model
        assert repo.mongo_client is not None

    @patch("core.apps.cms.services.mongo.MongoDBClient")
    def test_insert_one(self, mock_client_class):
        """Test insert_one method"""
        user = User._create_fake()
        project = ProjectModel._create_fake(owner=user)
        create_default_collections(project)

        # Get auto-created collection
        collection_model = CollectionModel.objects.get(project=project, name="users")

        # Setup mocks
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_result = MagicMock()
        mock_result.inserted_id = "test_id_123"

        mock_collection.insert_one.return_value = mock_result
        mock_db.__getitem__.return_value = mock_collection
        mock_client.get_project_database.return_value = mock_db
        mock_client_class.return_value = mock_client

        # Create repository with mocked client
        repo = MongoRepository(collection_model, mock_client)

        # Insert data
        test_data = {"name": "Test User", "chat_id": 123}
        result = repo.insert_one(test_data)

        # Verify
        mock_collection.insert_one.assert_called_once_with(test_data)
        assert result == "test_id_123"

    @patch("core.apps.cms.services.mongo.MongoDBClient")
    def test_find_with_pagination(self, mock_client_class):
        """Test find with limit and skip"""
        user = User._create_fake()
        project = ProjectModel._create_fake(owner=user)
        create_default_collections(project)

        # Get auto-created collection
        collection_model = CollectionModel.objects.get(project=project, name="users")

        # Setup mocks
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_collection = MagicMock()
        mock_cursor = MagicMock()

        mock_cursor.skip.return_value = mock_cursor
        mock_cursor.limit.return_value = mock_cursor
        mock_cursor.sort.return_value = mock_cursor
        mock_cursor.__iter__.return_value = iter([{"name": "User 1"}, {"name": "User 2"}])

        mock_collection.find.return_value = mock_cursor
        mock_db.__getitem__.return_value = mock_collection
        mock_client.get_project_database.return_value = mock_db
        mock_client_class.return_value = mock_client

        # Create repository
        repo = MongoRepository(collection_model, mock_client)

        # Find with pagination
        result = repo.find(where={"active": True}, limit=10, skip=5)

        # Verify
        mock_collection.find.assert_called_once_with({"active": True})
        mock_cursor.skip.assert_called_once_with(5)
        mock_cursor.limit.assert_called_once_with(10)
        assert len(result) == 2


@pytest.mark.django_db
class TestMongoService:
    """Test MongoService class"""

    def test_get_repository(self):
        """Test getting repository from service"""
        user = User._create_fake()
        project = ProjectModel._create_fake(owner=user)
        create_default_collections(project)

        # Get auto-created collection
        collection_model = CollectionModel.objects.get(project=project, name="users")

        service = MongoService()
        repo = service.get_repository(collection_model)

        assert isinstance(repo, MongoRepository)
        assert repo.collection_model == collection_model

    @patch("core.apps.cms.services.mongo.MongoDBClient")
    def test_delete_project_database(self, mock_client_class):
        """Test deleting project database"""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        service = MongoService(mock_client)
        service.delete_project_database(5)

        mock_client.client.drop_database.assert_called_once_with("project_5")


@pytest.mark.django_db
class TestDependencyInjection:
    """Test dependency injection pattern"""

    @patch("core.apps.cms.services.mongo.pymongo.MongoClient")
    def test_custom_mongo_client_injection(self, mock_mongo_client):
        """Test injecting custom MongoDB client"""
        # Create custom client
        custom_client = MongoDBClient("mongodb://custom:27017")

        # Create service with custom client
        service = MongoService(custom_client)

        assert service.mongo_client == custom_client

    @patch("core.apps.cms.services.mongo.pymongo.MongoClient")
    def test_repository_uses_injected_client(self, mock_mongo_client):
        """Test that repository uses injected client"""
        user = User._create_fake()
        project = ProjectModel._create_fake(owner=user)
        create_default_collections(project)

        # Get auto-created collection
        collection_model = CollectionModel.objects.get(project=project, name="users")

        # Create custom client
        custom_client = MongoDBClient("mongodb://custom:27017")

        # Create repository with custom client
        repo = MongoRepository(collection_model, custom_client)

        assert repo.mongo_client == custom_client
