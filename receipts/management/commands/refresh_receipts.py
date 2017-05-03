from django.core.management.base import BaseCommand, CommandError
from receipts.utils import refresh_receipts_for_user
import datetime

class Command(BaseCommand):
    help = 'Refreshes receipts from Luovu for specified users'

    def add_arguments(self, parser):
        parser.add_argument('user_email', nargs='+', type=str)

    def handle(self, *args, **options):
        start_date = datetime.date.today() - datetime.timedelta(days=60)
        end_date = datetime.date.today() + datetime.timedelta(days=30)
        for user_email in options['user_email']:

            receipts_count = refresh_receipts_for_user(user_email, start_date, end_date)
            self.stdout.write(self.style.SUCCESS('Successfully refreshed %s receipts for user "%s"' % (receipts_count, user_email)))
