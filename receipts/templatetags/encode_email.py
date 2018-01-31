from django import template

from receipts.utils import encode_email as encode_email_func

register = template.Library()


@register.filter
def encode_email(value):
    return encode_email_func(value)
