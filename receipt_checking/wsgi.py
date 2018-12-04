"""
WSGI config for receipt_checking project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.10/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from whitenoise.django import DjangoWhiteNoise

# Reads the key,value pair from .env file and adds them to environment variables
# load_dotenv do not override existing System environment variables
from dotenv import load_dotenv
load_dotenv(verbose=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "receipt_checking.settings")

application = get_wsgi_application()  # pylint:disable=invalid-name
application = DjangoWhiteNoise(application)  # pylint:disable=invalid-name
