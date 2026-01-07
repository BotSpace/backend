import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from decimal import Decimal

from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.models.template import TemplateModel
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
def admin_user(db):
    """Create an admin user"""
    return User.objects.create_superuser(
        phone="+998901234568",
        username="adminuser",
        password="adminpass123"
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
def test_list_submissions_admin(api_client, admin_user, user, project):
    """Test that admins can see all submissions"""
    # Create submission by regular user
    submission = TemplateSubmissionRequestModel.objects.create(
        user=user,
        project=project,
        name="Test Template",
        short_description="Short description",
        description="Long description",
        original_price=Decimal("100.00")
    )
    
    api_client.force_authenticate(user=admin_user)
    
    url = reverse("submission-list")
    response = api_client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    # Admin should see all submissions
    assert len(data["data"]["results"]) >= 1


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
def test_approve_submission(api_client, admin_user, user, submission):
    """Test approving a template submission"""
    api_client.force_authenticate(user=admin_user)
    
    url = reverse("submission-approve", kwargs={"pk": submission.id})
    data = {
        "discount": "10.00",
        "discount_type": "percent"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 200
    
    # Check that submission was approved
    submission.refresh_from_db()
    assert submission.status == TemplateSubmissionStatusEnum.APPROVED.value
    assert submission.template is not None
    assert submission.reviewed_by == admin_user
    
    # Check that template was created
    template = TemplateModel.objects.get(id=submission.template.id)
    assert template.name == submission.name
    assert template.author == user
    assert template.is_verify is True
    assert template.discount == Decimal("10.00")


@pytest.mark.django_db
def test_reject_submission(api_client, admin_user, submission):
    """Test rejecting a template submission"""
    api_client.force_authenticate(user=admin_user)
    
    url = reverse("submission-reject", kwargs={"pk": submission.id})
    data = {
        "rejection_reason": "Quality standards not met"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 200
    
    # Check that submission was rejected
    submission.refresh_from_db()
    assert submission.status == TemplateSubmissionStatusEnum.REJECTED.value
    assert submission.rejection_reason == "Quality standards not met"
    assert submission.reviewed_by == admin_user
    assert submission.template is None


@pytest.mark.django_db
def test_approve_non_pending_submission_fails(api_client, admin_user, submission):
    """Test that non-pending submissions cannot be approved"""
    # First approve the submission
    submission.status = TemplateSubmissionStatusEnum.APPROVED.value
    submission.save()
    
    api_client.force_authenticate(user=admin_user)
    
    url = reverse("submission-approve", kwargs={"pk": submission.id})
    response = api_client.post(url)
    
    assert response.status_code == 400


@pytest.mark.django_db
def test_non_admin_cannot_approve(api_client, user, submission):
    """Test that non-admin users cannot approve submissions"""
    api_client.force_authenticate(user=user)
    
    url = reverse("submission-approve", kwargs={"pk": submission.id})
    response = api_client.post(url)
    
    assert response.status_code == 403


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
