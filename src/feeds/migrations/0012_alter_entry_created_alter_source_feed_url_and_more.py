# Generated by Django 4.2.10 on 2024-04-29 04:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('feeds', '0011_source_author_source_icon_url_source_subtitle_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='entry',
            name='created',
            field=models.DateTimeField(auto_now_add=True, db_index=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='feed_url',
            field=models.URLField(max_length=512, unique=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='icon_url',
            field=models.URLField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='image_url',
            field=models.URLField(blank=True, max_length=512, null=True),
        ),
        migrations.AlterField(
            model_name='source',
            name='site_url',
            field=models.URLField(blank=True, max_length=255, null=True),
        ),
    ]
