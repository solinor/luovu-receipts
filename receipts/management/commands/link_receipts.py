from django.core.management.base import BaseCommand, CommandError
from receipts.models import InvoiceRow, LuovuPrice, LuovuReceipt, InvoiceReceipt
from django.conf import settings
from django.utils import timezone
import datetime

class Command(BaseCommand):
    help = 'Automatically link unlinked receipts when possible'

    def handle(self, *args, **options):
        for invoice in InvoiceRow.objects.all():

#            print invoice.invoicereceipt_set.all()
            receipts = LuovuReceipt.objects.filter(luovu_user=invoice.card_holder_email_guess).filter(date__gte=invoice.delivery_date - datetime.timedelta(days=3)).filter(date__lte=invoice.delivery_date + datetime.timedelta(days=3))
            if invoice.invoicereceipt_set.exclude(confirmed_by=None).count() > 0:
                print "Skipping confirmed linking between invoice and receipt"
                continue
            receipts_count = receipts.count()
            if receipts_count == 1:
                invoice.invoicereceipt_set.all().delete()
                invoice_receipt = InvoiceReceipt(invoice_row=invoice, luovu_receipt=receipts[0], linked_at=timezone.now())
                invoice_receipt.save()
                print "Only a single hit; matching."
#                print invoice
            elif receipts_count > 1:
#                print invoice, receipts
                for receipt in receipts:
                    if receipt.price == invoice.row_price or (invoice.foreign_currency and receipt.price == invoice.foreign_currency):
                        print "Multiple receipts per day; price is matching"
                        invoice.invoicereceipt_set.all().delete()
                        invoice_receipt = InvoiceReceipt(invoice_row=invoice, luovu_receipt=receipt, linked_at=timezone.now())
                        break
