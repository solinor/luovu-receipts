#!/usr/bin/env python
import os
import sys
from pathlib import Path  # python3 only

from dotenv import load_dotenv

# Reads the key,value pair from .env file and adds them to environment variables
# load_dotenv do not override existing System environment variables
env_path = Path('receipt_checking', '.env')
load_dotenv(verbose=True, dotenv_path=env_path)

if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "receipt_checking.settings")

    from django.core.management import execute_from_command_line

    execute_from_command_line(sys.argv)
