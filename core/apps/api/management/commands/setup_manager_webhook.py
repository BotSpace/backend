from django.core.management import BaseCommand

from core.apps.api.services.managed_bot import set_manager_webhook


class Command(BaseCommand):
    help = "Manager bot uchun Telegram webhook o'rnatish"

    def handle(self, *args, **options):
        ok = set_manager_webhook()
        if ok:
            self.stdout.write(self.style.SUCCESS("Webhook muvaffaqiyatli o'rnatildi"))
        else:
            self.stderr.write("Webhook o'rnatishda xato (log'ni tekshiring)")
