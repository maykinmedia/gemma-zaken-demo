# Generated by Django 2.1.3 on 2019-08-07 19:59

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('demo', '0010_auto_20190729_1808'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='siteconfiguration',
            name='orc_base_url',
        ),
        migrations.RemoveField(
            model_name='siteconfiguration',
            name='orc_client_id',
        ),
        migrations.RemoveField(
            model_name='siteconfiguration',
            name='orc_secret',
        ),
    ]
