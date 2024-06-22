# Generated by Django 5.0.6 on 2024-06-22 20:33

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0016_rename_post_enclosure_entry'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='created',
            field=models.DateTimeField(db_index=True, default=django.utils.timezone.now),
        ),
    ]
