import logging

import slacker
from django.conf import settings
from django.db.models import Q, Sum
from django.db.models.functions import Length

from receipts.models import CcUser, InvoiceRow, LuovuReceipt, SlackChat

slack = slacker.Slacker(settings.SLACK_BOT_ACCESS_TOKEN)
logger = logging.getLogger(__name__)


def refresh_slack_users():
    slack_users = slack.users.list().body["members"]
    for member in slack_users:
        email = member.get("profile", {}).get("email")
        if not email:
            continue
        CcUser.objects.update_or_create(email=email, defaults={
            "slack_id": member.get("id"),
        })


def send_notifications(year, month, dry_run=False):
    slack_admin = CcUser.objects.get(email=settings.SLACK_ADMIN_EMAIL)
    users = InvoiceRow.objects.filter(invoice_date__year=year, invoice_date__month=month).values_list("card_holder_email_guess", flat=True).order_by("card_holder_email_guess").distinct("card_holder_email_guess")
    messages = []
    for user_email in users:
        user_invoice_rows = InvoiceRow.objects.filter(invoice_date__year=year, invoice_date__month=month).filter(card_holder_email_guess=user_email)
        user_invoice_rows_count = user_invoice_rows.count()
        user_invoice_rows_sum = user_invoice_rows.aggregate(sum=Sum("row_price"))["sum"]
        user_receipts = LuovuReceipt.objects.exclude(state__contains="deleted").exclude(account_number=1900).filter(luovu_user=user_email).filter(date__year=year, date__month=month)
        user_receipts_count = user_receipts.count()
        user_receipts_sum = user_receipts.aggregate(sum=Sum("price"))["sum"]

        issues = []
        if user_invoice_rows_count > user_receipts_count:
            issues.append("You have {} receipts but invoice had {} rows for you.".format(user_receipts_count, user_invoice_rows_count))
        elif user_invoice_rows_count < user_receipts_count:
            issues.append("You have {} receipts but invoice had only {} rows for you. If you have a receipt for a cash purchase, please mark it to the correct category.".format(user_receipts_count, user_invoice_rows_count))

        if user_invoice_rows_sum > user_receipts_sum:
            issues.append("Sum of your receipts (excluding cash purchases) is {}€, but you have {}€ in the invoice. Please check whether some receipts are missing, or and that you entered the correct sums for each receipts.".format(user_receipts_sum, user_invoice_rows_sum))
        elif user_receipts_sum > user_invoice_rows_sum:
            issues.append("Sum of your receipts (excluding cash purchases) is {}€, but you have {}€ in the invoice. If you have receipt(s) for cash purchases, please mark it to the correct category.".format(user_receipts_sum, user_invoice_rows_sum))


        empty_descriptions = user_receipts.annotate(description_len=Length("description")).filter(Q(description=None) | Q(description_len=0))
        for empty_description in empty_descriptions:
            issues.append("You have a receipt with empty description. Go to <https://app.luovu.com/a/#i/{}|Luovu> to fix this.".format(empty_description.luovu_id))
        if len(issues) > 0:
            message = "\n".join(issues)
            fallback_message = "Hi there!\n\nYou have work to do with your credit card receipts:\n" + message
            attachment = {
                "author_name": "Solinor Receipts",
                "author_link": "https://receipts.solinor.com",
                "fallback": fallback_message,
                "title": "Work to do with credit card invoices",
                "title_link": "https://app.luovu.com",
                "text": message,
                "fields": [
                    {"title": "Your receipts", "value": "{}".format(user_receipts_count), "short": True},
                    {"title": "Rows in invoice", "value": "{}".format(user_invoice_rows_count), "short": True},
                    {"title": "Sum of your receipts", "value": "{:02f}€".format(user_receipts_sum), "short": True},
                    {"title": "Sum on the invoice", "value": "{:02f}€".format(user_invoice_rows_sum), "short": True},
                    {"title": "Empty descriptions", "value": "{}".format(len(empty_descriptions)), "short": True}
                ],
                "actions": [
                    {
                        "type": "button",
                        "text": "See the details",
                        "url": "https://receipts.solinor.com/person/{}/{}/{}".format(user_email, year, month),
                        "style": "primary",
                    },
                    {
                        "type": "button",
                        "text": "Upload receipts",
                        "url": "https://app.luovu.com/",
                    },
                ],
                "footer": "This notification is sent when a new CC invoice comes in."
            }

            try:
                user = CcUser.objects.get(email=user_email)
            except CcUser.DoesNotExist:
                logger.warning("No CcUser for email=%s", user_email)
                continue
            if not user.slack_id:
                logger.warning("No CcUser.slack_id for email=%s", user_email)
                continue
            messages.append({
                "email": user_email,
                "issues": issues,
            })
            if dry_run:
                continue

            slack.chat.post_message(user.slack_id, attachments=[attachment], as_user="cc-bot")
            slack.chat.post_message(slack_admin, text="This message was sent to {}:".format(user.email), attachments=[attachment], as_user="cc-bot")
    return messages
