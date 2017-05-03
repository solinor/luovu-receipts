# -*- coding: utf-8 -*-

import django_tables2 as tables
from django.contrib.humanize.templatetags.humanize import intcomma
from django.template.defaultfilters import floatformat
from django.utils.html import format_html
from django.core.urlresolvers import reverse
from receipts.models import LuovuPrice, LuovuReceipt


class ReceiptsTable(tables.Table):
    class Meta:
        model = LuovuReceipt
        attrs = {"class": "table table-striped table-hover receipts-table"}
        fields = ("luovu_user", "date", "description", "price")

    def render_price(self, value):
        return u"%s€" % intcomma(floatformat(value, 2))
