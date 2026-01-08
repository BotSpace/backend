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
    # Only process if payment is confirmed, status is CONFIRM, and commission hasn't been paid yet
    if (instance.payment_status and 
        instance.status == TemplateOrderStatusEnum.CONFIRM.value and 
        not instance.commission_paid):
        
        if instance.template and instance.template.author:
            # Calculate 80% for the author (20% commission for platform)
            author_share = instance.amount * Decimal('0.80')
            
            # Add to author's template balance
            author = instance.template.author
            author.template_balance += author_share
            author.save()
            
            # Mark commission as paid to avoid double-processing
            # Use update to avoid triggering the signal again
            TemplateOrderModel.objects.filter(pk=instance.pk).update(commission_paid=True)
