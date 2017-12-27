import base64
import calendar
import datetime
from collections import defaultdict

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth, TruncYear, Length
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseServerError, HttpResponseBadRequest
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from receipts.forms import UploadFileForm, SlackNotificationForm
from receipts.html_parser import HtmlParser
from receipts.luovu_api import LuovuApi
from receipts.models import LuovuReceipt, InvoiceRow, invoice_tuple
from receipts.utils import get_all_users, refresh_receipts_for_user, get_latest_month_for_user, check_data_refresh, create_receipts_table
from receipts.slack import send_notifications
import langdetect

luovu_api = LuovuApi(settings.LUOVU_BUSINESS_ID, settings.LUOVU_PARTNER_TOKEN)  # pylint:disable=invalid-name
luovu_api.authenticate(settings.LUOVU_USERNAME, settings.LUOVU_PASSWORD)


def parse_date(date_string):
    return datetime.datetime.strptime(date_string, "%Y-%m-%d").date()


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
def people_list_redirect(request):
    months = InvoiceRow.objects.values_list("invoice_date").order_by("-invoice_date").distinct("invoice_date")
    return HttpResponseRedirect(reverse("people", args=(months[0][0].year, months[0][0].month)))


@login_required
def people_list(request, year, month):
    year = int(year)
    month = int(month)
    today = datetime.date(year, month, 1)
    people = [{"email": a, "data": defaultdict(int)} for a in get_all_users()]
    invoice_per_person_data = InvoiceRow.objects.filter(invoice_date__year=year).filter(invoice_date__month=month).values_list("card_holder_email_guess", "invoice_date").order_by("card_holder_email_guess", "invoice_date").annotate(rowcount=Count("row_identifier"))
    receipts_per_user_data = LuovuReceipt.objects.filter(date__year=year, date__month=month).exclude(state="deleted").exclude(account_number=1900).annotate(month=TruncMonth("date")).values_list("luovu_user", "month").order_by("luovu_user", "month").annotate(rowcount=Count("pk"))
    cash_purchases_per_user_data = LuovuReceipt.objects.filter(date__year=year, date__month=month).exclude(state="deleted").filter(account_number=1900).annotate(month=TruncMonth("date")).values_list("luovu_user", "month").order_by("luovu_user", "month").annotate(rowcount=Count("pk"))
    receipts_without_descriptions = LuovuReceipt.objects.exclude(state="deleted").filter(date__year=year, date__month=month).annotate(description_length=Length("description")).filter(description_length=0).values_list("luovu_user", "description_length").order_by("luovu_user", "description_length").annotate(rowcount=Count("pk"))

    invoice_sum_per_person = InvoiceRow.objects.filter(invoice_date__year=year).filter(invoice_date__month=month).values_list("card_holder_email_guess", "invoice_date").order_by("card_holder_email_guess", "invoice_date").annotate(price_sum=Sum("row_price"))
    receipts_sum_per_user = LuovuReceipt.objects.filter(date__year=year, date__month=month).exclude(state="deleted").exclude(account_number=1900).annotate(month=TruncMonth("date")).values_list("luovu_user", "month").order_by("luovu_user", "month").annotate(price_sum=Sum("price"))
    cash_purchases_sum_per_user = LuovuReceipt.objects.filter(date__year=year, date__month=month).exclude(state="deleted").filter(account_number=1900).annotate(month=TruncMonth("date")).values_list("luovu_user", "month").order_by("luovu_user", "month").annotate(price_sum=Sum("price"))

    def gen_user_dict():
        return defaultdict(int)

    invoice_per_person = defaultdict(gen_user_dict)

    for user_email, _, cnt in invoice_per_person_data:
        invoice_per_person[user_email]["invoice_rows"] = cnt
    for user_email, _, cnt in receipts_per_user_data:
        invoice_per_person[user_email]["receipt_rows"] = cnt
    for user_email, _, cnt in cash_purchases_per_user_data:
        invoice_per_person[user_email]["cash_purchase_rows"] = cnt
    for user_email, _, cnt in receipts_without_descriptions:
        invoice_per_person[user_email]["empty_descriptions"] = cnt
    for user_email, _, price_sum in invoice_sum_per_person:
        invoice_per_person[user_email]["invoice_sum"] = price_sum
    for user_email, _, price_sum in receipts_sum_per_user:
        invoice_per_person[user_email]["receipts_sum"] = price_sum
    for user_email, _, price_sum in cash_purchases_sum_per_user:
        invoice_per_person[user_email]["cash_purchase_sum"] = price_sum

    summary_row = {
        "invoice_sum": 0,
        "receipts_sum": 0,
        "receipts_count": 0,
        "invoice_count": 0,
        "cash_purchase_count": 0,
        "cash_purchase_sum": 0,
    }
    for i, person in enumerate(people):
        if person["email"] not in invoice_per_person:
            people[i]["data"] = False
            continue

        invoice_row = invoice_per_person[person["email"]]
        row = {
            "sum_match": False,
            "count_match": False,
            "invoice_rows": invoice_row["invoice_rows"],
            "receipt_rows": invoice_row["receipt_rows"],
            "cash_purchase_rows": invoice_row["cash_purchase_rows"],
            "invoice_sum": invoice_row["invoice_sum"],
            "receipts_sum": invoice_row["receipts_sum"],
            "cash_purchase_sum": invoice_row["cash_purchase_sum"],
            "empty_descriptions": invoice_row["empty_descriptions"],
        }
        if row["invoice_rows"] == row["receipt_rows"]:
            row["count_match"] = True
        if row["invoice_sum"] == row["receipts_sum"]:
            row["sum_match"] = True
        people[i]["data"] = row
        summary_row["invoice_sum"] += invoice_row["invoice_sum"]
        summary_row["receipts_sum"] += invoice_row["receipts_sum"]
        summary_row["receipts_count"] += invoice_row["receipt_rows"]
        summary_row["invoice_count"] += invoice_row["invoice_rows"]
        summary_row["cash_purchase_sum"] += invoice_row["cash_purchase_sum"]
        summary_row["cash_purchase_count"] += invoice_row["cash_purchase_rows"]

    months = InvoiceRow.objects.values_list("invoice_date").order_by("-invoice_date").distinct("invoice_date")
    context = {
        "people": people,
        "months": months,
        "today": today,
        "summary_row": summary_row
    }
    return render(request, "people.html", context)


