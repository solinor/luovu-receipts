from django.core.management.base import BaseCommand, CommandError

from receipts.slack import send_notifications


class Command(BaseCommand):
    help = 'Send slack notifications'

    def add_arguments(self, parser):
        parser.add_argument('year', nargs=1, type=int)
        parser.add_argument('month', nargs=1, type=int)

    def handle(self, *args, **options):
        send_notifications(options["year"][0], options["month"][0])
