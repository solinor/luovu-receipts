import datetime

from django.core.management.base import BaseCommand, CommandError

from receipts.models import InvoiceRow, LuovuReceipt
from receipts.utils import get_all_users, refresh_receipts_for_user


class Command(BaseCommand):
    help = 'Refreshes receipts for all known users'

    def handle(self, *args, **options):
        start_date = datetime.date.today() - datetime.timedelta(days=60)
        end_date = datetime.date.today() + datetime.timedelta(days=30)
        for user_email in get_all_users():
            receipt_count = refresh_receipts_for_user(user_email, start_date, end_date)
            self.stdout.write(self.style.SUCCESS('Successfully refreshed %s receipts for user "%s"' % (receipt_count, user_email)))