@staff_member_required
def send_slack_notifications(request):
    context = {}
    if request.method == "POST":
        form = SlackNotificationForm(request.POST)
        if form.is_valid():
            context["slack_notifications"] = send_notifications(form.cleaned_data["year"], form.cleaned_data["month"], form.cleaned_data["dry_run"])
    else:
        form = SlackNotificationForm()
    context["form"] = form
    return render(request, "slack.html", context)


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
            if form.cleaned_data["send_slack_notifications"]:
                slack_notifications = send_notifications(form.cleaned_data["year"], form.cleaned_data["month"])
                messages.add_message(request, messages.INFO, "Sent %s Slack notifications" % len(slack_notifications))
            return HttpResponseRedirect(reverse("frontpage"))
    else:
        form = UploadFileForm()
    return render(request, "import.html", {"form": form})


@login_required
def search(request):
    keyword = request.GET.get("q")
    if not keyword:
        return HttpResponseRedirect(reverse("frontpage"))
    invoices = InvoiceRow.objects.filter(description__icontains=keyword).order_by("-delivery_date")
    receipts = LuovuReceipt.objects.filter(description__icontains=keyword).order_by("-date")
    return render(request, "search.html", {"keyword": keyword, "invoices": invoices, "receipts": receipts})


def get_receipts_table(year, month, user_invoice, user_receipts):
    start_date = datetime.date(year, month, 1)
    end_date = start_date.replace(day=calendar.monthrange(year, month)[1]) + datetime.timedelta(days=32)
    start_date = start_date - datetime.timedelta(days=32)

    table_rows = {}
    for item in user_invoice:
        if item.delivery_date not in table_rows:
            table_rows[item.delivery_date] = {"invoice_rows": [], "receipt_rows": []}
        table_rows[item.delivery_date]["invoice_rows"].append(item)
    for item in user_receipts:
        if item.date not in table_rows:
            table_rows[item.date] = {"invoice_rows": [], "receipt_rows": []}
        try:
            item.autodetected_language = langdetect.detect(item.description)
        except (TypeError, langdetect.lang_detect_exception.LangDetectException):
            pass
        table_rows[item.date]["receipt_rows"].append(item)
        if item.account_number == 1900:
            table_rows[item.date]["invoice_rows"].append(invoice_tuple(user_email=item.luovu_user, row_identifier="Autogenerated", description="Cash purchase", row_price=item.price, account_number=1900, delivery_date=item.date))

    table = create_receipts_table(sorted(table_rows.items()))
    invoice_total = sum([invoice.row_price for invoice in user_invoice])
    receipts_total = sum([receipt.price for receipt in user_receipts])
    return table, start_date, end_date, invoice_total, receipts_total


