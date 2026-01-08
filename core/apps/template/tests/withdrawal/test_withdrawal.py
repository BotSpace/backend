import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from decimal import Decimal

from core.apps.template.models.withdrawal import TemplateWithdrawalRequestModel
from core.apps.template.enums.withdrawal import WithdrawalStatusEnum
from core.apps.accounts.models import User


@pytest.fixture
def user(db):
    """Create a regular user with template balance"""
    user = User.objects.create_user(
        phone="+998901234567",
        username="testuser",
        password="testpass123"
    )
    user.template_balance = Decimal("1000.00")
    user.save()
    return user


@pytest.fixture
def another_user(db):
    """Create another regular user"""
    user = User.objects.create_user(
        phone="+998901234569",
        username="anotheruser",
        password="testpass123"
    )
    user.template_balance = Decimal("500.00")
    user.save()
    return user


@pytest.fixture
def withdrawal(db, user):
    """Create a withdrawal request"""
    return TemplateWithdrawalRequestModel.objects.create(
        user=user,
        amount=Decimal("100.00"),
        card_number="8600123456789012",
        card_owner="Test User",
        status=WithdrawalStatusEnum.PENDING.value
    )


@pytest.fixture
def api_client():
    """Create API client"""
    return APIClient()


@pytest.mark.django_db
def test_create_withdrawal_request(api_client, user):
    """Test creating a withdrawal request"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    data = {
        "amount": "500.00",
        "card_number": "8600123456789012",
        "card_owner": "John Doe"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 201
    
    # Check that withdrawal was created
    withdrawal = TemplateWithdrawalRequestModel.objects.get(card_owner="John Doe")
    assert withdrawal.user == user
    assert withdrawal.amount == Decimal("500.00")
    assert withdrawal.status == WithdrawalStatusEnum.PENDING.value


@pytest.mark.django_db
def test_create_withdrawal_exceeding_balance(api_client, user):
    """Test creating a withdrawal request exceeding template balance"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    data = {
        "amount": "2000.00",  # User has only 1000.00
        "card_number": "8600123456789012",
        "card_owner": "John Doe"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 400
    assert "template balance" in str(response.content).lower()


@pytest.mark.django_db
def test_create_withdrawal_with_zero_amount(api_client, user):
    """Test creating a withdrawal request with zero amount"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    data = {
        "amount": "0.00",
        "card_number": "8600123456789012",
        "card_owner": "John Doe"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 400


@pytest.mark.django_db
def test_create_withdrawal_with_negative_amount(api_client, user):
    """Test creating a withdrawal request with negative amount"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    data = {
        "amount": "-100.00",
        "card_number": "8600123456789012",
        "card_owner": "John Doe"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 400


@pytest.mark.django_db
def test_create_withdrawal_with_invalid_card_number(api_client, user):
    """Test creating a withdrawal request with invalid card number"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    data = {
        "amount": "100.00",
        "card_number": "12345",  # Too short
        "card_owner": "John Doe"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 400


@pytest.mark.django_db
def test_create_withdrawal_with_non_numeric_card(api_client, user):
    """Test creating a withdrawal request with non-numeric card"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    data = {
        "amount": "100.00",
        "card_number": "860012345ABC9012",
        "card_owner": "John Doe"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 400


@pytest.mark.django_db
def test_list_withdrawals(api_client, user, withdrawal):
    """Test listing withdrawal requests"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    response = api_client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    assert len(data["data"]["results"]) == 1
    assert data["data"]["results"][0]["id"] == withdrawal.id


@pytest.mark.django_db
def test_user_cannot_see_other_users_withdrawals(api_client, user, another_user):
    """Test that users cannot see other users' withdrawal requests"""
    # Create withdrawal by another user
    other_withdrawal = TemplateWithdrawalRequestModel.objects.create(
        user=another_user,
        amount=Decimal("200.00"),
        card_number="8600123456789013",
        card_owner="Another User"
    )
    
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    response = api_client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    # Should not see other user's withdrawal
    assert len(data["data"]["results"]) == 0


@pytest.mark.django_db
def test_retrieve_withdrawal(api_client, user, withdrawal):
    """Test retrieving a withdrawal request detail"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-detail", kwargs={"pk": withdrawal.id})
    response = api_client.get(url)
    
    assert response.status_code == 200
    data = response.json()
    assert data["status"] is True
    assert data["data"]["id"] == withdrawal.id
    assert data["data"]["amount"] == "100.00"


@pytest.mark.django_db
def test_delete_pending_withdrawal(api_client, user, withdrawal):
    """Test deleting a pending withdrawal request"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-detail", kwargs={"pk": withdrawal.id})
    response = api_client.delete(url)
    
    assert response.status_code == 204
    assert not TemplateWithdrawalRequestModel.objects.filter(id=withdrawal.id).exists()


@pytest.mark.django_db
def test_cannot_delete_approved_withdrawal(api_client, user, withdrawal):
    """Test that approved withdrawals cannot be deleted"""
    withdrawal.status = WithdrawalStatusEnum.APPROVED.value
    withdrawal.save()
    
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-detail", kwargs={"pk": withdrawal.id})
    response = api_client.delete(url)
    
    assert response.status_code == 400
    # Withdrawal should still exist
    assert TemplateWithdrawalRequestModel.objects.filter(id=withdrawal.id).exists()


@pytest.mark.django_db
def test_cannot_delete_rejected_withdrawal(api_client, user, withdrawal):
    """Test that rejected withdrawals cannot be deleted"""
    withdrawal.status = WithdrawalStatusEnum.REJECTED.value
    withdrawal.save()
    
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-detail", kwargs={"pk": withdrawal.id})
    response = api_client.delete(url)
    
    assert response.status_code == 400
    # Withdrawal should still exist
    assert TemplateWithdrawalRequestModel.objects.filter(id=withdrawal.id).exists()


@pytest.mark.django_db
def test_unauthenticated_cannot_create_withdrawal(api_client):
    """Test that unauthenticated users cannot create withdrawal requests"""
    url = reverse("withdrawal-list")
    data = {
        "amount": "100.00",
        "card_number": "8600123456789012",
        "card_owner": "John Doe"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 401


@pytest.mark.django_db
def test_create_withdrawal_with_spaces_in_card_number(api_client, user):
    """Test creating a withdrawal request with spaces in card number"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    data = {
        "amount": "100.00",
        "card_number": "8600 1234 5678 9012",  # With spaces
        "card_owner": "John Doe"
    }
    
    response = api_client.post(url, data=data)
    assert response.status_code == 201


@pytest.mark.django_db
def test_multiple_pending_withdrawals(api_client, user):
    """Test creating multiple pending withdrawal requests"""
    api_client.force_authenticate(user=user)
    
    url = reverse("withdrawal-list")
    
    # Create first withdrawal
    data1 = {
        "amount": "300.00",
        "card_number": "8600123456789012",
        "card_owner": "John Doe"
    }
    response1 = api_client.post(url, data=data1)
    assert response1.status_code == 201
    
    # Create second withdrawal
    data2 = {
        "amount": "400.00",
        "card_number": "8600123456789013",
        "card_owner": "John Doe"
    }
    response2 = api_client.post(url, data=data2)
    assert response2.status_code == 201
    
    # Both should exist
    assert TemplateWithdrawalRequestModel.objects.filter(user=user).count() == 2
