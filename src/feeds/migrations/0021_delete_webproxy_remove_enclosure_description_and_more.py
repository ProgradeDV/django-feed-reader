# Generated by Django 5.1.6 on 2025-03-05 03:13

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0020_alter_source_due_fetch'),
    ]

    operations = [
        migrations.DeleteModel(
            name='WebProxy',
        ),
        migrations.RemoveField(
            model_name='enclosure',
            name='description',
        ),
        migrations.RemoveField(
            model_name='enclosure',
            name='medium',
        ),
    ]
