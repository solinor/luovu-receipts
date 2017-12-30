from django.core.management.base import BaseCommand, CommandError

from receipts.slack import refresh_slack_users


class Command(BaseCommand):
    help = 'Refresh users from Slack'

    def handle(self, *args, **options):
        refresh_slack_users()
