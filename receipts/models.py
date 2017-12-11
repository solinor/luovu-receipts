from __future__ import unicode_literals

from django.db import models


class CcUser(models.Model):
    email = models.EmailField(primary_key=True)
    slack_id = models.CharField(max_length=50, null=True, blank=True)

    def __unicode__(self):
        return self.email

class SlackChat(models.Model):
    chat_id = models.CharField(max_length=50, primary_key=True, editable=False)
    members = models.ManyToManyField(CcUser)

    def __unicode__(self):
        return self.chat_id


class InvoiceRow(models.Model):
    row_identifier = models.CharField(max_length=100, primary_key=True, editable=False)
    description = models.CharField(max_length=255)
    card_holder = models.CharField(max_length=100)
    card_holder_id = models.CharField(max_length=100, null=True, blank=True)
    card_holder_email_guess = models.CharField(max_length=255)
    record_date = models.DateField()
    foreign_currency = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    foreign_currency_name = models.CharField(null=True, blank=True, max_length=5)
    foreign_currency_rate = models.FloatField(null=True, blank=True)
    cc_code = models.CharField(max_length=10)
    cc_description = models.CharField(max_length=255)
    delivery_date = models.DateField()
    row_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    invoice_date = models.DateField()

    class Meta:
        ordering = ("delivery_date", "row_price")

    def __unicode__(self):
        return u"%s - %s - %s" % (self.row_identifier, self.card_holder, self.row_price)


class InvoiceReceipt(models.Model):
    invoice_row = models.ForeignKey("InvoiceRow", on_delete=models.CASCADE)
    luovu_receipt = models.ForeignKey("LuovuReceipt", on_delete=models.CASCADE)
    linked_by_user = models.CharField(max_length=255, null=True, blank=True)
    confirmed_by = models.CharField(max_length=255, null=True, blank=True)
    linked_at = models.DateTimeField()
    confirmed_at = models.DateTimeField(null=True, blank=True)

    def __unicode__(self):
        return u"%s -> %s" % (self.invoice_row, self.luovu_receipt)


class LuovuReceipt(models.Model):
    luovu_id = models.IntegerField(primary_key=True, editable=False)
    luovu_user = models.CharField(max_length=255, null=True, blank=True)

    date = models.DateField()

    business_id = models.CharField(max_length=20, null=True, blank=True)
    barcode = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    filename = models.CharField(max_length=50, null=True, blank=True)
    mime_type = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=30, null=True, blank=True)
    receipt_type = models.CharField(max_length=50, null=True, blank=True)
    uploader = models.CharField(max_length=255, null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    account_number = models.IntegerField(null=True, blank=True)

    class Meta:
        ordering = ("date", "price")

    def __unicode__(self):
        return u"%s: %s - %s, %s" % (self.luovu_id, self.luovu_user, self.description, self.price)

    def has_description(self):
        return not (self.description is None or len(self.description) == 0)


class LuovuPrice(models.Model):
    receipt = models.ForeignKey("LuovuReceipt", on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    vat_percent = models.IntegerField(null=True, blank=True)
    account_number = models.IntegerField(null=True, blank=True)

    def __unicode__(self):
        return u"%s - %s - %s" % (self.receipt, self.price, self.vat_number)
