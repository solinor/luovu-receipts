from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required

from receipts.models import LuovuReceipt, InvoiceRow, InvoiceReceipt
from receipts.tables import ReceiptsTable
from receipts.utils import get_all_users
from receipts.luovu_api import LuovuApi

import base64


luovu_api = LuovuApi(settings.LUOVU_BUSINESS_ID, settings.LUOVU_PARTNER_TOKEN)
luovu_api.authenticate(settings.LUOVU_USERNAME, settings.LUOVU_PASSWORD)

@login_required
def frontpage(request):
    return HttpResponseRedirect(reverse("people"))
    return render(request, "frontpage.html", {})

@login_required
def receipt_image(request, receipt_id):
    receipt = luovu_api.get_receipt(receipt_id)
    attachment = base64.b64decode(receipt["attachment"])
    mime_type = receipt["mime_type"]
    return HttpResponse(attachment, content_type=mime_type)

@login_required
def receipt_details(request, receipt_id):
    receipt = get_object_or_404(LuovuReceipt, luovu_id=receipt_id)
    if receipt.mime_type in ("image/jpeg", "image/png"):
        context = {"receipt": receipt}
        return render(request, "receipt.html", context)
    else:
        return HttpResponseRedirect(reverse("receipt_image", args=(receipt_id,)))

@login_required
def people_list(request):

    context = {
        "people": get_all_users(),
    }
    return render(request, "people.html", context)

@login_required
def person_details(request, user_email, year, month):
    year = int(year)
    month = int(month)
    user_invoice = InvoiceRow.objects.filter(card_holder_email_guess=user_email).filter(invoice_date__year=year, invoice_date__month=month)
    user_receipts = LuovuReceipt.objects.filter(luovu_user=user_email).filter(date__year=year, date__month=month).exclude(state="deleted")

    table_rows = {}
    for item in user_invoice:
        if item.delivery_date not in table_rows:
            table_rows[item.delivery_date] = {"invoice_rows": [], "receipt_rows": []}
        table_rows[item.delivery_date]["invoice_rows"].append(item)
    for item in user_receipts:
        if item.date not in table_rows:
            table_rows[item.date] = {"invoice_rows": [], "receipt_rows": []}
        table_rows[item.date]["receipt_rows"].append(item)


    context = {"table": sorted(table_rows.items())}
    return render(request, "person_details.html", context)
