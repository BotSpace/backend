from django.core import management
from .base import bot
from config.env import env


class Command(management.BaseCommand):
    help = 'Set up Telegram webhook for the bot'

    def add_arguments(self, parser):
        parser.add_argument(
            '--url',
            type=str,
            help='Full webhook URL (e.g., https://yourdomain.com/authbot/webhook/)',
        )
        parser.add_argument(
            '--delete',
            action='store_true',
            help='Delete webhook and switch to polling mode',
        )

    def handle(self, *args, **options):
        if bot is None:
            self.stdout.write(self.style.ERROR('Bot is not initialized. Check BOT_TOKEN in environment.'))
            return

        try:
            if options['delete']:
                # Delete webhook
                bot.remove_webhook()
                self.stdout.write(self.style.SUCCESS('Webhook deleted successfully!'))
                self.stdout.write(self.style.WARNING('Bot is now ready for polling mode.'))
            else:
                webhook_url = options.get('url')
                if not webhook_url:
                    # Try to get from environment
                    webhook_url = env.str('WEBHOOK_URL', None)
                
                if not webhook_url:
                    self.stdout.write(self.style.ERROR(
                        'Please provide webhook URL either via --url argument or WEBHOOK_URL environment variable'
                    ))
                    return

                # Set webhook
                result = bot.set_webhook(url=webhook_url)
                
                if result:
                    self.stdout.write(self.style.SUCCESS(f'Webhook set successfully to: {webhook_url}'))
                    
                    # Get webhook info
                    webhook_info = bot.get_webhook_info()
                    self.stdout.write(self.style.SUCCESS(f'Webhook info:'))
                    self.stdout.write(f'  URL: {webhook_info.url}')
                    self.stdout.write(f'  Pending updates: {webhook_info.pending_update_count}')
                    if webhook_info.last_error_message:
                        self.stdout.write(self.style.WARNING(f'  Last error: {webhook_info.last_error_message}'))
                else:
                    self.stdout.write(self.style.ERROR('Failed to set webhook'))
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error setting webhook: {e}'))
