import datetime
from collections import defaultdict

import schema
from django.conf import settings
from django.contrib.auth.models import User

from receipts.luovu_api import LuovuApi
from receipts.models import InvoiceRow, LuovuPrice, LuovuReceipt

luovu_api = LuovuApi(settings.LUOVU_BUSINESS_ID, settings.LUOVU_PARTNER_TOKEN, username=settings.LUOVU_USERNAME, password=settings.LUOVU_PASSWORD)  # pylint:disable=invalid-name


def create_receipts_table(sorted_table):
    table = []
    for date, content in sorted_table:
        receipt_rows = defaultdict(list)
        for item in content["receipt_rows"]:
            receipt_rows[item.price].append(item)
        invoice_rows = sorted(content["invoice_rows"], key=lambda x: x.row_price)
        for item in invoice_rows:
            if len(receipt_rows[item.row_price]):
                receipt = receipt_rows[item.row_price].pop()
                row = {"matching": True, "user_email": receipt.luovu_user, "items": [date, item, receipt]}
            else:
                row = {"matching": False, "user_email": item.card_holder_email_guess, "items": [date, item, None]}
            table.append(row)
        for item in receipt_rows.values():
            for receipt in item:
                row = {"matching": False, "user_email": receipt.luovu_user, "items": [date, None, receipt]}
                table.append(row)
    return table


def check_data_refresh(request):
    if request.session.get("refresh_data"):
        refresh_data = request.session["refresh_data"]
        refresh_user_email = refresh_data["user_email"]
        refresh_receipt_id = refresh_data["receipt_id"]
        request.session["refresh_data"] = False
        refresh_receipt(refresh_user_email, refresh_receipt_id)


def refresh_receipt(user_email, receipt_id):
    try:
        receipt_data = luovu_api.get_receipt(receipt_id)
    except schema.SchemaUnexpectedTypeError:
        return
    process_receipt(user_email, receipt_data)


def get_latest_month_for_user(user_email):
    """ Returns latest month when specified user had receipts or invoice rows """
    try:
        latest_invoice = InvoiceRow.objects.filter(card_holder_email_guess=user_email).values_list("invoice_date", flat=True).latest("invoice_date")
    except InvoiceRow.DoesNotExist:
        latest_invoice = None
    try:
        latest_receipt = LuovuReceipt.objects.filter(luovu_user=user_email).values_list("date", flat=True).latest("date")
    except LuovuReceipt.DoesNotExist:
        latest_receipt = None
    if latest_invoice is None:
        return latest_receipt
    if latest_receipt is None:
        return latest_invoice
    return max(latest_invoice, latest_receipt)


def process_receipt(user_email, receipt):
    if not receipt or not receipt["id"]:
        return
    obj, _ = LuovuReceipt.objects.update_or_create(luovu_id=receipt["id"], defaults={
        "luovu_user": user_email,
        "business_id": settings.LUOVU_BUSINESS_ID,
        "barcode": receipt["barcode"],
        "description": receipt["description"],
        "filename": receipt["filename"],
        "mime_type": receipt["mime_type"],
        "date": receipt["date"],
        "state": receipt["state"],
        "receipt_type": receipt["type"],
        "uploader": receipt["uploader"],
    })
    LuovuPrice.objects.filter(receipt=obj).delete()
    total_price = 0
    account_number = None
    for price in receipt["prices"]:
        if price["account_number"] != 0:
            account_number = price["account_number"]
        if price["price"] < 0:
            continue
        price_obj = LuovuPrice(price=price["price"], vat_percent=price["vat_percent"], receipt=obj, account_number=price["account_number"])
        price_obj.save()
        total_price += price["price"]
    obj.price = total_price
    obj.account_number = account_number
    obj.save()


def get_all_users():
    people_with_invoices = InvoiceRow.objects.values_list("card_holder_email_guess", flat=True).distinct()
    people_with_receipts = LuovuReceipt.objects.values_list("luovu_user", flat=True).distinct()
    django_users = User.objects.values_list("email", flat=True)
    people = set()
    for item in people_with_invoices:
        people.add(item)
    for item in people_with_receipts:
        people.add(item)
    for item in django_users:
        people.add(item)
    return sorted(people)


def refresh_receipts_for_user(user_email, start_date, end_date):
    receipt_count = 0
    receipts = luovu_api.get_receipts(user_email, start_date, end_date)
    for receipt in receipts:
        receipt_count += 1
        process_receipt(user_email, receipt)
    return receipt_count


def encode_email(email):
    return email.replace("@", "__at__").replace(".", "__")


def decode_email(email):
    return email.replace("__at__", "@").replace("__", ".")
