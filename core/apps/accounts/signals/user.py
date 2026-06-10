from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model

from core.apps.shared.observability import metrics


@receiver(post_save, sender=get_user_model())
def user_signal(sender, created, instance, **kwargs):
    """Yangi user yaratilganda: username generatsiya + ro'yxatdan o'tish metrikasi."""
    if created:
        # Yangi ro'yxatdan o'tish — Prometheus counter (vaqt taqsimoti uchun).
        metrics.safe_inc(metrics.USER_REGISTRATIONS)
        if instance.username is None:
            instance.username = "U%(id)s" % {"id": 1000 + instance.id}
            instance.save()
