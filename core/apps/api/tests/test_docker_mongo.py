"""
Test MongoDB user creation and Docker CPU limits
"""
import pytest
from unittest.mock import patch, MagicMock
from core.apps.cms.services.mongo import MongoDBClient
from core.apps.api.models import ProjectModel
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestMongoDBUserManagement:
    """Test MongoDB user creation for projects"""

    @patch('core.apps.cms.services.mongo.pymongo.MongoClient')
    def test_create_project_user(self, mock_mongo_client):
        """Test creating MongoDB user for project"""
        # Setup mock
        mock_admin_db = MagicMock()
        mock_admin = MagicMock()
        mock_admin.admin = mock_admin_db
        mock_admin_db.command.return_value = {"users": []}  # No existing users
        mock_mongo_client.return_value = mock_admin
        
        # Create client and user
        client = MongoDBClient("mongodb://test:27017")
        credentials = client.create_project_user(project_id=5)
        
        # Verify user creation command was called
        mock_admin_db.command.assert_any_call(
            "createUser",
            "project_5_user",
            pwd=credentials["password"],
            roles=[{"role": "readWrite", "db": "project_5"}]
        )
        
        # Verify credentials
        assert credentials["username"] == "project_5_user"
        assert credentials["database"] == "project_5"
        assert len(credentials["password"]) == 32
        assert "mongodb://" in credentials["connection_string"]

    @patch('core.apps.cms.services.mongo.pymongo.MongoClient')
    def test_update_existing_user(self, mock_mongo_client):
        """Test updating existing MongoDB user"""
        # Setup mock - user exists
        mock_admin_db = MagicMock()
        mock_admin = MagicMock()
        mock_admin.admin = mock_admin_db
        mock_admin_db.command.return_value = {
            "users": [{"user": "project_5_user"}]
        }
        mock_mongo_client.return_value = mock_admin
        
        # Create client and update user
        client = MongoDBClient("mongodb://test:27017")
        credentials = client.create_project_user(project_id=5, password="custom_password")
        
        # Verify update command was called
        mock_admin_db.command.assert_any_call(
            "updateUser",
            "project_5_user",
            pwd="custom_password",
            roles=[{"role": "readWrite", "db": "project_5"}]
        )
        
        assert credentials["password"] == "custom_password"

    @patch('core.apps.cms.services.mongo.pymongo.MongoClient')
    def test_delete_project_user(self, mock_mongo_client):
        """Test deleting MongoDB user"""
        mock_admin_db = MagicMock()
        mock_admin = MagicMock()
        mock_admin.admin = mock_admin_db
        mock_mongo_client.return_value = mock_admin
        
        client = MongoDBClient("mongodb://test:27017")
        client.delete_project_user(project_id=5)
        
        # Verify dropUser command
        mock_admin_db.command.assert_called_once_with("dropUser", "project_5_user")

    def test_connection_string_building(self):
        """Test MongoDB connection string building"""
        client = MongoDBClient("mongodb://admin:pass@localhost:27017")
        
        conn_str = client._build_connection_string(
            "project_5_user",
            "secret_pass",
            "project_5"
        )
        
        assert "project_5_user" in conn_str
        assert "secret_pass" in conn_str
        assert "project_5" in conn_str
        assert "mongodb://" in conn_str


@pytest.mark.django_db  
class TestDockerServiceCPULimit:
    """Test Docker service CPU limits"""

    @patch('core.apps.api.services.docker_service.get_client')
    def test_service_created_with_cpu_limit(self, mock_get_client):
        """Test that Docker service is created with CPU limit"""
        from core.apps.api.services.docker_service import create_service
        from docker.types import Resources
        
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.services.create.return_value = mock_service
        mock_get_client.return_value = mock_client
        
        # Create service
        service = create_service("test-image", "test-service")
        
        # Verify create was called
        assert mock_client.services.create.called
        
        # Get call arguments
        call_kwargs = mock_client.services.create.call_args[1]
        
        # Verify resources were set
        assert "resources" in call_kwargs
        resources = call_kwargs["resources"]
        assert isinstance(resources, Resources)

    @patch('core.apps.api.services.docker_service.get_client')
    @patch('core.apps.cms.services.mongo.MongoDBClient')
    def test_deploy_service_with_mongo_credentials(self, mock_mongo_client_class, mock_get_client):
        """Test that deploy_service adds MongoDB credentials to environment"""
        from core.apps.api.services.docker_service import deploy_service
        
        # Setup mocks
        mock_client = MagicMock()
        mock_service = MagicMock()
        mock_client.services.create.return_value = mock_service
        mock_get_client.return_value = mock_client
        
        mock_mongo = MagicMock()
        mock_mongo.create_project_user.return_value = {
            "username": "project_5_user",
            "password": "test_pass",
            "database": "project_5",
            "connection_string": "mongodb://project_5_user:test_pass@localhost:27017/project_5"
        }
        mock_mongo_client_class.return_value = mock_mongo
        
        # Create project and deploy
        user = User._create_fake()
        project = ProjectModel._create_fake(owner=user)
        
        service = deploy_service(
            project=project,
            prefix="test",
            flow={"nodes": [], "edges": []},
            key=f"{project.id}_1"
        )
        
        # Verify MongoDB user was created
        mock_mongo.create_project_user.assert_called_once_with(project.id)
        
        # Verify environment variables include MongoDB credentials
        call_kwargs = mock_client.services.create.call_args[1]
        env_vars = call_kwargs.get("env", [])
        
        # Check for MONGO_ADDR and MONGO_DB_NAME
        mongo_addr_found = any("MONGO_ADDR=" in var for var in env_vars)
        mongo_db_found = any("MONGO_DB_NAME=" in var for var in env_vars)
        
        assert mongo_addr_found, "MONGO_ADDR not found in environment variables"
        assert mongo_db_found, "MONGO_DB_NAME not found in environment variables"
