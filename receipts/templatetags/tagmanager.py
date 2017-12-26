from django import template
from django.conf import settings
from django.template.loader import render_to_string


register = template.Library()


class FormatTagManagerCode(template.Node):
    def __init__(self, tag_manager_code):
        self.tag_manager_code = tag_manager_code

    def render(self, context):
        if self.tag_manager_code:
            return render_to_string("snippets/tag_manager.html", {"tag_manager_code": settings.TAG_MANAGER_CODE})
        else:
            return ""


@register.tag
def tag_manager_snippet(parser, token):
    if not settings.TAG_MANAGER_CODE:
        return FormatTagManagerCode(None)
    return FormatTagManagerCode(settings.TAG_MANAGER_CODE)