def get_stats_view(previous_months, monthly_invoice_sum, monthly_cash_purchases_sum, monthly_receipts_sum):
    today = datetime.date.today()
    current_month = today.replace(year=today.year - 1, day=1)
    months = []
    while current_month < today:
        months.append(current_month)
        if current_month.month == 12:
            current_month = current_month.replace(year=current_month.year + 1, month=1)
        else:
            current_month = current_month.replace(month=current_month.month + 1)
    chart_data = {k: [k, 0, 0, 0] for k in months}

    for row in monthly_invoice_sum:
        if row["month"] in chart_data:
            chart_data[row["month"]][1] = row["price"]
    for row in monthly_receipts_sum:
        if row["month"] in chart_data:
            chart_data[row["month"]][2] = row["price"]
    for row in monthly_cash_purchases_sum:
        if row["month"] in chart_data:
            chart_data[row["month"]][3] = row["price"]
    chart_data = sorted(chart_data.values(), key=lambda k: k[0])

    return previous_months, chart_data


@login_required
def all_receipts_redirect(request):
    latest_month = datetime.date.today()
    return HttpResponseRedirect(reverse("all_receipts", args=(latest_month.year, latest_month.month)))


@login_required
def all_receipts(request, year, month):
    year = int(year)
    month = int(month)
    user_invoice = InvoiceRow.objects.filter(invoice_date__year=year, invoice_date__month=month)
    user_receipts = LuovuReceipt.objects.filter(date__year=year, date__month=month).exclude(state="deleted")
    previous_months = InvoiceRow.objects.values_list("invoice_date").order_by("-invoice_date").distinct("invoice_date")

    monthly_invoice_sum = InvoiceRow.objects.annotate(month=TruncMonth("delivery_date")).order_by("month").values("month").annotate(price=Sum("row_price")).values("month", "price")
    monthly_cash_purchases_sum = LuovuReceipt.objects.exclude(state="deleted").filter(account_number=1900).annotate(month=TruncMonth("date")).order_by("month").values("month").annotate(price=Sum("price")).values("month", "price")
    monthly_receipts_sum = LuovuReceipt.objects.exclude(state="deleted").exclude(account_number=1900).annotate(month=TruncMonth("date")).order_by("month").values("month").annotate(price=Sum("price")).values("month", "price")
    context = {
        "year": year,
        "month": month,
    }
    context["table"], context["start_date"], context["end_date"], context["invoice_total"], context["receipts_total"] = get_receipts_table(year, month, user_invoice, user_receipts)
    context["previous_months"], context["chart_data"] = get_stats_view(previous_months, monthly_invoice_sum, monthly_cash_purchases_sum, monthly_receipts_sum)

    return render(request, "all_receipts.html", context)


