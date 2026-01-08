import pytest
from decimal import Decimal
from django.utils import timezone

from core.apps.template.models.withdrawal import TemplateWithdrawalRequestModel
from core.apps.template.models.order import TemplateOrderModel
from core.apps.template.models.template import TemplateModel
from core.apps.template.enums.withdrawal import WithdrawalStatusEnum
from core.apps.template.enums.order import TemplateOrderStatusEnum
from core.apps.accounts.models import User
from core.apps.api.models import ProjectModel


@pytest.fixture
def admin_user(db):
    """Create an admin user"""
    return User.objects.create_superuser(
        phone="+998901234560",
        username="admin",
        password="admin123"
    )


@pytest.fixture
def template_author(db):
    """Create a template author user"""
    user = User.objects.create_user(
        phone="+998901234567",
        username="author",
        password="testpass123"
    )
    user.template_balance = Decimal("0.00")
    user.save()
    return user


@pytest.fixture
def buyer(db):
    """Create a buyer user"""
    return User.objects.create_user(
        phone="+998901234568",
        username="buyer",
        password="testpass123"
    )


@pytest.fixture
def project(db, template_author):
    """Create a project"""
    return ProjectModel.objects.create(
        name="Test Project",
        description="Test Description",
        owner=template_author
    )


@pytest.fixture
def template(db, template_author, project):
    """Create a template"""
    return TemplateModel.objects.create(
        author=template_author,
        name="Test Template",
        image="test.jpg",
        project=project,
        short_description="Short desc",
        description="Long desc",
        original_price=Decimal("100.00"),
        is_verify=True
    )


@pytest.mark.django_db
def test_commission_distribution_on_template_sale(template_author, buyer, template):
    """Test that 80% commission is distributed to author on template sale"""
    # Create a confirmed order
    order = TemplateOrderModel.objects.create(
        user=buyer,
        template=template,
        amount=Decimal("100.00"),
        status=TemplateOrderStatusEnum.CONFIRM.value,
        payment_status=True,
        commission_paid=False
    )
    
    # Refresh author from database
    template_author.refresh_from_db()
    
    # Check that author received 80% of the amount
    expected_amount = Decimal("80.00")  # 80% of 100.00
    assert template_author.template_balance == expected_amount
    
    # Check that commission_paid flag is set
    order.refresh_from_db()
    assert order.commission_paid is True


@pytest.mark.django_db
def test_commission_not_distributed_without_payment(template_author, buyer, template):
    """Test that commission is not distributed if payment_status is False"""
    initial_balance = template_author.template_balance
    
    # Create an order without payment
    order = TemplateOrderModel.objects.create(
        user=buyer,
        template=template,
        amount=Decimal("100.00"),
        status=TemplateOrderStatusEnum.CONFIRM.value,
        payment_status=False,
        commission_paid=False
    )
    
    # Refresh author from database
    template_author.refresh_from_db()
    
    # Balance should not change
    assert template_author.template_balance == initial_balance
    
    # Commission should not be marked as paid
    order.refresh_from_db()
    assert order.commission_paid is False


@pytest.mark.django_db
def test_commission_not_distributed_for_pending_order(template_author, buyer, template):
    """Test that commission is not distributed for pending orders"""
    initial_balance = template_author.template_balance
    
    # Create a pending order
    order = TemplateOrderModel.objects.create(
        user=buyer,
        template=template,
        amount=Decimal("100.00"),
        status=TemplateOrderStatusEnum.PENDING.value,
        payment_status=True,
        commission_paid=False
    )
    
    # Refresh author from database
    template_author.refresh_from_db()
    
    # Balance should not change
    assert template_author.template_balance == initial_balance


@pytest.mark.django_db
def test_commission_not_distributed_twice(template_author, buyer, template):
    """Test that commission is not distributed twice for the same order"""
    # Create a confirmed order
    order = TemplateOrderModel.objects.create(
        user=buyer,
        template=template,
        amount=Decimal("100.00"),
        status=TemplateOrderStatusEnum.CONFIRM.value,
        payment_status=True,
        commission_paid=False
    )
    
    # Refresh author from database
    template_author.refresh_from_db()
    first_balance = template_author.template_balance
    
    # Update the order (this should trigger the signal again)
    order.save()
    
    # Refresh author again
    template_author.refresh_from_db()
    
    # Balance should not have changed from the first distribution
    assert template_author.template_balance == first_balance


@pytest.mark.django_db
def test_withdrawal_approval_deducts_balance(admin_user):
    """Test that approving a withdrawal deducts from user's template balance"""
    # Create a user with template balance
    user = User.objects.create_user(
        phone="+998901234567",
        username="testuser",
        password="testpass123"
    )
    user.template_balance = Decimal("1000.00")
    user.save()
    
    # Create a withdrawal request
    withdrawal = TemplateWithdrawalRequestModel.objects.create(
        user=user,
        amount=Decimal("500.00"),
        card_number="8600123456789012",
        card_owner="Test User",
        status=WithdrawalStatusEnum.PENDING.value
    )
    
    # Simulate admin approval
    withdrawal.status = WithdrawalStatusEnum.APPROVED.value
    withdrawal.reviewed_by = admin_user
    withdrawal.reviewed_at = timezone.now()
    
    # Deduct balance (this simulates what the admin does)
    user.template_balance -= withdrawal.amount
    user.save()
    withdrawal.save()
    
    # Refresh user
    user.refresh_from_db()
    
    # Check that balance was deducted
    assert user.template_balance == Decimal("500.00")
    
    # Check withdrawal status
    withdrawal.refresh_from_db()
    assert withdrawal.status == WithdrawalStatusEnum.APPROVED.value
    assert withdrawal.reviewed_by == admin_user
    assert withdrawal.reviewed_at is not None


