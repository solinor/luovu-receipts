import logging


import slacker
from receipts.models import LuovuReceipt, InvoiceRow, CcUser, SlackChat

from django.conf import settings
from django.db.models import Q
from django.db.models.functions import Length

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

def send_notifications(year, month):
    martiska = CcUser.objects.get(email="martiska.reinikka@solinor.com")
    users = InvoiceRow.objects.filter(invoice_date__year=year, invoice_date__month=month).values_list("card_holder_email_guess").order_by("card_holder_email_guess").distinct("card_holder_email_guess")
    for user_email, in users:  # unpack tuples
        user_invoice_rows_count = InvoiceRow.objects.filter(invoice_date__year=year, invoice_date__month=month).filter(card_holder_email_guess=user_email).count()
        user_receipts = LuovuReceipt.objects.exclude(state="deleted").filter(luovu_user=user_email).filter(date__year=year, date__month=month)
        user_receipts_count = user_receipts.count()
        issues = []
        if user_invoice_rows_count > user_receipts_count:
            issues.append("You have %s receipts but invoice had %s rows for you. Please go to <https://solinor-receipts.herokuapp.com/person/%s/%s/%s|receipts checking service> to check what is missing and add missing receipts to <app.luovu.com/a/|Luovu>." % (user_receipts_count, user_invoice_rows_count, user_email, year, month))
        elif user_invoice_rows_count < user_receipts_count:
            issues.append("You have %s receipts but invoice had only %s rows for you. Please go to <https://solinor-receipts.herokuapp.com/person/%s/%s/%s|receipts checking service> to verify that you have correct data for your receipts." % (user_receipts_count, user_invoice_rows_count, user_email, year, month))
        empty_descriptions = user_receipts.annotate(description_len=Length("description")).filter(Q(description=None) | Q(description_len=0))
        for empty_description in empty_descriptions:
            issues.append("You have a receipt with empty description. Open <https://app.luovu.com/a/#i/%s|Luovu> to fix this." % empty_description.luovu_id)
        if len(issues) > 0:
            slack_message = """Hi there!
It seems you have work to do with your credit card receipts:
"""
            for issue in issues:
                slack_message += "- %s\n" % issue
            try:
                user = CcUser.objects.get(email=user_email)
            except CcUser.DoesNotExist:
                logger.warning("No CcUser for email=%s", user_email)
                continue
            if not user.slack_id:
                logger.warning("No CcUser.slack_id for email=%s", user_email)
                continue
            slack_chat = SlackChat.objects.filter(members=user).filter(members=martiska)
            if slack_chat.count() == 0:
                if user == martiska:
                    continue
                slack_chat_details = slack.mpim.open(",".join([user.slack_id, martiska.slack_id]))
                chat_id = slack_chat_details.body["group"]["id"]
                slack_chat = SlackChat(chat_id=chat_id)
                slack_chat.save()
                slack_chat.members.add(martiska)
                slack_chat.members.add(user)
                logger.info("Created a new slack.mpim for %s", user)
            else:
                slack_chat = slack_chat[0]
                chat_id = slack_chat.chat_id
            slack.chat.post_message(chat_id, slack_message)
