import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from decimal import Decimal

from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.enums.template import TemplateSubmissionStatusEnum
from core.apps.accounts.models import User
from core.apps.api.models import ProjectModel


@pytest.fixture
def user(db):
    """Create a regular user"""
    return User.objects.create_user(
        phone="+998901234567",
        username="testuser",
        password="testpass123"
    )


@pytest.fixture
def another_user(db):
    """Create another regular user"""
    return User.objects.create_user(
        phone="+998901234569",
        username="anotheruser",
        password="testpass123"
    )


@pytest.fixture
def project(db, user):
    """Create a project"""
    return ProjectModel.objects.create(
        name="Test Project",
        description="Test Description",
        owner=user
    )


@pytest.fixture
def submission(db, user, project):
    """Create a template submission"""
    return TemplateSubmissionRequestModel.objects.create(
        user=user,
        project=project,
        name="Test Template",
        short_description="Short description",
        description="Long description",
        original_price=Decimal("100.00"),
        status=TemplateSubmissionStatusEnum.PENDING.value
    )


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.mark.django_db
def test_create_submission(api_client, user, project):
    """Test creating a template submission"""
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-list")
    data = {
        "project": project.id,
        "name": "New Template",
        "short_description": "Short desc",
        "description": "Long desc",
        "original_price": "150.00"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 201
    
    # Check that submission was created
    submission = TemplateSubmissionRequestModel.objects.get(name="New Template")
    assert submission.user == user
    assert submission.project == project
    assert submission.status == TemplateSubmissionStatusEnum.PENDING.value


@pytest.mark.django_db
def test_list_submissions_user(api_client, user, submission):
    """Test that users can only see their own submissions"""
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-list")
    response = api_client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    assert len(data["data"]["results"]) == 1
    assert data["data"]["results"][0]["id"] == submission.id


@pytest.mark.django_db
def test_user_cannot_see_other_users_submissions(api_client, user, another_user, project):
    """Test that users cannot see other users' submissions"""
    # Create submission by another user
    other_submission = TemplateSubmissionRequestModel.objects.create(
        user=another_user,
        project=project,
        name="Other User Template",
        short_description="Short description",
        description="Long description",
        original_price=Decimal("100.00")
    )
    
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-list")
    response = api_client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    # User should only see their own submissions, not other users'
    for submission in data["data"]["results"]:
        assert submission["user_phone"] == user.phone


@pytest.mark.django_db
def test_retrieve_submission(api_client, user, submission):
    """Test retrieving a submission detail"""
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-detail", kwargs={"pk": submission.id})
    response = api_client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    assert data["data"]["id"] == submission.id
    assert data["data"]["name"] == submission.name


@pytest.mark.django_db
def test_unauthenticated_cannot_create_submission(api_client, project):
    """Test that unauthenticated users cannot create submissions"""
    url = reverse("submission-list")
    data = {
        "project": project.id,
        "name": "New Template",
        "short_description": "Short desc",
        "description": "Long desc",
        "original_price": "150.00"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 401


@pytest.mark.django_db
def test_update_pending_submission(api_client, user, submission):
    """Test updating a pending submission"""
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-detail", kwargs={"pk": submission.id})
    data = {
        "name": "Updated Template Name",
        "short_description": "Updated description"
    }
    
    response = api_client.patch(url, data=data)
    assert response.status_code == 200
    
    submission.refresh_from_db()
    assert submission.name == "Updated Template Name"


@pytest.mark.django_db
def test_delete_pending_submission(api_client, user, submission):
    """Test deleting a pending submission"""
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-detail", kwargs={"pk": submission.id})
    response = api_client.delete(url)
    
    assert response.status_code == 204
    assert not TemplateSubmissionRequestModel.objects.filter(id=submission.id).exists()


@pytest.mark.django_db
def test_create_submission_without_categories_and_features(api_client, user, project):
    """Test creating a template submission without categories and features"""
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-list")
    data = {
        "project": project.id,
        "name": "Template Without Categories",
        "short_description": "Short desc",
        "description": "Long desc",
        "original_price": "100.00"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 201
    
    # Check that submission was created without categories and features
    submission = TemplateSubmissionRequestModel.objects.get(name="Template Without Categories")
    assert submission.user == user
    assert submission.project == project
    assert submission.status == TemplateSubmissionStatusEnum.PENDING.value
    assert submission.categories.count() == 0
    assert submission.features.count() == 0


@pytest.mark.django_db
def test_create_submission_with_empty_categories_and_features(api_client, user, project):
    """Test creating a template submission with explicitly empty categories and features"""
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-list")
    data = {
        "project": project.id,
        "name": "Template With Empty Lists",
        "short_description": "Short desc",
        "description": "Long desc",
        "original_price": "100.00",
        "categories": [],
        "features": []
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 201
    
    # Check that submission was created with empty categories and features
    submission = TemplateSubmissionRequestModel.objects.get(name="Template With Empty Lists")
    assert submission.user == user
    assert submission.project == project
    assert submission.status == TemplateSubmissionStatusEnum.PENDING.value
    assert submission.categories.count() == 0
    assert submission.features.count() == 0
