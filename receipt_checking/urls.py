from django.conf.urls import include, url
from django.contrib import admin
from django.views.generic.base import RedirectView

import receipts.views

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^person/(?P<user_email>[a-zA-Z0-9-_\.@]+)/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})$', receipts.views.person_details, name='person'),
    url(r'^people/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})$', receipts.views.people_list, name='people'),
    url(r'^people$', receipts.views.people_list_redirect, name='people_list_redirect'),
    url(r'^all_rows/(?P<year>[0-9]{4})/(?P<month>[0-9]{1,2})$', receipts.views.all_receipts, name='all_receipts'),
    url(r'^all_rows$', receipts.views.all_receipts_redirect, name='all_receipts_redirect'),
    url(r'^receipt/(?P<receipt_id>[0-9]+)$', receipts.views.receipt_details, name='receipt'),
    url(r'^receipt/(?P<receipt_id>[0-9]+)/image', receipts.views.receipt_image, name='receipt_image'),
    url(r'^redirect_to_luovu/(?P<user_email>[a-zA-Z0-9-_\.@]+)/(?P<receipt_id>[0-9]+)$', receipts.views.redirect_to_luovu, name='redirect_to_luovu'),
    url(r'^$', receipts.views.frontpage, name='frontpage'),
    url(r'^queue_update$', receipts.views.queue_update, name="queue_update"),
    url(r'^accounts/', include('django.contrib.auth.urls')),
    url('', include('social_django.urls', namespace='social')),
    url(r'^import_html$', receipts.views.upload_invoice_html, name="import_html"),
    url(r'^slack_notifications$', receipts.views.send_slack_notifications, name="slack_notifications"),
    url(r'^search$', receipts.views.search, name='search'),
    url(r'^stats$', receipts.views.stats, name='stats'),
]
