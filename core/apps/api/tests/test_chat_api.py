# type: ignore
import pytest
from unittest.mock import MagicMock, patch
from django.urls import reverse
from rest_framework.test import APIClient

from core.apps.api.models import ProjectModel
from core.apps.cms.models.cms import CollectionModel


@pytest.fixture(autouse=True)
def patch_docker_services():
    """Patch Docker services to avoid errors during project creation"""
    with patch("core.apps.api.signals.project.remove_service") as mock_remove, \
         patch("core.apps.api.signals.project.deploy_service") as mock_deploy:
        magic = MagicMock()
        magic.id = "test_service_id"
        mock_deploy.return_value = magic
        mock_remove.return_value = True
        yield


@pytest.fixture
def chat_client(db):
    """Create test project with authenticated client"""
    instance = ProjectModel._create_fake()
    client = APIClient()
    client.force_authenticate(instance.owner)
    
    # Get collections created by signal
    users_collection = CollectionModel.objects.get(project=instance, name="users")
    chat_collection = CollectionModel.objects.get(project=instance, name="chat")
    
    return client, instance, users_collection, chat_collection


@pytest.mark.django_db
class TestChatAPI:
    """Test Chat API endpoints"""

    def test_collections_created_on_project_creation(self, chat_client):
        """Test that users and chat collections are created automatically"""
        client, project, users_collection, chat_collection = chat_client
        
        assert users_collection is not None
        assert chat_collection is not None
        assert users_collection.name == "users"
        assert chat_collection.name == "chat"
        
        # Check users collection fields
        user_fields = list(users_collection.fields.values_list('name', flat=True))
        assert 'chat_id' in user_fields
        assert 'first_name' in user_fields
        assert 'last_name' in user_fields
        assert 'created_at' in user_fields
        
        # Check chat collection fields
        chat_fields = list(chat_collection.fields.values_list('name', flat=True))
        assert 'chat_id' in chat_fields
        assert 'text' in chat_fields

    @patch('core.apps.api.views.chat.MongoRepository')
    @patch('core.apps.api.views.chat.MongoDBClient')
    def test_get_users_with_messages(self, mock_mongo_client, mock_mongo_repo, chat_client):
        """Test getting users with their messages"""
        client, project, users_collection, chat_collection = chat_client
        
        # Mock MongoDB data
        mock_users = [
            {
                "_id": "507f1f77bcf86cd799439011",
                "chat_id": "123456789",
                "first_name": "Test",
                "last_name": "User",
                "created_at": "2024-12-04T10:00:00Z"
            }
        ]
        
        mock_messages = [
            {
                "_id": "507f191e810c19729de860ea",
                "chat_id": "123456789",
                "text": "Test message",
                "read": False
            }
        ]
        
        # Setup mock repository
        mock_repo_instance = MagicMock()
        mock_repo_instance.find.side_effect = [mock_users, mock_messages]
        mock_repo_instance.count.side_effect = [1, 1]  # total users, unread count
        mock_mongo_repo.return_value = mock_repo_instance
        
        # Setup mock client
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        
        # Make request
        url = reverse('chat-get-users-with-messages', kwargs={'project_id': project.id})
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert 'users' in data
        assert 'total' in data
        assert data['total'] == 1
        assert len(data['users']) == 1
        assert data['users'][0]['user']['chat_id'] == '123456789'
        assert data['users'][0]['unread_count'] == 1

    @patch('core.apps.api.views.chat.MongoRepository')
    @patch('core.apps.api.views.chat.MongoDBClient')
    def test_get_user_messages(self, mock_mongo_client, mock_mongo_repo, chat_client):
        """Test getting messages for a specific user"""
        client, project, users_collection, chat_collection = chat_client
        
        # Mock MongoDB data
        mock_messages = [
            {
                "_id": "507f191e810c19729de860ea",
                "chat_id": "123456789",
                "text": "Test message 1",
                "read": False
            },
            {
                "_id": "507f191e810c19729de860eb",
                "chat_id": "123456789",
                "text": "Test message 2",
                "read": True
            }
        ]
        
        # Setup mock repository
        mock_repo_instance = MagicMock()
        mock_repo_instance.find.return_value = mock_messages
        mock_repo_instance.count.return_value = 2
        mock_mongo_repo.return_value = mock_repo_instance
        
        # Setup mock client
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        
        # Make request
        url = reverse('chat-get-user-messages', kwargs={
            'project_id': project.id,
            'chat_id': '123456789'
        })
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert 'messages' in data
        assert 'total' in data
        assert data['total'] == 2
        assert len(data['messages']) == 2

    @patch('core.apps.api.views.chat.MongoRepository')
    @patch('core.apps.api.views.chat.MongoDBClient')
    def test_mark_messages_as_read(self, mock_mongo_client, mock_mongo_repo, chat_client):
        """Test marking messages as read"""
        client, project, users_collection, chat_collection = chat_client
        
        # Setup mock repository
        mock_repo_instance = MagicMock()
        mock_update_result = MagicMock()
        mock_update_result.modified_count = 2
        mock_repo_instance.update.return_value = mock_update_result
        mock_mongo_repo.return_value = mock_repo_instance
        
        # Setup mock client
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        
        # Make request
        url = reverse('chat-mark-messages-as-read', kwargs={'project_id': project.id})
        response = client.post(url, data={
            'chat_id': '123456789',
            'message_ids': ['507f191e810c19729de860ea', '507f191e810c19729de860eb']
        }, format='json')
        
        assert response.status_code == 200
        data = response.json()
        assert data['success'] is True
        assert data['modified_count'] == 2

    @patch('core.apps.api.views.chat.MongoRepository')
    @patch('core.apps.api.views.chat.MongoDBClient')
    def test_get_chat_stats(self, mock_mongo_client, mock_mongo_repo, chat_client):
        """Test getting chat statistics"""
        client, project, users_collection, chat_collection = chat_client
        
        # Setup mock repository
        mock_repo_instance = MagicMock()
        mock_repo_instance.count.side_effect = [10, 100, 25]  # users, messages, unread
        mock_mongo_repo.return_value = mock_repo_instance
        
        # Setup mock client
        mock_client_instance = MagicMock()
        mock_mongo_client.return_value = mock_client_instance
        
        # Make request
        url = reverse('chat-get-chat-stats', kwargs={'project_id': project.id})
        response = client.get(url)
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_users'] == 10
        assert data['total_messages'] == 100
        assert data['unread_messages'] == 25
        assert data['read_messages'] == 75

    def test_unauthorized_access(self, chat_client):
        """Test that unauthenticated requests are rejected"""
        client, project, users_collection, chat_collection = chat_client
        
        # Create unauthenticated client
        unauth_client = APIClient()
        
        url = reverse('chat-get-users-with-messages', kwargs={'project_id': project.id})
        response = unauth_client.get(url)
        
        assert response.status_code == 401

    def test_access_other_user_project(self, chat_client, db):
        """Test that users cannot access other users' projects"""
        client, project, users_collection, chat_collection = chat_client
        
        # Create another project with different owner
        other_project = ProjectModel._create_fake()
        
        # Try to access other user's project
        url = reverse('chat-get-users-with-messages', kwargs={'project_id': other_project.id})
        response = client.get(url)
        
        assert response.status_code == 404