@login_required
def person_details(request, user_email, year, month):
    year = int(year)
    month = int(month)
    check_data_refresh(request)
    user_invoice = InvoiceRow.objects.filter(card_holder_email_guess=user_email).filter(invoice_date__year=year, invoice_date__month=month)
    user_receipts = LuovuReceipt.objects.filter(luovu_user=user_email).filter(date__year=year, date__month=month).exclude(state="deleted")
    previous_months = InvoiceRow.objects.filter(card_holder_email_guess=user_email).values_list("invoice_date").order_by("-invoice_date").distinct("invoice_date")

    monthly_invoice_sum = InvoiceRow.objects.filter(card_holder_email_guess=user_email).annotate(month=TruncMonth("delivery_date")).order_by("month").values("month").annotate(price=Sum("row_price")).values("month", "price")
    monthly_cash_purchases_sum = LuovuReceipt.objects.filter(luovu_user=user_email).exclude(state="deleted").filter(account_number=1900).annotate(month=TruncMonth("date")).order_by("month").values("month").annotate(price=Sum("price")).values("month", "price")
    monthly_receipts_sum = LuovuReceipt.objects.filter(luovu_user=user_email).exclude(state="deleted").exclude(account_number=1900).annotate(month=TruncMonth("date")).order_by("month").values("month").annotate(price=Sum("price")).values("month", "price")
    context = {
        "user_email": user_email,
        "year": year,
        "month": month,
    }
    context["table"], context["start_date"], context["end_date"], context["invoice_total"], context["receipts_total"] = get_receipts_table(year, month, user_invoice, user_receipts)
    context["previous_months"], context["chart_data"] = get_stats_view(previous_months, monthly_invoice_sum, monthly_cash_purchases_sum, monthly_receipts_sum)
    return render(request, "person.html", context)


@login_required
def stats(request):
    today = datetime.date.today()
    current_month = today.replace(year=today.year - 1, day=1)

    monthly_invoice_sum = InvoiceRow.objects.filter(delivery_date__gte=current_month).annotate(month=TruncMonth("delivery_date")).order_by("month").values("month").annotate(price=Sum("row_price")).values("month", "price")
    monthly_cash_purchases_sum = LuovuReceipt.objects.exclude(state="deleted").filter(account_number=1900).filter(date__gte=current_month).annotate(month=TruncMonth("date")).order_by("month").values("month").annotate(price=Sum("price")).values("month", "price")
    monthly_receipts_sum = LuovuReceipt.objects.exclude(state="deleted").exclude(account_number=1900).filter(date__gte=current_month).annotate(month=TruncMonth("date")).order_by("month").values("month").annotate(price=Sum("price")).values("month", "price")

    months = []
    while current_month < today:
        months.append(current_month)
        if current_month.month == 12:
            current_month = current_month.replace(year=current_month.year + 1, month=1)
        else:
            current_month = current_month.replace(month=current_month.month + 1)
    chart_data = {k: [k, 0, 0, 0] for k in months}

    for row in monthly_invoice_sum:
        if row["month"] in chart_data:
            chart_data[row["month"]][1] = row["price"]
    for row in monthly_receipts_sum:
        if row["month"] in chart_data:
            chart_data[row["month"]][2] = row["price"]
    for row in monthly_cash_purchases_sum:
        if row["month"] in chart_data:
            chart_data[row["month"]][3] = row["price"]
    chart_data = sorted(chart_data.values(), key=lambda k: k[0])


    prices = InvoiceRow.objects.filter(row_price__gt=0).values_list("row_price")
    histogram_slots = (5, 10, 15, 20, 25, 50, 100, 250, 500, 750, 1000, 2000, 4000, 8000, 16000)
    count_histogram = {k: 0 for k in histogram_slots}
    sum_histogram = {k: 0 for k in histogram_slots}

    for price, in prices:
        for k in histogram_slots:
            if price < k:
                count_histogram[k] += 1
                sum_histogram[k] += price
                break
        else:
            count_histogram[histogram_slots[-1]] += 1
            sum_histogram[histogram_slots[-1]] += price

    context = {
        "per_month": chart_data,
        "count_histogram": [i for i in sorted(count_histogram.items(), key=lambda k: k[0])],
        "sum_histogram": [i for i in sorted(sum_histogram.items(), key=lambda k: k[0])],
    }
    return render(request, "stats.html", context)
