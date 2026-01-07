import pytest
from django.contrib.admin.sites import AdminSite
from django.utils import timezone
from decimal import Decimal

from core.apps.template.models.submission import TemplateSubmissionRequestModel
from core.apps.template.models.template import TemplateModel
from core.apps.template.enums.template import TemplateSubmissionStatusEnum
from core.apps.template.admin.submission import TemplateSubmissionRequestAdmin
from core.apps.accounts.models import User
from core.apps.api.models import ProjectModel


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    return User.objects.create_user(
        phone="+998901111111",
        username="adminuser",
        password="adminpass123",
        is_staff=True,
        is_superuser=True
    )


@pytest.fixture
def regular_user(db):
    """Create a regular user"""
    return User.objects.create_user(
        phone="+998901234567",
        username="testuser",
        password="testpass123"
    )


@pytest.fixture
def project(db, regular_user):
    """Create a project"""
    return ProjectModel.objects.create(
        name="Test Project",
        description="Test Description",
        owner=regular_user
    )


@pytest.fixture
def pending_submission(db, regular_user, project):
    """Create a pending template submission"""
    return TemplateSubmissionRequestModel.objects.create(
        user=regular_user,
        project=project,
        name="Test Template",
        short_description="Short description",
        description="Long description",
        original_price=Decimal("100.00"),
        status=TemplateSubmissionStatusEnum.PENDING.value
    )


@pytest.fixture
def admin_site():
    """Create admin site"""
    return AdminSite()


@pytest.fixture
def submission_admin(admin_site):
    """Create TemplateSubmissionRequestAdmin instance"""
    return TemplateSubmissionRequestAdmin(TemplateSubmissionRequestModel, admin_site)


@pytest.mark.django_db
def test_status_change_to_approved_creates_template(admin_user, pending_submission, submission_admin):
    """Test that changing status to approved creates a template and sets review fields"""
    # Create a mock request object
    class MockRequest:
        def __init__(self, user):
            self.user = user
    
    request = MockRequest(admin_user)
    
    # Change status to approved
    pending_submission.status = TemplateSubmissionStatusEnum.APPROVED.value
    
    # Call save_model (simulating admin save)
    submission_admin.save_model(request, pending_submission, None, change=True)
    
    # Refresh from database
    pending_submission.refresh_from_db()
    
    # Verify status changed
    assert pending_submission.status == TemplateSubmissionStatusEnum.APPROVED.value
    
    # Verify reviewed fields are set
    assert pending_submission.reviewed_by == admin_user
    assert pending_submission.reviewed_at is not None
    
    # Verify template was created
    assert pending_submission.template is not None
    assert TemplateModel.objects.filter(id=pending_submission.template.id).exists()
    
    # Verify template details
    template = pending_submission.template
    assert template.author == pending_submission.user
    assert template.name == pending_submission.name
    assert template.short_description == pending_submission.short_description
    assert template.description == pending_submission.description
    assert template.original_price == pending_submission.original_price
    assert template.is_verify is True


@pytest.mark.django_db
def test_status_change_to_rejected_sets_review_fields(admin_user, pending_submission, submission_admin):
    """Test that changing status to rejected sets review fields"""
    # Create a mock request object
    class MockRequest:
        def __init__(self, user):
            self.user = user
    
    request = MockRequest(admin_user)
    
    # Change status to rejected
    pending_submission.status = TemplateSubmissionStatusEnum.REJECTED.value
    pending_submission.rejection_reason = "Does not meet quality standards"
    
    # Call save_model (simulating admin save)
    submission_admin.save_model(request, pending_submission, None, change=True)
    
    # Refresh from database
    pending_submission.refresh_from_db()
    
    # Verify status changed
    assert pending_submission.status == TemplateSubmissionStatusEnum.REJECTED.value
    
    # Verify reviewed fields are set
    assert pending_submission.reviewed_by == admin_user
    assert pending_submission.reviewed_at is not None
    
    # Verify rejection reason is preserved
    assert pending_submission.rejection_reason == "Does not meet quality standards"
    
    # Verify no template was created
    assert pending_submission.template is None


@pytest.mark.django_db
def test_no_changes_when_status_unchanged(admin_user, pending_submission, submission_admin):
    """Test that review fields are not changed when status is unchanged"""
    # Create a mock request object
    class MockRequest:
        def __init__(self, user):
            self.user = user
    
    request = MockRequest(admin_user)
    
    # Don't change status, just update other fields
    pending_submission.name = "Updated Name"
    
    # Call save_model (simulating admin save)
    submission_admin.save_model(request, pending_submission, None, change=True)
    
    # Refresh from database
    pending_submission.refresh_from_db()
    
    # Verify name changed
    assert pending_submission.name == "Updated Name"
    
    # Verify reviewed fields are not set
    assert pending_submission.reviewed_by is None
    assert pending_submission.reviewed_at is None
    
    # Verify status is still pending
    assert pending_submission.status == TemplateSubmissionStatusEnum.PENDING.value


@pytest.mark.django_db
def test_status_field_not_readonly(submission_admin):
    """Test that status field is not in readonly_fields"""
    assert "status" not in submission_admin.readonly_fields


@pytest.mark.django_db
def test_rejection_reason_field_not_readonly(submission_admin):
    """Test that rejection_reason field is not in readonly_fields"""
    assert "rejection_reason" not in submission_admin.readonly_fields
