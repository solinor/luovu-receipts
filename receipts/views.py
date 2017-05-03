from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError, HttpResponseBadRequest
from django.conf import settings
from django.core.urlresolvers import reverse
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from receipts.models import LuovuReceipt, InvoiceRow, InvoiceReceipt
from receipts.tables import ReceiptsTable
from receipts.utils import get_all_users, refresh_receipts_for_user
from receipts.luovu_api import LuovuApi

import base64
import calendar
import datetime


luovu_api = LuovuApi(settings.LUOVU_BUSINESS_ID, settings.LUOVU_PARTNER_TOKEN)
luovu_api.authenticate(settings.LUOVU_USERNAME, settings.LUOVU_PASSWORD)
def parse_date(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%d").date()

@login_required
def queue_update(request):
    if request.method == "POST":
        return_url = request.POST.get("back") or reverse("frontpage")
        user_email = request.POST.get("user_email")
        if user_email is None:
            return HttpResponseBadRequest("Missing user_email")
        end_date = parse_date(request.POST.get("end_date", (datetime.datetime.now() + datetime.timedelta(days=10)).strftime("%Y-%m-%d")))
        start_date = parse_date(request.POST.get("start_date", (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")))
        refresh_receipts_for_user(user_email, start_date, end_date)
        messages.add_message(request, messages.INFO, 'Luovu data for this view has been updated.')
        return HttpResponseRedirect(return_url)
    return HttpResponseBadRequest()


@login_required
def frontpage(request):
    return HttpResponseRedirect(reverse("people"))
    return render(request, "frontpage.html", {})

@login_required
def receipt_image(request, receipt_id):
    receipt = luovu_api.get_receipt(receipt_id)
    try:
        attachment = base64.b64decode(receipt["attachment"])
    except KeyError:
        print receipt
        return HttpResponseServerError("Unable to get receipt attachment.")
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

    start_date = datetime.date(year, month, 1)
    end_date = start_date.replace(day=calendar.monthrange(year, month)[1])
    sorted_table = sorted(table_rows.items())
    table = []
    for date, content in sorted_table:
        date_added = False
        for i in range(max(len(content["invoice_rows"]), len(content["receipt_rows"]))):
            row = []
            if not date_added:
                row.append(date)
                date_added = True
            else:
                row.append("")
            if i < len(content["invoice_rows"]):
                row.append(content["invoice_rows"][i])
            else:
                row.append(None)
            if i < len(content["receipt_rows"]):
                row.append(content["receipt_rows"][i])
            else:
                row.append(None)
            table.append(row)

    context = {"table": table, "user_email": user_email, "start_date": start_date, "end_date": end_date}
    return render(request, "person_details.html", context)
