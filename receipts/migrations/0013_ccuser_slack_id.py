# -*- coding: utf-8 -*-
# Generated by Django 1.11 on 2017-05-04 20:30
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0012_auto_20170504_2015'),
    ]

    operations = [
        migrations.AddField(
            model_name='ccuser',
            name='slack_id',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
