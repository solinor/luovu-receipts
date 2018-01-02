from django import template
from django.conf import settings
from django.template.loader import render_to_string

register = template.Library()


class FormatPingdomRumCode(template.Node):
    def __init__(self, rum_id):
        self.rum_id = rum_id

    def render(self, context):
        if self.rum_id:
            return render_to_string("snippets/pingdom_rum.html", {"rum_code": settings.RUM_CODE})
        return ""


@register.tag
def pingdom_rum_snippet(parser, token):  # pylint: disable=unused-argument
    if not settings.RUM_CODE:
        return FormatPingdomRumCode(None)
    return FormatPingdomRumCode(settings.TAG_MANAGER_CODE)
