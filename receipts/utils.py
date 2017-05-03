from receipts.models import LuovuReceipt, LuovuPrice, InvoiceRow
from django.contrib.auth.models import User
from receipts.luovu_api import LuovuApi
from django.conf import settings
import datetime

luovu_api = LuovuApi(settings.LUOVU_BUSINESS_ID, settings.LUOVU_PARTNER_TOKEN)
luovu_api.authenticate(settings.LUOVU_USERNAME, settings.LUOVU_PASSWORD)

def get_latest_month_for_user(user_email):
    """ Returns latest month when specified user had receipts or invoice rows """
    try:
        latest_invoice = InvoiceRow.objects.filter(card_holder_email_guess=user_email).values_list("invoice_date").latest("invoice_date")
        latest_invoice = latest_invoice[0]
    except InvoiceRow.DoesNotExist:
        latest_invoice = None
    try:
        latest_receipt = LuovuReceipt.objects.filter(luovu_user=user_email).values_list("date").latest("date")
        latest_receipt = latest_receipt[0]
    except LuovuReceipt.DoesNotExist:
        latest_receipt = None
    if latest_invoice is None:
        return latest_receipt
    if latest_receipt is None:
        return latest_invoice
    return max(latest_invoice, latest_receipt)


def get_all_users():
    people_with_invoices = InvoiceRow.objects.values_list("card_holder_email_guess").distinct()
    people_with_receipts = LuovuReceipt.objects.values_list("luovu_user")
    django_users = User.objects.values_list("email")
    people = set()
    for item in people_with_invoices:
        people.add(item[0])
    for item in people_with_receipts:
        people.add(item[0])
    for item in django_users:
        people.add(item[0])
    return sorted(people)

def refresh_receipts_for_user(user_email, start_date, end_date):
    receipt_count = 0
    receipts = luovu_api.get_receipts(user_email, start_date, end_date)
    for receipt in receipts:
        receipt_count += 1
        obj, created = LuovuReceipt.objects.update_or_create(luovu_id=receipt["id"], defaults={
            "luovu_user": user_email,
            "business_id": settings.LUOVU_BUSINESS_ID,
            "barcode": receipt["barcode"],
            "description": receipt["description"],
            "filename": receipt["filename"],
            "mime_type": receipt["mime_type"],
            "date": datetime.datetime.strptime(receipt["date"], "%Y-%m-%d").date(),
            "state": receipt["state"],
            "receipt_type": receipt["type"],
            "uploader": receipt["uploader"],
        })
        if not created:
            LuovuPrice.objects.filter(receipt=obj).delete()
            total_price = 0
            for price in receipt["prices"]:
                if price["price"].startswith("-"):
                    continue
                parsed_price = luovu_api.format_price(price["price"])
                price_obj = LuovuPrice(price=parsed_price, vat_percent=int(price["vat_percent"]), receipt=obj)
                price_obj.save()
                total_price += parsed_price
            obj.price = total_price
            obj.save()
    return receipt_count
