from django.core.management.base import BaseCommand, CommandError
from receipts.utils import refresh_receipts_for_user, get_all_users
from receipts.models import InvoiceRow, LuovuReceipt
import datetime

class Command(BaseCommand):
    help = 'Refreshes receipts for all known users'

    def handle(self, *args, **options):
        start_date = datetime.date.today() - datetime.timedelta(days=60)
        end_date = datetime.date.today() + datetime.timedelta(days=30)
        for user_email in get_all_users():
            receipt_count = refresh_receipts_for_user(user_email, start_date, end_date)
            self.stdout.write(self.style.SUCCESS('Successfully refreshed %s receipts for user "%s"' % (receipt_count, user_email)))
