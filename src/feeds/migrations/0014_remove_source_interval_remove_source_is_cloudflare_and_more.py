# Generated by Django 4.2.10 on 2024-05-14 00:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0013_alter_entry_options_remove_entry_index'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='source',
            name='interval',
        ),
        migrations.RemoveField(
            model_name='source',
            name='is_cloudflare',
        ),
        migrations.RemoveField(
            model_name='source',
            name='last_302_start',
        ),
        migrations.RemoveField(
            model_name='source',
            name='last_302_url',
        ),
    ]
