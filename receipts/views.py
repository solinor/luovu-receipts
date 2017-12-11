import base64
import calendar
import datetime
from collections import namedtuple, defaultdict

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError, HttpResponseBadRequest
from django.conf import settings
from django.urls import reverse
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, TruncYear
from receipts.models import LuovuReceipt, InvoiceRow
from receipts.utils import get_all_users, refresh_receipts_for_user, get_latest_month_for_user, check_data_refresh
from receipts.luovu_api import LuovuApi
from receipts.forms import UploadFileForm
from receipts.html_parser import HtmlParser

from dateutil.relativedelta import relativedelta


luovu_api = LuovuApi(settings.LUOVU_BUSINESS_ID, settings.LUOVU_PARTNER_TOKEN)  # pylint:disable=invalid-name
luovu_api.authenticate(settings.LUOVU_USERNAME, settings.LUOVU_PASSWORD)


def parse_date(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%d").date()


def create_receipts_table(sorted_table):
    table = []
    for date, content in sorted_table:
        date_added = False
        invoice_rows = sorted(content["invoice_rows"], key=lambda x: x.row_price)
        receipt_rows = sorted(content["receipt_rows"], key=lambda x: x.price)
        for i in range(max(len(invoice_rows), len(receipt_rows))):
            row = {"matching": False, "items": []}
            row["items"].append(date)
            if i < len(invoice_rows):
                row["items"].append(invoice_rows[i])
            else:
                row["items"].append(None)
            if i < len(receipt_rows):
                row["items"].append(receipt_rows[i])
            else:
                row["items"].append(None)

            if row["items"][1] and row["items"][2]:
                if row["items"][1].row_price == row["items"][2].price:
                    row["matching"] = True

            table.append(row)
    return table


@login_required
def redirect_to_luovu(request, user_email, receipt_id):
    request.session["refresh_data"] = {"user_email": user_email, "receipt_id": receipt_id}
    return HttpResponseRedirect("https://app.luovu.com/a/#i/%s" % receipt_id)


@login_required
def queue_update(request):
    if request.method == "POST":
        return_url = request.POST.get("back") or reverse("frontpage")
        user_email = request.POST.get("user_email")
        if user_email is None:
            return HttpResponseBadRequest("Missing user_email")
        end_date = parse_date(request.POST.get("end_date", (datetime.datetime.now() + datetime.timedelta(days=10)).strftime("%Y-%m-%d")))
        start_date = parse_date(request.POST.get("start_date", (datetime.datetime.now() - datetime.timedelta(days=60)).strftime("%Y-%m-%d")))
        print("Refreshing results for %s: %s-%s" % (user_email, start_date, end_date))
        count = refresh_receipts_for_user(user_email, start_date, end_date)
        messages.add_message(request, messages.INFO, 'Luovu data for this view has been updated (%s).' % count)
        return HttpResponseRedirect(return_url)
    return HttpResponseBadRequest()


@login_required
def frontpage(request):
    if request.user and request.user.email:
        latest_month = get_latest_month_for_user(request.user.email)
        if not latest_month:
            latest_month = datetime.date.today()

        return HttpResponseRedirect(reverse("person", args=(request.user.email, latest_month.year, latest_month.month)))
    return HttpResponseRedirect(reverse("people"))


@login_required
def receipt_image(request, receipt_id):
    receipt = luovu_api.get_receipt(receipt_id)
    try:
        attachment = base64.b64decode(receipt["attachment"])
    except KeyError:
        return HttpResponseServerError("Unable to get receipt attachment.")
    mime_type = receipt["mime_type"]
    return HttpResponse(attachment, content_type=mime_type)


@login_required
def receipt_details(request, receipt_id):
    receipt = get_object_or_404(LuovuReceipt, luovu_id=receipt_id)
    if receipt.mime_type in ("image/jpeg", "image/png"):
        context = {"receipt": receipt}
        return render(request, "receipt.html", context)
    return HttpResponseRedirect(reverse("receipt_image", args=(receipt_id,)))


@login_required
def people_list(request):
    today = datetime.date.today().replace(day=1)
    dates = [today]
    dates.append(today - relativedelta(months=1))
    dates.append(today - relativedelta(months=2))
    dates.append(today - relativedelta(months=3))
    dates.append(today - relativedelta(months=4))
    dates.reverse()
    dates_set = set(dates)
    people = [{"email": a, "dates": []} for a in get_all_users()]
    invoice_per_person_data = InvoiceRow.objects.values_list("card_holder_email_guess", "invoice_date").order_by("card_holder_email_guess", "invoice_date").annotate(rowcount=Count("row_identifier"))
    receipts_per_user_data = LuovuReceipt.objects.exclude(state="deleted").exclude(account_number=1900).annotate(month=TruncMonth("date")).values_list("luovu_user", "month").order_by("luovu_user", "month").annotate(rowcount=Count("pk"))
    cash_purchases_per_user_data = LuovuReceipt.objects.exclude(state="deleted").filter(account_number=1900).annotate(month=TruncMonth("date")).values_list("luovu_user", "month").order_by("luovu_user", "month").annotate(rowcount=Count("pk"))

    invoice_sum_per_person = InvoiceRow.objects.values_list("card_holder_email_guess", "invoice_date").order_by("card_holder_email_guess", "invoice_date").annotate(price_sum=Sum("row_price"))
    receipts_sum_per_user = LuovuReceipt.objects.exclude(state="deleted").exclude(account_number=1900).annotate(month=TruncMonth("date")).values_list("luovu_user", "month").order_by("luovu_user", "month").annotate(price_sum=Sum("price"))
    cash_purchases_sum_per_user = LuovuReceipt.objects.exclude(state="deleted").filter(account_number=1900).annotate(month=TruncMonth("date")).values_list("luovu_user", "month").order_by("luovu_user", "month").annotate(price_sum=Sum("price"))

    def gen_daily_dict():
        return defaultdict(int)

    def gen_user_dict():
        return defaultdict(gen_daily_dict)

    invoice_per_person = defaultdict(gen_user_dict)

    for user_email, invoice_date, cnt in invoice_per_person_data:
        invoice_per_person[user_email][invoice_date]["invoice_rows"] = cnt
    for user_email, receipt_date, cnt in receipts_per_user_data:
        invoice_per_person[user_email][receipt_date]["receipt_rows"] = cnt
    for user_email, receipt_date, cnt in cash_purchases_per_user_data:
        invoice_per_person[user_email][receipt_date]["cash_purchase_rows"] = cnt
    for user_email, receipt_date, price_sum in invoice_sum_per_person:
        invoice_per_person[user_email][receipt_date]["invoice_sum"] = price_sum
    for user_email, receipt_date, price_sum in receipts_sum_per_user:
        invoice_per_person[user_email][receipt_date]["receipts_sum"] = price_sum
    for user_email, receipt_date, price_sum in cash_purchases_sum_per_user:
        invoice_per_person[user_email][receipt_date]["cash_purchase_sum"] = price_sum

    for i, person in enumerate(people):
        if person["email"] not in invoice_per_person:
            people[i]["dates"] = False
            continue
        intersection = dates_set.intersection(invoice_per_person[person["email"]].keys())
        tmp = []
        for date in dates:
            if date not in invoice_per_person[person["email"]]:
                people[i]["dates"].append({})
            else:
                invoice_row = invoice_per_person[person["email"]][date]
                row = {"date": date, "match": False,
                       "invoice_rows": invoice_row["invoice_rows"],
                       "receipt_rows": invoice_row["receipt_rows"],
                       "cash_purchase_rows": invoice_row["cash_purchase_rows"],
                       "invoice_sum": invoice_row["invoice_sum"],
                       "receipts_sum": invoice_row["receipts_sum"],
                       "cash_purchase_sum": invoice_row["cash_purchase_sum"],
                }
                if row["invoice_rows"] == row["receipt_rows"] and row["invoice_sum"] == row["receipts_sum"]:
                    row["match"] = True
                people[i]["dates"].append(row)

    context = {
        "people": people,
        "dates": dates,
    }
    return render(request, "people.html", context)


@staff_member_required
def upload_invoice_html(request):
    if request.method == "POST":
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            invoice_date = datetime.date(form.cleaned_data["year"], form.cleaned_data["month"], 1)
            html_parser = HtmlParser(None, file_obj=request.FILES["file"])
            invoices = html_parser.process()
            for invoice in invoices:
                invoice["invoice_date"] = invoice_date
                InvoiceRow.objects.update_or_create(row_identifier=invoice["row_identifier"], defaults=invoice)

            messages.add_message(request, messages.INFO, "File imported for %s-%s" % (form.cleaned_data["year"], form.cleaned_data["month"]))
            return HttpResponseRedirect(reverse("frontpage"))
    else:
        form = UploadFileForm()
    return render(request, "import.html", {"form": form})


invoice_tuple = namedtuple("InvoiceRowTuple", ["row_identifier", "description", "row_price", "account_number", "delivery_date"])


@login_required
def person_details(request, user_email, year, month):
    year = int(year)
    month = int(month)
    start_date = datetime.date(year, month, 1)
    end_date = start_date.replace(day=calendar.monthrange(year, month)[1]) + datetime.timedelta(days=32)
    start_date = start_date - datetime.timedelta(days=32)

    check_data_refresh(request)

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
        if item.account_number == 1900:
            table_rows[item.date]["invoice_rows"].append(invoice_tuple(row_identifier="Autogenerated", description="Cash purchase", row_price=item.price, account_number=1900, delivery_date=item.date))

    table = create_receipts_table(sorted(table_rows.items()))

    previous_months = InvoiceRow.objects.filter(card_holder_email_guess=user_email).values_list("invoice_date").order_by("-invoice_date").distinct("invoice_date")

    context = {"table": table, "user_email": user_email, "start_date": start_date, "end_date": end_date, "previous_months": previous_months, "year": year, "month": month, "invoice_total": sum([invoice.row_price for invoice in user_invoice]), "receipts_total": sum([receipt.price for receipt in user_receipts])}
    return render(request, "person_details.html", context)
