# -*- coding: utf-8 -*-
# Generated by Django 1.9.7 on 2017-05-03 11:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0010_auto_20170503_1102'),
    ]

    operations = [
        migrations.AlterField(
            model_name='invoicerow',
            name='row_identifier',
            field=models.CharField(editable=False, max_length=100, primary_key=True, serialize=False),
        ),
    ]
