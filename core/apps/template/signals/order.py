from decimal import Decimal
from django.db.models.signals import post_save
from django.dispatch import receiver

from core.apps.template.models import TemplateOrderModel
from core.apps.template.enums.order import TemplateOrderStatusEnum


@receiver(post_save, sender=TemplateOrderModel)
def OrderSignal(sender, instance, created, **kwargs):
    """
    Signal to handle commission distribution when a template is sold.
    Takes 20% commission and gives 80% to the template author.
    """
    if instance.payment_status and instance.status == TemplateOrderStatusEnum.CONFIRM.value:
        if instance.template and instance.template.author:
            # Check if we've already processed this order
            # by seeing if the author already has template_balance credited
            # We use a flag to avoid double-processing
            if not hasattr(instance, '_commission_processed'):
                # Calculate 80% for the author (20% commission for platform)
                author_share = instance.amount * Decimal('0.80')
                
                # Add to author's template balance
                author = instance.template.author
                author.template_balance += author_share
                author.save()
                
                # Mark as processed to avoid double-processing
                instance._commission_processed = True
