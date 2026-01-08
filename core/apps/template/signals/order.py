from decimal import Decimal
from django.db.models import F
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from core.apps.template.models import TemplateOrderModel
from core.apps.template.enums.order import TemplateOrderStatusEnum

User = get_user_model()


@receiver(post_save, sender=TemplateOrderModel)
def OrderSignal(sender, instance, created, **kwargs):
    """
    Signal to handle commission distribution when a template is sold.
    Takes 20% commission and gives 80% to the template author.
    """
    # Check if update_fields is specified and doesn't include commission_paid
    update_fields = kwargs.get('update_fields')
    if update_fields is not None and 'commission_paid' in update_fields:
        return
        
    # Process on creation or update if payment is confirmed, status is CONFIRM, and commission hasn't been paid yet
    if (instance.payment_status and 
        instance.status == TemplateOrderStatusEnum.CONFIRM.value and 
        not instance.commission_paid):
        
        if instance.template and instance.template.author:
            # Calculate 80% for the author (20% commission for platform)
            author_share = instance.amount * Decimal('0.80')
            
            # Add to author's template balance using F() expression for atomic update
            # This prevents race conditions when multiple orders are processed simultaneously
            User.objects.filter(pk=instance.template.author.pk).update(
                template_balance=F('template_balance') + author_share
            )
            
            # Mark commission as paid to avoid double-processing
            instance.commission_paid = True
            instance.save(update_fields=['commission_paid'])
