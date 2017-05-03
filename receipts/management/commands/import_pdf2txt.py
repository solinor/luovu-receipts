from django.core.management.base import BaseCommand, CommandError
from receipts.models import InvoiceRow
from receipts.pdf_parser import PdfParser
from django.conf import settings
import datetime

class Command(BaseCommand):
    help = 'Imports txt file converted with pdf2txt.py'

    def add_arguments(self, parser):
        parser.add_argument('filename', nargs=1, type=str)
        parser.add_argument('year', nargs=1, type=int)
        parser.add_argument('month', nargs=1, type=int)

    def handle(self, *args, **options):
        print options
        invoice_date = datetime.date(options["year"][0], options["month"][0], 1)
        pdf_parser = PdfParser(options['filename'][0])
        invoices = pdf_parser.process()
        for invoice in invoices:
            invoice["invoice_date"] = invoice_date
            InvoiceRow.objects.update_or_create(row_identifier=invoice["row_identifier"], defaults=invoice)

        self.stdout.write(self.style.SUCCESS('Successfully imported %s rows from "%s"' % (len(invoices), options["filename"][0])))
