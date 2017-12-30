import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from receipts.html_parser import HtmlParser
from receipts.models import InvoiceRow


class Command(BaseCommand):
    help = 'Imports html invoice file'

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs=1, type=str)
        parser.add_argument('year', nargs=1, type=int)
        parser.add_argument('month', nargs=1, type=int)

    def handle(self, *args, **options):
        invoice_date = datetime.date(options["year"][0], options["month"][0], 1)
        html_parser = HtmlParser(options['filename'][0])
        invoices = html_parser.process()
        for invoice in invoices:
            invoice["invoice_date"] = invoice_date
            InvoiceRow.objects.update_or_create(row_identifier=invoice["row_identifier"], defaults=invoice)

        self.stdout.write(self.style.SUCCESS('Successfully imported %s rows from "%s"' % (len(invoices), options["filename"][0])))