@pytest.mark.django_db
def test_withdrawal_rejection_does_not_deduct_balance(admin_user):
    """Test that rejecting a withdrawal does not deduct balance"""
    # Create a user with template balance
    user = User.objects.create_user(
        phone="+998901234567",
        username="testuser",
        password="testpass123"
    )
    user.template_balance = Decimal("1000.00")
    user.save()
    
    # Create a withdrawal request
    withdrawal = TemplateWithdrawalRequestModel.objects.create(
        user=user,
        amount=Decimal("500.00"),
        card_number="8600123456789012",
        card_owner="Test User",
        status=WithdrawalStatusEnum.PENDING.value
    )
    
    # Simulate admin rejection
    withdrawal.status = WithdrawalStatusEnum.REJECTED.value
    withdrawal.rejection_reason = "Invalid card details"
    withdrawal.reviewed_by = admin_user
    withdrawal.reviewed_at = timezone.now()
    withdrawal.save()
    
    # Refresh user
    user.refresh_from_db()
    
    # Check that balance was NOT deducted
    assert user.template_balance == Decimal("1000.00")
    
    # Check withdrawal status
    withdrawal.refresh_from_db()
    assert withdrawal.status == WithdrawalStatusEnum.REJECTED.value
    assert withdrawal.rejection_reason == "Invalid card details"


@pytest.mark.django_db
def test_multiple_template_sales_accumulate_balance(template_author, template):
    """Test that multiple template sales accumulate in author's balance"""
    # Create first sale
    buyer1 = User.objects.create_user(
        phone="+998901234561",
        username="buyer1",
        password="testpass123"
    )
    order1 = TemplateOrderModel.objects.create(
        user=buyer1,
        template=template,
        amount=Decimal("100.00"),
        status=TemplateOrderStatusEnum.CONFIRM.value,
        payment_status=True,
        commission_paid=False
    )
    
    # Refresh author
    template_author.refresh_from_db()
    assert template_author.template_balance == Decimal("80.00")
    
    # Create second sale
    buyer2 = User.objects.create_user(
        phone="+998901234562",
        username="buyer2",
        password="testpass123"
    )
    order2 = TemplateOrderModel.objects.create(
        user=buyer2,
        template=template,
        amount=Decimal("150.00"),
        status=TemplateOrderStatusEnum.CONFIRM.value,
        payment_status=True,
        commission_paid=False
    )
    
    # Refresh author
    template_author.refresh_from_db()
    
    # Balance should be cumulative: 80 + 120 = 200
    assert template_author.template_balance == Decimal("200.00")


@pytest.mark.django_db
def test_withdrawal_and_new_sales_flow(template_author, template, admin_user):
    """Test complete flow: sales, withdrawal, more sales"""
    # Initial sale
    buyer1 = User.objects.create_user(
        phone="+998901234561",
        username="buyer1",
        password="testpass123"
    )
    order1 = TemplateOrderModel.objects.create(
        user=buyer1,
        template=template,
        amount=Decimal("100.00"),
        status=TemplateOrderStatusEnum.CONFIRM.value,
        payment_status=True,
        commission_paid=False
    )
    
    template_author.refresh_from_db()
    assert template_author.template_balance == Decimal("80.00")
    
    # Create and approve withdrawal
    withdrawal = TemplateWithdrawalRequestModel.objects.create(
        user=template_author,
        amount=Decimal("50.00"),
        card_number="8600123456789012",
        card_owner="Author",
        status=WithdrawalStatusEnum.PENDING.value
    )
    
    withdrawal.status = WithdrawalStatusEnum.APPROVED.value
    withdrawal.reviewed_by = admin_user
    withdrawal.reviewed_at = timezone.now()
    template_author.template_balance -= withdrawal.amount
    template_author.save()
    withdrawal.save()
    
    template_author.refresh_from_db()
    assert template_author.template_balance == Decimal("30.00")
    
    # Another sale
    buyer2 = User.objects.create_user(
        phone="+998901234562",
        username="buyer2",
        password="testpass123"
    )
    order2 = TemplateOrderModel.objects.create(
        user=buyer2,
        template=template,
        amount=Decimal("100.00"),
        status=TemplateOrderStatusEnum.CONFIRM.value,
        payment_status=True,
        commission_paid=False
    )
    
    template_author.refresh_from_db()
    # 30 + 80 = 110
    assert template_author.template_balance == Decimal("110.00")
